import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, Request, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.payment import PaymentTransaction, PaymentEvent
from app.models.bill import UpcomingRadar
from app.models.outbox import OutboxEvent
from app.providers.sandbox_upi import SandboxUPIProvider
from app.repositories.audit import AuditRepository
from app.core.rate_limit import get_client_ip
from app.schemas.payment import PaymentResponse
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp")
):
    """
    Receives verified payment webhooks from the payment gateway.
    Includes HMAC-SHA256 signature verification and replay-protected ledger deduplication.
    """
    body_bytes = await request.body()
    if not x_signature or not x_timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Signature or X-Timestamp headers"
        )

    provider = SandboxUPIProvider()
    valid_sig = provider.verify_webhook_signature(
        payload_bytes=body_bytes,
        signature=x_signature,
        timestamp_str=x_timestamp,
        secret=settings.WEBHOOK_SECRET
    )
    if not valid_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired webhook signature"
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_id = payload.get("event_id")
    event_type = payload.get("event_type")  # payment.success, payment.failed
    intent_id = payload.get("intent_id")
    payment_reference = payload.get("payment_reference")

    if not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event_id")

    audit_repo = AuditRepository(db)
    client_ip = get_client_ip(request)

    # 1. Processed-Events Ledger Deduplication via indexed unique event_id
    ev_check = await db.execute(
        select(PaymentEvent).where(PaymentEvent.event_id == event_id)
    )
    if ev_check.scalar_one_or_none():
        await audit_repo.log_action(
            action="WEBHOOK_IGNORED",
            entity_type="webhook_event",
            entity_id=event_id,
            user_id=None,
            metadata_json={"reason": "already_processed", "event_type": event_type},
            ip_address=client_ip,
            commit=True
        )
        return {"received": True, "status": "already_processed", "event_id": event_id}

    # 2. Locate matching PaymentTransaction with row lock
    txn_query = select(PaymentTransaction).with_for_update()
    if intent_id:
        txn_query = txn_query.where(PaymentTransaction.provider_intent_id == intent_id)
    elif payload.get("transaction_id"):
        txn_query = txn_query.where(PaymentTransaction.id == uuid.UUID(payload.get("transaction_id")))
    else:
        await audit_repo.log_action(
            action="WEBHOOK_IGNORED",
            entity_type="webhook_event",
            entity_id=event_id,
            user_id=None,
            metadata_json={"reason": "ignored_no_transaction_reference", "event_type": event_type},
            ip_address=client_ip,
            commit=True
        )
        return {"received": True, "status": "ignored_no_transaction_reference"}

    txn_res = await db.execute(txn_query)
    txn = txn_res.scalar_one_or_none()
    if not txn:
        await audit_repo.log_action(
            action="WEBHOOK_IGNORED",
            entity_type="webhook_event",
            entity_id=event_id,
            user_id=None,
            metadata_json={"reason": "transaction_not_found", "event_type": event_type},
            ip_address=client_ip,
            commit=True
        )
        return {"received": True, "status": "transaction_not_found"}

    # 3. Cryptographic & Business Amount Integrity Check
    if event_type == "payment.success":
        if "amount" not in payload or payload["amount"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required amount in payment.success webhook payload"
            )
        try:
            from decimal import Decimal, InvalidOperation
            webhook_amount = Decimal(str(payload["amount"]))
            if webhook_amount != txn.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Amount mismatch: expected {txn.amount}, received {webhook_amount}"
                )
        except (InvalidOperation, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid amount in webhook payload"
            )
    elif "amount" in payload and payload["amount"] is not None:
        try:
            from decimal import Decimal, InvalidOperation
            webhook_amount = Decimal(str(payload["amount"]))
            if webhook_amount != txn.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Amount mismatch: expected {txn.amount}, received {webhook_amount}"
                )
        except (InvalidOperation, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid amount in webhook payload"
            )

    now = datetime.now(timezone.utc)
    payment_service = PaymentService(db)

    # 4. Strict State Machine Validation:
    # A webhook may only move a transaction from PENDING to SUCCESS or FAILED.
    # Webhooks for already FAILED (cancelled) or SUCCESS transactions, or when the bill
    # is already PAID or PAID_UNVERIFIED, must never mark the bill paid.
    from sqlalchemy.exc import IntegrityError, OperationalError
    try:
        bill_res = await db.execute(
            select(UpcomingRadar).where(UpcomingRadar.id == txn.bill_id).with_for_update()
        )
        bill = bill_res.scalar_one_or_none()

        # Check if transaction or bill is in terminal state
        is_terminal_txn = txn.status != "PENDING"
        is_bill_already_settled = bill is not None and bill.bill_status in ("PAID", "PAID_UNVERIFIED")

        if is_terminal_txn or is_bill_already_settled:
            # Record in ledger for audit trail without altering transaction or bill state
            event_record = PaymentEvent(
                transaction_id=txn.id,
                event_id=event_id,
                from_status=txn.status,
                to_status=txn.status,
                detail={
                    "action": "IGNORED_TERMINAL_OR_ALREADY_SETTLED",
                    "reason": f"txn_status={txn.status}, bill_status={bill.bill_status if bill else 'none'}",
                    "payload": payload
                }
            )
            db.add(event_record)
            await audit_repo.log_action(
                action="WEBHOOK_IGNORED",
                entity_type="webhook_event",
                entity_id=event_id,
                user_id=txn.paid_by_user_id,
                metadata_json={"reason": "terminal_state_or_already_settled", "event_type": event_type},
                ip_address=client_ip,
                commit=False
            )
            await db.commit()
            return {
                "received": True,
                "event_id": event_id,
                "status": "ignored_terminal_state",
                "transaction_status": txn.status,
                "bill_status": bill.bill_status if bill else None
            }

        if event_type == "payment.success":
            old_status = txn.status
            txn.status = "SUCCESS"
            txn.payment_reference = payment_reference or txn.payment_reference
            txn.verified_timestamp = now
            db.add(txn)

            if bill:
                bill.bill_status = "PAID"
                bill.paid_at = now
                db.add(bill)
                payment_service._spawn_next_recurring_bill_if_needed(bill)

                # Emit OutboxEvent
                outbox_event = OutboxEvent(
                    event_type="PAYMENT_SUCCEEDED",
                    aggregate_type="UpcomingRadar",
                    aggregate_id=str(bill.id),
                    payload={
                        "bill_id": str(bill.id),
                        "bill_title": bill.title,
                        "amount": f"{bill.amount:.2f}",
                        "payer_id": str(txn.paid_by_user_id) if txn.paid_by_user_id else None,
                        "payer_name": txn.paid_by_display_name_snapshot or "Member",
                        "payment_reference": txn.payment_reference,
                        "family_group_id": str(bill.family_group_id) if bill.family_group_id else None
                    },
                    dedupe_key=f"webhook:{event_id}"
                )
                db.add(outbox_event)

            event_record = PaymentEvent(
                transaction_id=txn.id,
                event_id=event_id,
                from_status=old_status,
                to_status="SUCCESS",
                detail={"action": "WEBHOOK_SUCCESS", "payload": payload}
            )
            db.add(event_record)
            await audit_repo.log_action(
                action="WEBHOOK_PROCESSED",
                entity_type="webhook_event",
                entity_id=event_id,
                user_id=txn.paid_by_user_id,
                metadata_json={"event_type": event_type, "transaction_id": str(txn.id)},
                ip_address=client_ip,
                commit=False
            )
            await db.commit()

        elif event_type == "payment.failed":
            old_status = txn.status
            txn.status = "FAILED"
            txn.failure_reason = payload.get("failure_reason", "Payment failed at bank")
            db.add(txn)

            event_record = PaymentEvent(
                transaction_id=txn.id,
                event_id=event_id,
                from_status=old_status,
                to_status="FAILED",
                detail={"action": "WEBHOOK_FAILED", "payload": payload}
            )
            db.add(event_record)
            await audit_repo.log_action(
                action="WEBHOOK_PROCESSED",
                entity_type="webhook_event",
                entity_id=event_id,
                user_id=txn.paid_by_user_id,
                metadata_json={"event_type": event_type, "transaction_id": str(txn.id)},
                ip_address=client_ip,
                commit=False
            )
            await db.commit()

    except (IntegrityError, OperationalError):
        await db.rollback()
        # Only a confirmed duplicate event_id in the ledger returns 200 already_processed.
        # In case of concurrent write lock contention (e.g. SQLite), retry ledger lookup briefly.
        import asyncio
        event_found = False
        for _ in range(10):
            try:
                ledger_res = await db.execute(
                    select(PaymentEvent).where(PaymentEvent.event_id == event_id)
                )
                if ledger_res.scalar_one_or_none():
                    event_found = True
                    break
            except OperationalError:
                pass
            await asyncio.sleep(0.05)

        if event_found:
            return {"received": True, "status": "already_processed", "event_id": event_id}

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error processing webhook event. Gateway retry requested."
        )

    return {"received": True, "event_id": event_id, "status": "processed"}

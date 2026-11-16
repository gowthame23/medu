import uuid
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    ConflictException,
    ResourceNotFoundException,
    ForbiddenException,
)
from app.models.bill import UpcomingRadar
from app.models.payment import PaymentTransaction, PaymentEvent
from app.models.outbox import OutboxEvent
from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.payment import PaymentRepository
from app.providers.sandbox_upi import SandboxUPIProvider
from app.schemas.payment import PaymentResponse


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.provider = SandboxUPIProvider()

    async def pay_bill(
        self,
        bill_id: uuid.UUID,
        idempotency_key: str,
        payer: User,
        family_group_id: Optional[uuid.UUID] = None,
        force_failure: bool = False
    ) -> PaymentResponse:
        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # TRANSACTION 1: Lock bill, validate status, insert PENDING txn
        # -------------------------------------------------------------
        # Re-fetch bill with lock and ignore soft-deleted bills
        query = select(UpcomingRadar).where(
            UpcomingRadar.id == bill_id,
            UpcomingRadar.deleted_at.is_(None)
        ).with_for_update()
        if family_group_id:
            query = query.where(UpcomingRadar.family_group_id == family_group_id)
        else:
            query = query.where(UpcomingRadar.user_id == payer.id)

        result = await self.db.execute(query)
        bill = result.scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found")

        # Check idempotency key first
        existing_idempotent = await self.payment_repo.get_by_idempotency_key(bill_id, idempotency_key)
        if existing_idempotent:
            if existing_idempotent.amount != bill.amount:
                raise ConflictException(
                    "IDEMPOTENCY_CONFLICT",
                    "Idempotency key has already been used with different payment parameters."
                )
            # Return stored result
            return PaymentResponse(
                transaction_id=existing_idempotent.id,
                bill_id=bill.id,
                amount=existing_idempotent.amount,
                status=existing_idempotent.status,
                payment_reference=existing_idempotent.payment_reference,
                paid_by_display_name=existing_idempotent.paid_by_display_name_snapshot,
                verified_timestamp=existing_idempotent.verified_timestamp,
                failure_reason=existing_idempotent.failure_reason,
                sandbox=True
            )

        if bill.bill_status in ("PAID", "PAID_UNVERIFIED"):
            raise ConflictException(
                "ALREADY_PAID",
                f"Bill has already been paid and settled ({bill.bill_status})."
            )

        # Check if another PENDING transaction is in progress
        active_txn = await self.payment_repo.get_active_transaction(bill_id)
        if active_txn and active_txn.status == "PENDING":
            exp = active_txn.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp > now:
                raise ConflictException(
                    "PAYMENT_IN_PROGRESS",
                    "Another payment transaction is currently processing for this bill."
                )

        # Insert PENDING transaction
        expires_at = now + timedelta(minutes=15)
        try:
            txn = await self.payment_repo.create_pending_transaction(
                bill_id=bill.id,
                idempotency_key=idempotency_key,
                amount=bill.amount,
                paid_by_user_id=payer.id,
                paid_by_display_name=payer.display_name,
                expires_at=expires_at,
                provider="SANDBOX_UPI"
            )
        except (IntegrityError, OperationalError):
            await self.db.rollback()
            raise ConflictException(
                "PAYMENT_IN_PROGRESS",
                "Another payment transaction is currently processing for this bill."
            )

        # -------------------------------------------------------------
        # OUTSIDE TRANSACTION: Call Payment Provider
        # -------------------------------------------------------------
        intent = await self.provider.create_intent(
            amount=bill.amount,
            reference_hint=bill.title
        )
        provider_result = await self.provider.verify(
            intent_id=intent.intent_id,
            force_outcome="FAILED" if force_failure else "SUCCESS"
        )

        # -------------------------------------------------------------
        # TRANSACTION 2: Finalize transaction exactly once
        # -------------------------------------------------------------
        if provider_result.success:
            finalized_txn = await self.payment_repo.finalize_transaction(
                transaction_id=txn.id,
                new_status="SUCCESS",
                payment_reference=provider_result.payment_reference,
                provider_intent_id=intent.intent_id
            )

            # Update bill status to PAID
            bill.bill_status = "PAID"
            bill.paid_at = datetime.now(timezone.utc)
            self.db.add(bill)

            # Auto-settlement: Spawn next recurring bill if applicable
            self._spawn_next_recurring_bill_if_needed(bill)

            # Insert OutboxEvent for notifications
            outbox_event = OutboxEvent(
                event_type="PAYMENT_SUCCEEDED",
                aggregate_type="UpcomingRadar",
                aggregate_id=str(bill.id),
                payload={
                    "bill_id": str(bill.id),
                    "bill_title": bill.title,
                    "amount": f"{bill.amount:.2f}",
                    "payer_id": str(payer.id),
                    "payer_name": payer.display_name,
                    "payment_reference": provider_result.payment_reference,
                    "family_group_id": str(family_group_id) if family_group_id else None
                },
                dedupe_key=f"payment:{txn.id}:event"
            )
            self.db.add(outbox_event)
            await self.db.commit()

            return PaymentResponse(
                transaction_id=finalized_txn.id,
                bill_id=bill.id,
                amount=finalized_txn.amount,
                status="SUCCESS",
                payment_reference=finalized_txn.payment_reference,
                paid_by_display_name=finalized_txn.paid_by_display_name_snapshot,
                verified_timestamp=finalized_txn.verified_timestamp,
                failure_reason=None,
                sandbox=True,
                upi_intent_uri=intent.upi_intent_uri
            )
        else:
            finalized_txn = await self.payment_repo.finalize_transaction(
                transaction_id=txn.id,
                new_status="FAILED",
                failure_reason=provider_result.failure_reason,
                provider_intent_id=intent.intent_id
            )
            return PaymentResponse(
                transaction_id=finalized_txn.id,
                bill_id=bill.id,
                amount=finalized_txn.amount,
                status="FAILED",
                payment_reference=None,
                paid_by_display_name=finalized_txn.paid_by_display_name_snapshot,
                verified_timestamp=None,
                failure_reason=provider_result.failure_reason,
                sandbox=True,
                upi_intent_uri=intent.upi_intent_uri
            )

    def _spawn_next_recurring_bill_if_needed(self, bill: UpcomingRadar) -> Optional[UpcomingRadar]:
        if bill.recurrence_interval != "NONE" and not bill.next_bill_generated:
            bill.next_bill_generated = True
            next_due = self._compute_next_due_date(bill.due_date, bill.recurrence_interval, anchor_day=bill.anchor_day)
            next_bill = UpcomingRadar(
                user_id=bill.user_id,
                family_group_id=bill.family_group_id,
                created_by_user_id=bill.created_by_user_id,
                title=bill.title,
                amount=bill.amount,
                due_date=next_due,
                consumer_number=bill.consumer_number,
                category=bill.category,
                bill_status="UNPAID",
                recurrence_interval=bill.recurrence_interval,
                anchor_day=bill.anchor_day,
                next_bill_generated=False
            )
            self.db.add(next_bill)
            return next_bill
        return None

    async def settle_self_reported_payment(
        self,
        bill_id: uuid.UUID,
        payer: User,
        family_group_id: Optional[uuid.UUID] = None
    ) -> UpcomingRadar:
        now = datetime.now(timezone.utc)

        # 1. Row-lock bill and ensure not soft-deleted
        query = select(UpcomingRadar).where(
            UpcomingRadar.id == bill_id,
            UpcomingRadar.deleted_at.is_(None)
        ).with_for_update()

        if family_group_id:
            query = query.where(UpcomingRadar.family_group_id == family_group_id)
        else:
            query = query.where(UpcomingRadar.user_id == payer.id)

        result = await self.db.execute(query)
        bill = result.scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found or deleted")

        # 2. Reject if already settled
        if bill.bill_status in ("PAID", "PAID_UNVERIFIED"):
            raise ConflictException(
                "ALREADY_PAID",
                f"Bill has already been settled ({bill.bill_status})."
            )

        # 3. Reject if active transaction is pending
        active_txn = await self.payment_repo.get_active_transaction(bill_id)
        if active_txn and active_txn.status == "PENDING":
            exp = active_txn.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp > now:
                raise ConflictException(
                    "PAYMENT_IN_PROGRESS",
                    "Another payment transaction is currently processing for this bill."
                )

        # 4. Mark status as PAID_UNVERIFIED
        bill.bill_status = "PAID_UNVERIFIED"
        bill.paid_at = now
        self.db.add(bill)

        # 5. Insert PaymentTransaction (verified_timestamp is None!)
        txn = PaymentTransaction(
            bill_id=bill.id,
            paid_by_user_id=payer.id,
            amount=bill.amount,
            idempotency_key=f"self_reported_{uuid.uuid4().hex}",
            status="SUCCESS",
            paid_by_display_name_snapshot=f"{payer.display_name} (Self-Reported)",
            payment_reference=f"SELF_REPORTED_{uuid.uuid4().hex[:12].upper()}",
            provider="SELF_REPORTED_OFFLINE",
            expires_at=now,
            verified_timestamp=None
        )
        self.db.add(txn)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(
                "ALREADY_PAID",
                "Bill has already been settled."
            )

        # 6. Shared recurring bill auto-spawn
        self._spawn_next_recurring_bill_if_needed(bill)

        # 7. Outbox notification
        outbox_event = OutboxEvent(
            event_type="BILL_MARKED_PAID",
            aggregate_type="UpcomingRadar",
            aggregate_id=str(bill.id),
            payload={
                "bill_id": str(bill.id),
                "bill_title": bill.title,
                "amount": f"{bill.amount:.2f}",
                "payer_id": str(payer.id),
                "payer_name": payer.display_name,
                "self_reported": True,
                "family_group_id": str(family_group_id) if family_group_id else None
            },
            dedupe_key=f"self_reported:{bill.id}:{now.isoformat()}"
        )
        self.db.add(outbox_event)

        await self.db.commit()
        await self.db.refresh(bill)
        return bill

    async def cancel_pending_payment(
        self,
        bill_id: uuid.UUID,
        user: User,
        family_group_id: Optional[uuid.UUID] = None
    ) -> PaymentResponse:
        # Confirm bill existence and ownership
        query = select(UpcomingRadar).where(
            UpcomingRadar.id == bill_id,
            UpcomingRadar.deleted_at.is_(None)
        )
        if family_group_id:
            query = query.where(UpcomingRadar.family_group_id == family_group_id)
        else:
            query = query.where(UpcomingRadar.user_id == user.id)

        res = await self.db.execute(query)
        bill = res.scalar_one_or_none()
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found")

        # Check active transaction
        active_txn = await self.payment_repo.get_active_transaction(bill_id)
        if not active_txn or active_txn.status != "PENDING":
            raise ConflictException("NO_PENDING_PAYMENT", "No pending payment transaction found to cancel.")

        finalized = await self.payment_repo.finalize_transaction(
            transaction_id=active_txn.id,
            new_status="FAILED",
            failure_reason="CANCELLED_BY_USER"
        )
        return PaymentResponse(
            transaction_id=finalized.id,
            bill_id=bill_id,
            amount=finalized.amount,
            status="FAILED",
            payment_reference=None,
            paid_by_display_name=finalized.paid_by_display_name_snapshot,
            verified_timestamp=None,
            failure_reason="CANCELLED_BY_USER",
            sandbox=True
        )

    def _compute_next_due_date(self, current_due: date, recurrence_interval: str, anchor_day: Optional[int] = None) -> date:
        import calendar
        if recurrence_interval == "WEEKLY":
            return current_due + timedelta(days=7)
        elif recurrence_interval == "MONTHLY":
            target_anchor = anchor_day or current_due.day
            year = current_due.year + (1 if current_due.month == 12 else 0)
            month = 1 if current_due.month == 12 else current_due.month + 1
            max_day = calendar.monthrange(year, month)[1]
            day = min(target_anchor, max_day)
            return date(year, month, day)
        elif recurrence_interval == "QUARTERLY":
            return current_due + timedelta(days=91)
        elif recurrence_interval == "YEARLY":
            target_anchor = anchor_day or current_due.day
            year = current_due.year + 1
            max_day = calendar.monthrange(year, current_due.month)[1]
            day = min(target_anchor, max_day)
            return date(year, current_due.month, day)
        return current_due

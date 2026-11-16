from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentTransaction, PaymentEvent
from app.providers.sandbox_upi import SandboxUPIProvider


async def reconcile_stale_pending_payments(session: AsyncSession) -> int:
    """
    Scans for PENDING transactions older than their expires_at (15 mins).
    Asks provider for status and finalizes idempotently.
    """
    now = datetime.now(timezone.utc)
    query = (
        select(PaymentTransaction)
        .where(
            PaymentTransaction.status == "PENDING",
            PaymentTransaction.expires_at <= now,
        )
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(query)
    stale_transactions = result.scalars().all()

    provider = SandboxUPIProvider()
    reconciled_count = 0

    for txn in stale_transactions:
        # Ask provider for status
        if txn.provider_intent_id:
            res = await provider.verify(txn.provider_intent_id)
            if res.success:
                txn.status = "SUCCESS"
                txn.payment_reference = res.payment_reference
                txn.verified_timestamp = now
            else:
                txn.status = "FAILED"
                txn.failure_reason = "TIMED_OUT_AND_RECONCILED"
        else:
            txn.status = "FAILED"
            txn.failure_reason = "EXPIRED_WITHOUT_PROVIDER_INTENT"

        txn.last_reconciled_at = now
        event = PaymentEvent(
            transaction_id=txn.id,
            from_status="PENDING",
            to_status=txn.status,
            detail={"reconciliation": "AUTOMATIC_APS_JOB", "reason": txn.failure_reason}
        )
        session.add(event)
        reconciled_count += 1

    if reconciled_count > 0:
        await session.commit()

    return reconciled_count

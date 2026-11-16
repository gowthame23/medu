import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentTransaction, PaymentEvent
from app.models.bill import UpcomingRadar


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_transaction(self, bill_id: uuid.UUID) -> Optional[PaymentTransaction]:
        """Finds any current PENDING or SUCCESS transaction for this bill."""
        query = select(PaymentTransaction).where(
            PaymentTransaction.bill_id == bill_id,
            PaymentTransaction.status.in_(["PENDING", "SUCCESS"])
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self,
        bill_id: uuid.UUID,
        idempotency_key: str
    ) -> Optional[PaymentTransaction]:
        query = select(PaymentTransaction).where(
            PaymentTransaction.bill_id == bill_id,
            PaymentTransaction.idempotency_key == idempotency_key
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_pending_transaction(
        self,
        bill_id: uuid.UUID,
        idempotency_key: str,
        amount: Decimal,
        paid_by_user_id: uuid.UUID,
        paid_by_display_name: str,
        expires_at: datetime,
        provider: str = "SANDBOX_UPI"
    ) -> PaymentTransaction:
        txn = PaymentTransaction(
            bill_id=bill_id,
            idempotency_key=idempotency_key,
            amount=amount,
            status="PENDING",
            paid_by_user_id=paid_by_user_id,
            paid_by_display_name_snapshot=paid_by_display_name,
            provider=provider,
            expires_at=expires_at
        )
        self.db.add(txn)
        await self.db.flush()

        event = PaymentEvent(
            transaction_id=txn.id,
            from_status="NONE",
            to_status="PENDING",
            detail={"action": "INITIATE_PAYMENT", "idempotency_key": idempotency_key}
        )
        self.db.add(event)
        try:
            await self.db.commit()
            return txn
        except (IntegrityError, OperationalError):
            await self.db.rollback()
            raise

    async def finalize_transaction(
        self,
        transaction_id: uuid.UUID,
        new_status: str,  # SUCCESS or FAILED
        payment_reference: Optional[str] = None,
        failure_reason: Optional[str] = None,
        provider_intent_id: Optional[str] = None
    ) -> PaymentTransaction:
        now = datetime.now(timezone.utc)
        query = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
        result = await self.db.execute(query)
        txn = result.scalar_one()

        old_status = txn.status
        txn.status = new_status
        txn.provider_intent_id = provider_intent_id or txn.provider_intent_id
        if new_status == "SUCCESS":
            txn.payment_reference = payment_reference
            txn.verified_timestamp = now
        elif new_status == "FAILED":
            txn.failure_reason = failure_reason

        event = PaymentEvent(
            transaction_id=txn.id,
            from_status=old_status,
            to_status=new_status,
            detail={"payment_reference": payment_reference, "failure_reason": failure_reason}
        )
        self.db.add(event)
        try:
            await self.db.commit()
            return txn
        except (IntegrityError, OperationalError):
            await self.db.rollback()
            raise

    async def get_family_payment_history(self, family_group_id: uuid.UUID) -> List[Tuple[PaymentTransaction, str]]:
        """Returns list of (PaymentTransaction, bill_title) for family group."""
        query = (
            select(PaymentTransaction, UpcomingRadar.title)
            .join(UpcomingRadar, UpcomingRadar.id == PaymentTransaction.bill_id)
            .where(
                UpcomingRadar.family_group_id == family_group_id,
                PaymentTransaction.status == "SUCCESS"
            )
            .order_by(PaymentTransaction.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.all()

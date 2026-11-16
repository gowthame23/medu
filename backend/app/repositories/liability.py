import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.liability import LiabilitiesVault, LoanPayment, LoanPrepayment


class LiabilityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_loan(
        self,
        user_id: uuid.UUID,  # MANDATORY owner context
        loan_name: str,
        principal_amount: Decimal,
        interest_rate: Decimal,
        tenure_months: int,
        start_date: date,
        monthly_emi: Decimal,
        currency: str = "INR"
    ) -> LiabilitiesVault:
        loan = LiabilitiesVault(
            user_id=user_id,
            loan_name=loan_name,
            principal_amount=principal_amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            start_date=start_date,
            monthly_emi=monthly_emi,
            currency=currency
        )
        self.db.add(loan)
        await self.db.commit()
        await self.db.refresh(loan)
        return loan

    async def get_loans(self, user_id: uuid.UUID) -> List[LiabilitiesVault]:
        """Strictly filtered by acting user_id."""
        query = (
            select(LiabilitiesVault)
            .where(
                LiabilitiesVault.user_id == user_id,
                LiabilitiesVault.deleted_at == None
            )
            .order_by(LiabilitiesVault.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_loan_by_id(self, user_id: uuid.UUID, loan_id: uuid.UUID) -> Optional[LiabilitiesVault]:
        """Strictly filtered by (loan_id, user_id). Never returns another user's loan."""
        query = select(LiabilitiesVault).where(
            LiabilitiesVault.id == loan_id,
            LiabilitiesVault.user_id == user_id,
            LiabilitiesVault.deleted_at == None
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_loan(self, user_id: uuid.UUID, loan_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(LiabilitiesVault)
            .where(
                LiabilitiesVault.id == loan_id,
                LiabilitiesVault.user_id == user_id
            )
            .values(deleted_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

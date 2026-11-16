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
                LiabilitiesVault.deleted_at.is_(None)
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
            LiabilitiesVault.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_remaining_principal(self, user_id: uuid.UUID, loan_id: uuid.UUID) -> Decimal:
        loan = await self.get_loan_by_id(user_id, loan_id)
        if not loan:
            return Decimal("0.00")
        from sqlalchemy import func
        q_prep = select(func.coalesce(func.sum(LoanPrepayment.lump_sum_amount), Decimal("0.00"))).where(LoanPrepayment.loan_id == loan_id)
        res_prep = await self.db.execute(q_prep)
        total_prepaid = res_prep.scalar_one()

        q_pay = select(func.coalesce(func.sum(LoanPayment.principal_paid), Decimal("0.00"))).where(LoanPayment.loan_id == loan_id)
        res_pay = await self.db.execute(q_pay)
        total_principal_paid = res_pay.scalar_one()

        rem = loan.principal_amount - (total_prepaid + total_principal_paid)
        return max(Decimal("0.00"), rem)

    async def add_payment(
        self,
        loan_id: uuid.UUID,
        payment_date: date,
        principal_paid: Decimal,
        interest_paid: Decimal,
        remaining_balance: Decimal
    ) -> LoanPayment:
        payment = LoanPayment(
            loan_id=loan_id,
            payment_date=payment_date,
            principal_paid=principal_paid,
            interest_paid=interest_paid,
            remaining_balance=remaining_balance
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def add_prepayment(
        self,
        loan_id: uuid.UUID,
        prepayment_date: date,
        lump_sum_amount: Decimal,
        effect: str = "REDUCE_TENURE"
    ) -> LoanPrepayment:
        prepayment = LoanPrepayment(
            loan_id=loan_id,
            prepayment_date=prepayment_date,
            lump_sum_amount=lump_sum_amount,
            effect=effect
        )
        self.db.add(prepayment)
        await self.db.commit()
        await self.db.refresh(prepayment)
        return prepayment

    async def update_loan(
        self,
        user_id: uuid.UUID,
        loan_id: uuid.UUID,
        **values
    ) -> Optional[LiabilitiesVault]:
        filtered_values = {k: v for k, v in values.items() if v is not None}
        if filtered_values:
            stmt = (
                update(LiabilitiesVault)
                .where(
                    LiabilitiesVault.id == loan_id,
                    LiabilitiesVault.user_id == user_id,
                    LiabilitiesVault.deleted_at.is_(None)
                )
                .values(**filtered_values)
            )
            await self.db.execute(stmt)
            await self.db.commit()
        return await self.get_loan_by_id(user_id, loan_id)

    async def get_payments(self, loan_id: uuid.UUID) -> List[LoanPayment]:
        query = (
            select(LoanPayment)
            .where(LoanPayment.loan_id == loan_id)
            .order_by(LoanPayment.payment_date.asc())
        )
        res = await self.db.execute(query)
        return res.scalars().all()

    async def get_prepayments(self, loan_id: uuid.UUID) -> List[LoanPrepayment]:
        query = (
            select(LoanPrepayment)
            .where(LoanPrepayment.loan_id == loan_id)
            .order_by(LoanPrepayment.prepayment_date.asc())
        )
        res = await self.db.execute(query)
        return res.scalars().all()

    async def delete_loan(self, user_id: uuid.UUID, loan_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(LiabilitiesVault)
            .where(
                LiabilitiesVault.id == loan_id,
                LiabilitiesVault.user_id == user_id,
                LiabilitiesVault.deleted_at.is_(None)
            )
            .values(deleted_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

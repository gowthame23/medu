import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import UpcomingRadar, BillReminder
from app.models.payment import PaymentTransaction


def mask_consumer_number(num: Optional[str]) -> Optional[str]:
    if not num:
        return None
    cleaned = num.strip()
    if len(cleaned) <= 4:
        return "****"
    return f"****{cleaned[-4:]}"


class BillRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_personal_bill(
        self,
        user_id: uuid.UUID,
        title: str,
        amount: Decimal,
        due_date: date,
        consumer_number: Optional[str] = None,
        category: str = "utility",
        recurrence_interval: str = "NONE"
    ) -> UpcomingRadar:
        bill = UpcomingRadar(
            user_id=user_id,
            family_group_id=None,
            created_by_user_id=user_id,
            title=title,
            amount=amount,
            due_date=due_date,
            consumer_number=consumer_number,
            category=category,
            recurrence_interval=recurrence_interval,
            bill_status="UNPAID"
        )
        self.db.add(bill)
        await self.db.commit()
        await self.db.refresh(bill)
        return bill

    async def create_family_bill(
        self,
        family_group_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        title: str,
        amount: Decimal,
        due_date: date,
        consumer_number: Optional[str] = None,
        category: str = "utility",
        recurrence_interval: str = "NONE"
    ) -> UpcomingRadar:
        bill = UpcomingRadar(
            user_id=None,
            family_group_id=family_group_id,
            created_by_user_id=created_by_user_id,
            title=title,
            amount=amount,
            due_date=due_date,
            consumer_number=consumer_number,
            category=category,
            recurrence_interval=recurrence_interval,
            bill_status="UNPAID"
        )
        self.db.add(bill)
        await self.db.commit()
        await self.db.refresh(bill)
        return bill

    async def get_personal_bills(self, user_id: uuid.UUID) -> List[UpcomingRadar]:
        query = (
            select(UpcomingRadar)
            .where(
                UpcomingRadar.user_id == user_id,
                UpcomingRadar.deleted_at == None
            )
            .order_by(UpcomingRadar.due_date.asc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_personal_bill(self, user_id: uuid.UUID, bill_id: uuid.UUID) -> Optional[UpcomingRadar]:
        query = select(UpcomingRadar).where(
            UpcomingRadar.id == bill_id,
            UpcomingRadar.user_id == user_id,
            UpcomingRadar.deleted_at == None
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_family_bills(self, family_group_id: uuid.UUID) -> List[UpcomingRadar]:
        query = (
            select(UpcomingRadar)
            .where(
                UpcomingRadar.family_group_id == family_group_id,
                UpcomingRadar.deleted_at == None
            )
            .order_by(UpcomingRadar.due_date.asc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_family_bill(self, family_group_id: uuid.UUID, bill_id: uuid.UUID) -> Optional[UpcomingRadar]:
        query = select(UpcomingRadar).where(
            UpcomingRadar.id == bill_id,
            UpcomingRadar.family_group_id == family_group_id,
            UpcomingRadar.deleted_at == None
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_bill(
        self,
        bill_id: uuid.UUID,
        title: Optional[str] = None,
        amount: Optional[Decimal] = None,
        due_date: Optional[date] = None,
        consumer_number: Optional[str] = None,
        category: Optional[str] = None,
        recurrence_interval: Optional[str] = None
    ) -> Optional[UpcomingRadar]:
        values = {}
        if title is not None:
            values["title"] = title
        if amount is not None:
            values["amount"] = amount
        if due_date is not None:
            values["due_date"] = due_date
        if consumer_number is not None:
            values["consumer_number"] = consumer_number
        if category is not None:
            values["category"] = category
        if recurrence_interval is not None:
            values["recurrence_interval"] = recurrence_interval

        if values:
            stmt = update(UpcomingRadar).where(UpcomingRadar.id == bill_id).values(**values)
            await self.db.execute(stmt)
            await self.db.commit()

        query = select(UpcomingRadar).where(UpcomingRadar.id == bill_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def soft_delete_bill(self, bill_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = update(UpcomingRadar).where(UpcomingRadar.id == bill_id).values(deleted_at=now)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_latest_successful_payment(self, bill_id: uuid.UUID) -> Optional[PaymentTransaction]:
        query = (
            select(PaymentTransaction)
            .where(
                PaymentTransaction.bill_id == bill_id,
                PaymentTransaction.status == "SUCCESS"
            )
            .order_by(PaymentTransaction.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().first()

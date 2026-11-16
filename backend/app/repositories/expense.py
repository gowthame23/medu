import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import ExpenseCategory, DailyLog, DailyLogEntry


SYSTEM_DEFAULT_CATEGORIES = [
    ("Groceries", "shopping-cart", 1),
    ("Transport", "car", 2),
    ("Food Out", "utensils", 3),
    ("Utilities", "zap", 4),
    ("Health", "heart-pulse", 5),
    ("Kids", "baby", 6),
    ("Shopping", "bag", 7),
    ("Entertainment", "tv", 8),
    ("Other", "more-horizontal", 9),
]


class ExpenseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def seed_system_categories(self) -> None:
        """Seeds default categories if they don't exist yet."""
        query = select(ExpenseCategory).where(ExpenseCategory.user_id == None)
        result = await self.db.execute(query)
        existing = {c.name for c in result.scalars().all()}

        for name, icon, sort_order in SYSTEM_DEFAULT_CATEGORIES:
            if name not in existing:
                cat = ExpenseCategory(
                    user_id=None,
                    name=name,
                    icon=icon,
                    sort_order=sort_order,
                    is_archived=False
                )
                self.db.add(cat)
        await self.db.commit()

    async def get_categories_for_user(self, user_id: uuid.UUID) -> List[ExpenseCategory]:
        """Returns system defaults plus active custom categories for the user."""
        query = (
            select(ExpenseCategory)
            .where(
                or_(ExpenseCategory.user_id == None, ExpenseCategory.user_id == user_id),
                ExpenseCategory.is_archived == False
            )
            .order_by(ExpenseCategory.sort_order.asc(), ExpenseCategory.name.asc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_category_by_id(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ExpenseCategory]:
        query = select(ExpenseCategory).where(
            ExpenseCategory.id == category_id,
            or_(ExpenseCategory.user_id == None, ExpenseCategory.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_user_category(
        self,
        user_id: uuid.UUID,
        name: str,
        icon: Optional[str] = None,
        sort_order: int = 0
    ) -> ExpenseCategory:
        cat = ExpenseCategory(
            user_id=user_id,
            name=name,
            icon=icon,
            sort_order=sort_order,
            is_archived=False
        )
        self.db.add(cat)
        await self.db.commit()
        await self.db.refresh(cat)
        return cat

    async def get_or_create_daily_log(
        self,
        user_id: uuid.UUID,
        log_date: date
    ) -> DailyLog:
        query = (
            select(DailyLog)
            .options(
                selectinload(DailyLog.entries).selectinload(DailyLogEntry.category)
            )
            .where(
                DailyLog.user_id == user_id,
                DailyLog.log_date == log_date
            )
        )
        result = await self.db.execute(query)
        log = result.scalar_one_or_none()

        if not log:
            log = DailyLog(user_id=user_id, log_date=log_date)
            self.db.add(log)
            await self.db.commit()
            await self.db.refresh(log)
            # Re-fetch with relationships loaded
            result = await self.db.execute(query)
            log = result.scalar_one()

        return log

    async def update_daily_log_notes(
        self,
        user_id: uuid.UUID,
        log_date: date,
        notes: Optional[str]
    ) -> Optional[DailyLog]:
        log = await self.get_or_create_daily_log(user_id, log_date)
        log.notes = notes
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def add_entry(
        self,
        user_id: uuid.UUID,
        daily_log_id: uuid.UUID,
        category_id: uuid.UUID,
        amount: Decimal
    ) -> DailyLogEntry:
        # Validate that daily_log belongs to user
        log_query = select(DailyLog).where(DailyLog.id == daily_log_id, DailyLog.user_id == user_id)
        log_result = await self.db.execute(log_query)
        if not log_result.scalar_one_or_none():
            raise ValueError("Daily log does not belong to acting user.")

        # Validate that category is system default or belongs to user
        cat = await self.get_category_by_id(category_id, user_id)
        if not cat:
            raise ValueError("Category not found or does not belong to acting user.")

        entry = DailyLogEntry(
            daily_log_id=daily_log_id,
            category_id=category_id,
            amount=amount
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        self.db.expire_all()
        return entry

    async def delete_entry(
        self,
        user_id: uuid.UUID,
        daily_log_id: uuid.UUID,
        entry_id: uuid.UUID
    ) -> bool:
        # Confirm log belongs to user
        log_query = select(DailyLog).where(DailyLog.id == daily_log_id, DailyLog.user_id == user_id)
        log_result = await self.db.execute(log_query)
        if not log_result.scalar_one_or_none():
            return False

        stmt = delete(DailyLogEntry).where(
            DailyLogEntry.id == entry_id,
            DailyLogEntry.daily_log_id == daily_log_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        self.db.expire_all()
        return result.rowcount > 0

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundException, ConflictException
from app.models.user import User
from app.repositories.expense import ExpenseRepository
from app.schemas.expense import (
    CategoryResponse,
    DailyLogResponse,
    DailyLogEntryResponse,
)


class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.expense_repo = ExpenseRepository(db)

    async def get_categories(self, user_id: uuid.UUID) -> List[CategoryResponse]:
        await self.expense_repo.seed_system_categories()
        categories = await self.expense_repo.get_categories_for_user(user_id)
        return [
            CategoryResponse(
                id=c.id,
                name=c.name,
                icon=c.icon,
                sort_order=c.sort_order,
                is_system_default=(c.user_id is None)
            )
            for c in categories
        ]

    async def create_custom_category(
        self,
        user_id: uuid.UUID,
        name: str,
        icon: Optional[str] = None
    ) -> CategoryResponse:
        cat = await self.expense_repo.create_user_category(
            user_id=user_id,
            name=name,
            icon=icon
        )
        return CategoryResponse(
            id=cat.id,
            name=cat.name,
            icon=cat.icon,
            sort_order=cat.sort_order,
            is_system_default=False
        )

    async def get_daily_log(
        self,
        user_id: uuid.UUID,
        log_date: date
    ) -> DailyLogResponse:
        log = await self.expense_repo.get_or_create_daily_log(user_id, log_date)

        # Dynamic computation of total_spent using Decimal
        total = Decimal("0.00")
        entry_responses = []
        for entry in log.entries:
            total += entry.amount
            entry_responses.append(
                DailyLogEntryResponse(
                    id=entry.id,
                    category_id=entry.category_id,
                    category_name=entry.category.name if entry.category else "Unknown",
                    category_icon=entry.category.icon if entry.category else None,
                    amount=entry.amount,
                    created_at=entry.created_at
                )
            )

        return DailyLogResponse(
            id=log.id,
            user_id=log.user_id,
            log_date=log.log_date,
            notes=log.notes,
            total_spent=total,
            entries=entry_responses,
            created_at=log.created_at
        )

    async def update_notes(
        self,
        user_id: uuid.UUID,
        log_date: date,
        notes: Optional[str]
    ) -> DailyLogResponse:
        await self.expense_repo.update_daily_log_notes(user_id, log_date, notes)
        return await self.get_daily_log(user_id, log_date)

    async def add_entry(
        self,
        user_id: uuid.UUID,
        log_date: date,
        category_id: uuid.UUID,
        amount: Decimal
    ) -> DailyLogResponse:
        log = await self.expense_repo.get_or_create_daily_log(user_id, log_date)
        try:
            await self.expense_repo.add_entry(user_id, log.id, category_id, amount)
        except ValueError as e:
            raise ResourceNotFoundException("Category", str(e))

        return await self.get_daily_log(user_id, log_date)

    async def delete_entry(
        self,
        user_id: uuid.UUID,
        log_date: date,
        entry_id: uuid.UUID
    ) -> DailyLogResponse:
        log = await self.expense_repo.get_or_create_daily_log(user_id, log_date)
        deleted = await self.expense_repo.delete_entry(user_id, log.id, entry_id)
        if not deleted:
            raise ResourceNotFoundException("Entry", "Entry not found in this day's check-in")

        return await self.get_daily_log(user_id, log_date)

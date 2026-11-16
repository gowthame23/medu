import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.errors import ResourceNotFoundException, ConflictException
from app.models.user import User
from app.models.expense import DailyLog
from app.repositories.expense import ExpenseRepository
from app.schemas.expense import (
    CategoryResponse,
    DailyLogResponse,
    DailyLogEntryResponse,
    DailyLogRangeResponse,
    CategoryTotalItem,
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

    async def get_daily_logs_range(
        self,
        user_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> DailyLogRangeResponse:
        logs = await self.expense_repo.get_daily_logs_range(user_id, start_date, end_date)
        log_map = {l.log_date: l for l in logs}

        # Calculate streak: consecutive active days ending today/yesterday
        today = date.today()
        streak = 0
        for i in range(365):
            day_to_check = today - timedelta(days=i)
            log = log_map.get(day_to_check)
            if not log and day_to_check < start_date:
                query = select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_date == day_to_check)
                res = await self.db.execute(query)
                log = res.scalar_one_or_none()
            if log and (len(log.entries) > 0 or log.notes):
                streak += 1
            else:
                if i == 0:
                    continue
                break

        total_range_spent = Decimal("0.00")
        category_sums: dict[uuid.UUID, dict] = {}
        log_responses: List[DailyLogResponse] = []

        for log in logs:
            day_total = Decimal("0.00")
            entry_responses = []
            for entry in log.entries:
                day_total += entry.amount
                total_range_spent += entry.amount
                cat_id = entry.category_id
                cat_name = entry.category.name if entry.category else "Other"
                cat_icon = entry.category.icon if entry.category else None
                if cat_id not in category_sums:
                    category_sums[cat_id] = {
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "category_icon": cat_icon,
                        "total_spent": Decimal("0.00")
                    }
                category_sums[cat_id]["total_spent"] += entry.amount
                entry_responses.append(
                    DailyLogEntryResponse(
                        id=entry.id,
                        category_id=entry.category_id,
                        category_name=cat_name,
                        category_icon=cat_icon,
                        amount=entry.amount,
                        created_at=entry.created_at
                    )
                )
            log_responses.append(
                DailyLogResponse(
                    id=log.id,
                    user_id=log.user_id,
                    log_date=log.log_date,
                    notes=log.notes,
                    total_spent=day_total,
                    entries=entry_responses,
                    created_at=log.created_at
                )
            )

        cat_totals_list = [
            CategoryTotalItem(
                category_id=item["category_id"],
                category_name=item["category_name"],
                category_icon=item["category_icon"],
                total_spent=item["total_spent"]
            )
            for item in category_sums.values()
        ]
        cat_totals_list.sort(key=lambda x: x.total_spent, reverse=True)

        return DailyLogRangeResponse(
            start_date=start_date,
            end_date=end_date,
            total_spent=total_range_spent,
            streak_days=streak,
            category_totals=cat_totals_list,
            logs=log_responses
        )

import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.expense import ExpenseService
from app.schemas.expense import (
    CategoryResponse,
    CategoryCreateRequest,
    DailyLogResponse,
    DailyLogEntryCreateRequest,
    DailyLogUpdateRequest,
)

router = APIRouter(tags=["Daily Expense Check-in"])


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ExpenseService(db)
    return await service.get_categories(current_user.id)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ExpenseService(db)
    return await service.create_custom_category(current_user.id, data.name, data.icon)


@router.get("/daily-logs", response_model=DailyLogResponse)
async def get_daily_log(
    log_date: Optional[date] = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_date = log_date or date.today()
    service = ExpenseService(db)
    return await service.get_daily_log(current_user.id, target_date)


@router.put("/daily-logs/{log_date}/notes", response_model=DailyLogResponse)
async def update_daily_log_notes(
    log_date: date,
    data: DailyLogUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ExpenseService(db)
    return await service.update_notes(current_user.id, log_date, data.notes)


@router.post("/daily-logs/{log_date}/entries", response_model=DailyLogResponse, status_code=status.HTTP_201_CREATED)
async def add_daily_log_entry(
    log_date: date,
    data: DailyLogEntryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ExpenseService(db)
    return await service.add_entry(
        user_id=current_user.id,
        log_date=log_date,
        category_id=data.category_id,
        amount=data.amount
    )


@router.delete("/daily-logs/{log_date}/entries/{entry_id}", response_model=DailyLogResponse)
async def delete_daily_log_entry(
    log_date: date,
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ExpenseService(db)
    return await service.delete_entry(current_user.id, log_date, entry_id)

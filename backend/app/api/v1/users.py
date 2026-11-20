from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import (
    UserResponse,
    UserUpdateRequest,
    ReminderSettingsResponse,
    ReminderSettingsUpdateRequest,
)

router = APIRouter(prefix="/me", tags=["User Profile"])


@router.get("", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("", response_model=UserResponse)
async def update_me(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    updated = await repo.update_profile(
        user_id=current_user.id,
        display_name=data.display_name,
        timezone=data.timezone,
        reminder_morning_enabled=data.reminder_morning_enabled,
        reminder_evening_enabled=data.reminder_evening_enabled
    )
    return UserResponse.model_validate(updated)


@router.get("/reminders", response_model=ReminderSettingsResponse)
async def get_reminder_settings(current_user: User = Depends(get_current_user)):
    return ReminderSettingsResponse(
        reminder_morning_enabled=current_user.reminder_morning_enabled,
        reminder_evening_enabled=current_user.reminder_evening_enabled
    )


@router.patch("/reminders", response_model=ReminderSettingsResponse)
async def update_reminder_settings(
    data: ReminderSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    updated = await repo.update_profile(
        user_id=current_user.id,
        reminder_morning_enabled=data.reminder_morning_enabled,
        reminder_evening_enabled=data.reminder_evening_enabled
    )
    return ReminderSettingsResponse(
        reminder_morning_enabled=updated.reminder_morning_enabled,
        reminder_evening_enabled=updated.reminder_evening_enabled
    )

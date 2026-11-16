import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = NotificationRepository(db)
    items = await repo.get_notifications(current_user.id)
    return [NotificationResponse.model_validate(n) for n in items]


@router.patch("/{id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = NotificationRepository(db)
    await repo.mark_read(current_user.id, id)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = NotificationRepository(db)
    await repo.mark_all_read(current_user.id)

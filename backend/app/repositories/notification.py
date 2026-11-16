import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: uuid.UUID,
        type_str: str,
        title: str,
        message: str,
        related_bill_id: Optional[uuid.UUID] = None
    ) -> Notification:
        # Guarantee: No loan information in notification message
        notif = Notification(
            user_id=user_id,
            type=type_str,
            title=title,
            message=message,
            related_bill_id=related_bill_id,
            is_read=False
        )
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def get_notifications(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
            .values(is_read=True, read_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

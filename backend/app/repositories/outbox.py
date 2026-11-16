import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


class OutboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        dedupe_key: str
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            dedupe_key=dedupe_key,
            status="PENDING",
            attempts=0
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_pending_events(self, limit: int = 50) -> List[OutboxEvent]:
        now = datetime.now(timezone.utc)
        query = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == "PENDING",
                OutboxEvent.next_attempt_at <= now
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_delivered(self, event_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(status="DELIVERED", processed_at=now)
        )
        await self.db.execute(stmt)
        await self.db.commit()

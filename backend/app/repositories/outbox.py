import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.outbox import OutboxEvent


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        # Guarantee: Never log passwords, tokens, full consumer numbers, or loan details
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_json,
            ip_address=ip_address
        )
        self.db.add(entry)
        await self.db.commit()
        return entry


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

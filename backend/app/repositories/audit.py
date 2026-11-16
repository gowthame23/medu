import hashlib
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

FORBIDDEN_KEY_FRAGMENTS = (
    "password", "pwd", "secret", "token", "auth",
    "consumer_number", "loan", "principal", "tenure", "interest", "emi"
)


def sanitize_audit_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not metadata:
        return metadata
    sanitized = {}
    for k, v in metadata.items():
        k_lower = str(k).lower()
        if any(frag in k_lower for frag in FORBIDDEN_KEY_FRAGMENTS):
            continue
        if isinstance(v, dict):
            sanitized[k] = sanitize_audit_metadata(v)
        else:
            sanitized[k] = v
    return sanitized


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
        ip_address: Optional[str] = None,
        commit: bool = True
    ) -> AuditLog:
        # Guarantee: Never log passwords, tokens, full consumer numbers, or loan details
        cleaned_meta = sanitize_audit_metadata(metadata_json)
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=cleaned_meta,
            ip_address=ip_address
        )
        self.db.add(entry)
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        return entry

    async def get_logs_by_action(self, action: str) -> List[AuditLog]:
        res = await self.db.execute(
            select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at.desc())
        )
        return list(res.scalars().all())

    async def get_all_logs(self) -> List[AuditLog]:
        res = await self.db.execute(
            select(AuditLog).order_by(AuditLog.created_at.asc())
        )
        return list(res.scalars().all())

import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verification import VerificationChallenge
from app.models.user import User
from app.core.errors import ValidationException


def normalize_e164_phone(phone: str) -> str:
    r"""
    Normalizes a phone number to standard E.164:
    - Strips spaces and dashes.
    - If bare 10-digit number, prefixes with +91.
    - Validates against ^\+[1-9]\d{7,14}$.
    """
    cleaned = re.sub(r"[\s\-]", "", phone.strip())
    if re.match(r"^\d{10}$", cleaned):
        cleaned = "+91" + cleaned
    if not re.match(r"^\+[1-9]\d{7,14}$", cleaned):
        raise ValidationException("Invalid phone number. Must be valid E.164 format (e.g. +919876543210).")
    return cleaned


class VerificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_phone_verified_by_other_user(self, phone_e164: str, user_id: uuid.UUID) -> bool:
        stmt = (
            select(User.id)
            .where(
                User.phone_e164 == phone_e164,
                User.phone_verified_at.is_not(None),
                User.id != user_id
            )
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def get_sends_in_cooldown(self, user_id: uuid.UUID, channel: str, cooldown_seconds: int = 60) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        stmt = (
            select(func.count())
            .select_from(VerificationChallenge)
            .where(
                VerificationChallenge.user_id == user_id,
                VerificationChallenge.channel == channel,
                VerificationChallenge.created_at >= cutoff
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def get_sends_in_window(self, user_id: uuid.UUID, channel: str, window_seconds: int = 3600) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        stmt = (
            select(func.count())
            .select_from(VerificationChallenge)
            .where(
                VerificationChallenge.user_id == user_id,
                VerificationChallenge.channel == channel,
                VerificationChallenge.created_at >= cutoff
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def invalidate_active_challenges(self, user_id: uuid.UUID, channel: str) -> None:
        stmt = (
            select(VerificationChallenge)
            .where(
                VerificationChallenge.user_id == user_id,
                VerificationChallenge.channel == channel,
                VerificationChallenge.consumed_at.is_(None)
            )
        )
        res = await self.db.execute(stmt)
        active_challenges = res.scalars().all()
        now = datetime.now(timezone.utc)
        for c in active_challenges:
            c.consumed_at = now

    async def create_challenge(
        self,
        challenge_id: uuid.UUID,
        user_id: uuid.UUID,
        channel: str,
        target_hash: str,
        code_hash: str,
        expires_at: datetime,
        max_attempts: int = 5
    ) -> VerificationChallenge:
        challenge = VerificationChallenge(
            id=challenge_id,
            user_id=user_id,
            channel=channel,
            target_hash=target_hash,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
            max_attempts=max_attempts
        )
        self.db.add(challenge)
        await self.db.flush()
        return challenge

    async def get_latest_challenge_for_update(
        self, user_id: uuid.UUID, channel: str
    ) -> Optional[VerificationChallenge]:
        stmt = (
            select(VerificationChallenge)
            .where(
                VerificationChallenge.user_id == user_id,
                VerificationChallenge.channel == channel
            )
            .order_by(VerificationChallenge.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

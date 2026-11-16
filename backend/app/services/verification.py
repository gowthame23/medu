import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    InvalidOrExpiredCodeException,
    ResourceNotFoundException,
)
from app.core.security import (
    hash_verification_target,
    hash_verification_code,
    encrypt_outbox_payload,
)
from app.models.user import User
from app.repositories.verification import VerificationRepository, normalize_e164_phone
from app.repositories.audit import AuditRepository
from app.repositories.outbox import OutboxRepository
from app.schemas.verification import (
    VerificationSendResponse,
    VerificationConfirmResponse,
)

# Test-only storage for E2E tests (guarded against production usage)
_test_codes: Dict[Tuple[uuid.UUID, str], str] = {}


def set_last_test_code(user_id: uuid.UUID, channel: str, code: str) -> None:
    if settings.APP_ENV != "production":
        _test_codes[(user_id, channel)] = code


def get_last_test_code(user_id: uuid.UUID, channel: str = "email") -> Optional[str]:
    if settings.APP_ENV == "production":
        return None
    return _test_codes.get((user_id, channel))


class VerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VerificationRepository(db)
        self.audit_repo = AuditRepository(db)
        self.outbox_repo = OutboxRepository(db)

    async def send_email_code(
        self, user: User, ip_address: Optional[str] = None
    ) -> VerificationSendResponse:
        # Enumeration & idempotent safety: always return 202
        if user.email_verified_at is not None:
            return VerificationSendResponse()

        # Cooldown check (60s)
        cooldown_sends = await self.repo.get_sends_in_cooldown(
            user.id, "email", settings.VERIFICATION_RESEND_COOLDOWN_SECONDS
        )
        if cooldown_sends > 0:
            return VerificationSendResponse()

        # Hourly cap (5 sends/hr)
        hourly_sends = await self.repo.get_sends_in_window(
            user.id, "email", 3600
        )
        if hourly_sends >= settings.VERIFICATION_HOURLY_CAP:
            return VerificationSendResponse()

        # Invalidate old active challenges for this channel
        await self.repo.invalidate_active_challenges(user.id, "email")

        # Generate 6-digit random code
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.VERIFICATION_CODE_TTL_MINUTES)

        target_hash = hash_verification_target(user.email.strip().lower())
        code_hash = hash_verification_code(str(challenge_id), code)

        await self.repo.create_challenge(
            challenge_id=challenge_id,
            user_id=user.id,
            channel="email",
            target_hash=target_hash,
            code_hash=code_hash,
            expires_at=expires_at,
            max_attempts=settings.VERIFICATION_MAX_ATTEMPTS
        )

        # Enqueue encrypted OutboxEvent in same transaction
        encrypted_payload = encrypt_outbox_payload({
            "to_email": user.email,
            "subject": "Your Mend Verification Code",
            "body": f"Your Mend verification code is: {code}\nValid for 10 minutes."
        })
        await self.outbox_repo.insert_event(
            event_type="VERIFICATION_EMAIL_DISPATCH",
            aggregate_type="VERIFICATION",
            aggregate_id=str(challenge_id),
            payload=encrypted_payload,
            dedupe_key=f"ver_email_{challenge_id}"
        )

        # Audit row with IDs and HMACs only - NO plaintext code or raw target
        await self.audit_repo.log_action(
            action="VERIFICATION_SENT",
            entity_type="VERIFICATION",
            entity_id=str(challenge_id),
            user_id=user.id,
            metadata_json={"channel": "email", "target_hash": target_hash},
            ip_address=ip_address,
            commit=False
        )

        set_last_test_code(user.id, "email", code)
        await self.db.commit()

        return VerificationSendResponse()

    async def confirm_email_code(
        self, user: User, code: str, ip_address: Optional[str] = None
    ) -> VerificationConfirmResponse:
        challenge = await self.repo.get_latest_challenge_for_update(user.id, "email")
        if not challenge or challenge.consumed_at is not None or challenge.attempts >= challenge.max_attempts:
            await self.audit_repo.log_action(
                action="VERIFICATION_FAILED",
                entity_type="VERIFICATION",
                entity_id=str(challenge.id) if challenge else None,
                user_id=user.id,
                metadata_json={"channel": "email", "reason": "challenge_invalid_or_consumed"},
                ip_address=ip_address,
                commit=True
            )
            raise InvalidOrExpiredCodeException()

        now = datetime.now(timezone.utc)
        exp = challenge.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            challenge.attempts += 1
            await self.audit_repo.log_action(
                action="VERIFICATION_FAILED",
                entity_type="VERIFICATION",
                entity_id=str(challenge.id),
                user_id=user.id,
                metadata_json={"channel": "email", "reason": "expired"},
                ip_address=ip_address,
                commit=True
            )
            raise InvalidOrExpiredCodeException()

        expected_hash = hash_verification_code(str(challenge.id), code.strip())
        if not secrets.compare_digest(challenge.code_hash, expected_hash):
            challenge.attempts += 1
            if challenge.attempts >= challenge.max_attempts:
                await self.audit_repo.log_action(
                    action="VERIFICATION_LOCKED",
                    entity_type="VERIFICATION",
                    entity_id=str(challenge.id),
                    user_id=user.id,
                    metadata_json={"channel": "email", "attempts": challenge.attempts},
                    ip_address=ip_address,
                    commit=True
                )
            else:
                await self.audit_repo.log_action(
                    action="VERIFICATION_FAILED",
                    entity_type="VERIFICATION",
                    entity_id=str(challenge.id),
                    user_id=user.id,
                    metadata_json={"channel": "email", "attempts": challenge.attempts},
                    ip_address=ip_address,
                    commit=True
                )
            raise InvalidOrExpiredCodeException()

        # Success
        challenge.consumed_at = now
        user.email_verified_at = now
        await self.audit_repo.log_action(
            action="VERIFICATION_CONFIRMED",
            entity_type="VERIFICATION",
            entity_id=str(challenge.id),
            user_id=user.id,
            metadata_json={"channel": "email"},
            ip_address=ip_address,
            commit=True
        )

        return VerificationConfirmResponse(channel="email")

    async def send_phone_code(
        self, user: User, phone_raw: str, ip_address: Optional[str] = None
    ) -> VerificationSendResponse:
        phone_e164 = normalize_e164_phone(phone_raw)

        # Enumeration safety: if phone is already verified by another user, return generic 202
        if await self.repo.is_phone_verified_by_other_user(phone_e164, user.id):
            return VerificationSendResponse()

        # Cooldown check (60s)
        cooldown_sends = await self.repo.get_sends_in_cooldown(
            user.id, "phone", settings.VERIFICATION_RESEND_COOLDOWN_SECONDS
        )
        if cooldown_sends > 0:
            return VerificationSendResponse()

        # Hourly cap (5 sends/hr)
        hourly_sends = await self.repo.get_sends_in_window(
            user.id, "phone", 3600
        )
        if hourly_sends >= settings.VERIFICATION_HOURLY_CAP:
            return VerificationSendResponse()

        await self.repo.invalidate_active_challenges(user.id, "phone")

        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.VERIFICATION_CODE_TTL_MINUTES)

        target_hash = hash_verification_target(phone_e164)
        code_hash = hash_verification_code(str(challenge_id), code)

        await self.repo.create_challenge(
            challenge_id=challenge_id,
            user_id=user.id,
            channel="phone",
            target_hash=target_hash,
            code_hash=code_hash,
            expires_at=expires_at,
            max_attempts=settings.VERIFICATION_MAX_ATTEMPTS
        )

        # Set user's phone_e164 (remains unverified until confirmed)
        user.phone_e164 = phone_e164

        encrypted_payload = encrypt_outbox_payload({
            "to_phone_e164": phone_e164,
            "message": f"Your Mend verification code is: {code}\nValid for 10 minutes."
        })
        await self.outbox_repo.insert_event(
            event_type="VERIFICATION_PHONE_DISPATCH",
            aggregate_type="VERIFICATION",
            aggregate_id=str(challenge_id),
            payload=encrypted_payload,
            dedupe_key=f"ver_phone_{challenge_id}"
        )

        await self.audit_repo.log_action(
            action="VERIFICATION_SENT",
            entity_type="VERIFICATION",
            entity_id=str(challenge_id),
            user_id=user.id,
            metadata_json={"channel": "phone", "target_hash": target_hash},
            ip_address=ip_address,
            commit=False
        )

        set_last_test_code(user.id, "phone", code)
        await self.db.commit()

        return VerificationSendResponse()

    async def confirm_phone_code(
        self, user: User, code: str, ip_address: Optional[str] = None
    ) -> VerificationConfirmResponse:
        challenge = await self.repo.get_latest_challenge_for_update(user.id, "phone")
        if not challenge or challenge.consumed_at is not None or challenge.attempts >= challenge.max_attempts:
            await self.audit_repo.log_action(
                action="VERIFICATION_FAILED",
                entity_type="VERIFICATION",
                entity_id=str(challenge.id) if challenge else None,
                user_id=user.id,
                metadata_json={"channel": "phone", "reason": "challenge_invalid_or_consumed"},
                ip_address=ip_address,
                commit=True
            )
            raise InvalidOrExpiredCodeException()

        now = datetime.now(timezone.utc)
        exp = challenge.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            challenge.attempts += 1
            await self.audit_repo.log_action(
                action="VERIFICATION_FAILED",
                entity_type="VERIFICATION",
                entity_id=str(challenge.id),
                user_id=user.id,
                metadata_json={"channel": "phone", "reason": "expired"},
                ip_address=ip_address,
                commit=True
            )
            raise InvalidOrExpiredCodeException()

        expected_hash = hash_verification_code(str(challenge.id), code.strip())
        if not secrets.compare_digest(challenge.code_hash, expected_hash):
            challenge.attempts += 1
            if challenge.attempts >= challenge.max_attempts:
                await self.audit_repo.log_action(
                    action="VERIFICATION_LOCKED",
                    entity_type="VERIFICATION",
                    entity_id=str(challenge.id),
                    user_id=user.id,
                    metadata_json={"channel": "phone", "attempts": challenge.attempts},
                    ip_address=ip_address,
                    commit=True
                )
            else:
                await self.audit_repo.log_action(
                    action="VERIFICATION_FAILED",
                    entity_type="VERIFICATION",
                    entity_id=str(challenge.id),
                    user_id=user.id,
                    metadata_json={"channel": "phone", "attempts": challenge.attempts},
                    ip_address=ip_address,
                    commit=True
                )
            raise InvalidOrExpiredCodeException()

        # Success
        challenge.consumed_at = now
        user.phone_verified_at = now
        await self.audit_repo.log_action(
            action="VERIFICATION_CONFIRMED",
            entity_type="VERIFICATION",
            entity_id=str(challenge.id),
            user_id=user.id,
            metadata_json={"channel": "phone"},
            ip_address=ip_address,
            commit=True
        )

        return VerificationConfirmResponse(channel="phone")

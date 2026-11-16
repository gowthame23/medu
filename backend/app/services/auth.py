import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_secure_token,
    hash_token,
    hash_audit_email,
)
from app.core.errors import (
    AuthenticationFailedException,
    ConflictException,
    TokenRevokedOrExpiredException,
)
from app.repositories.user import UserRepository
from app.repositories.audit import AuditRepository
from app.models.user import User, RefreshToken
from app.schemas.user import TokenResponse, UserResponse


# Dummy Argon2 hash for constant-time authentication and user enumeration mitigation
DUMMY_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgqlfreSaAcw"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
        timezone_str: str = "Asia/Kolkata"
    ) -> UserResponse:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            # Constant-time computation: compute hash even if user exists to prevent timing attacks
            hash_password(password)
            # Return uniform response to prevent email enumeration and account metadata leakage
            # NEVER expose the existing user's real ID or created_at timestamp
            return UserResponse(
                id=uuid.uuid4(),
                email=email,
                display_name=display_name,
                timezone=timezone_str,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )

        pwd_hash = hash_password(password)
        user = await self.user_repo.create(
            email=email,
            password_hash=pwd_hash,
            display_name=display_name,
            timezone=timezone_str
        )
        return UserResponse.model_validate(user)

    async def login(
        self,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[TokenResponse, str]:
        email_hash = hash_audit_email(email)
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Constant-time mitigation against user enumeration
            verify_password(password, DUMMY_ARGON2_HASH)
            await self.audit_repo.log_action(
                action="LOGIN_FAILURE",
                entity_type="user",
                entity_id=None,
                user_id=None,
                metadata_json={"email_hash": email_hash, "reason": "user_not_found"},
                ip_address=ip_address,
                commit=True
            )
            raise AuthenticationFailedException("Invalid email or password")

        if not verify_password(password, user.password_hash):
            await self.audit_repo.log_action(
                action="LOGIN_FAILURE",
                entity_type="user",
                entity_id=str(user.id),
                user_id=user.id,
                metadata_json={"email_hash": email_hash, "reason": "invalid_credentials"},
                ip_address=ip_address,
                commit=True
            )
            raise AuthenticationFailedException("Invalid email or password")

        await self.user_repo.update_last_login(user.id)

        # Issue Access Token (15 mins)
        access_token = create_access_token(str(user.id), user.email)

        # Issue Refresh Token (30 days) with secure rotation hash
        raw_refresh, token_hash = generate_secure_token(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.user_repo.create_refresh_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent
        )

        await self.audit_repo.log_action(
            action="LOGIN_SUCCESS",
            entity_type="user",
            entity_id=str(user.id),
            user_id=user.id,
            metadata_json={"email_hash": email_hash},
            ip_address=ip_address,
            commit=True
        )

        token_resp = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name
        )
        return token_resp, raw_refresh

    async def refresh_token(
        self,
        raw_refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[TokenResponse, str]:
        token_hash = hash_token(raw_refresh_token)
        token_record = await self.user_repo.get_refresh_token_by_hash(token_hash)

        if not token_record:
            raise TokenRevokedOrExpiredException("Invalid refresh token")

        # REUSE DETECTION: If token already revoked, check grace window for concurrent requests (e.g. React StrictMode)
        if token_record.revoked_at is not None:
            now = datetime.now(timezone.utc)
            rev_at = token_record.revoked_at
            if rev_at.tzinfo is None:
                rev_at = rev_at.replace(tzinfo=timezone.utc)

            # 30-second grace window ONLY for legitimately rotated tokens (has replaced_by_id)
            if token_record.replaced_by_id is not None and (now - rev_at).total_seconds() <= 30:
                user = await self.user_repo.get_by_id(token_record.user_id)
                if not user or not user.is_active:
                    raise AuthenticationFailedException("User not found or inactive")
                access_token = create_access_token(str(user.id), user.email)
                token_resp = TokenResponse(
                    access_token=access_token,
                    token_type="bearer",
                    expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name
                )
                # Return fresh access token and empty refresh string so cookie is untouched
                return token_resp, ""

            # Outside grace window or invalidated session: genuine reuse breach detected. Revoke all tokens!
            await self.user_repo.revoke_all_user_tokens(token_record.user_id)
            await self.audit_repo.log_action(
                action="REFRESH_TOKEN_REUSE_DETECTED",
                entity_type="refresh_token",
                entity_id=str(token_record.id),
                user_id=token_record.user_id,
                metadata_json={"reason": "revoked_token_reuse_outside_grace_window"},
                ip_address=ip_address,
                commit=True
            )
            raise TokenRevokedOrExpiredException("Security violation: Revoked token reuse detected. All sessions invalidated.")

        # Check expiry
        now = datetime.now(timezone.utc)
        exp = token_record.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            await self.user_repo.revoke_refresh_token(token_record.id)
            raise TokenRevokedOrExpiredException("Refresh token expired")

        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise AuthenticationFailedException("User not found or inactive")

        # Rotate: issue new token & revoke old one
        new_raw_refresh, new_token_hash = generate_secure_token(32)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_token_record = await self.user_repo.create_refresh_token(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            user_agent=user_agent
        )

        await self.user_repo.revoke_refresh_token(
            token_id=token_record.id,
            replaced_by_id=new_token_record.id
        )

        access_token = create_access_token(str(user.id), user.email)
        token_resp = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name
        )
        return token_resp, new_raw_refresh

    async def logout(self, raw_refresh_token: Optional[str]) -> None:
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            token_record = await self.user_repo.get_refresh_token_by_hash(token_hash)
            if token_record and token_record.revoked_at is None:
                await self.user_repo.revoke_refresh_token(token_record.id)

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not verify_password(current_password, user.password_hash):
            raise AuthenticationFailedException("Current password is incorrect")
        new_hash = hash_password(new_password)
        await self.user_repo.update_password(user_id, new_hash)
        # Security: Revoke all refresh tokens so all sessions must re-authenticate
        await self.user_repo.revoke_all_user_tokens(user_id)
        await self.audit_repo.log_action(
            action="CHANGE_PASSWORD",
            entity_type="user",
            entity_id=str(user_id),
            user_id=user_id,
            metadata_json={},
            ip_address=ip_address,
            commit=True
        )

    async def logout_all(self, user_id: uuid.UUID, ip_address: Optional[str] = None) -> None:
        await self.user_repo.revoke_all_user_tokens(user_id)
        await self.audit_repo.log_action(
            action="LOGOUT_ALL",
            entity_type="user",
            entity_id=str(user_id),
            user_id=user_id,
            metadata_json={},
            ip_address=ip_address,
            commit=True
        )

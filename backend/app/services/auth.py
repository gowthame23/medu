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
)
from app.core.errors import (
    AuthenticationFailedException,
    ConflictException,
    TokenRevokedOrExpiredException,
)
from app.repositories.user import UserRepository
from app.models.user import User, RefreshToken
from app.schemas.user import TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
        timezone_str: str = "Asia/Kolkata"
    ) -> UserResponse:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            # Generic error to prevent email enumeration
            raise ConflictException("REGISTRATION_FAILED", "Email already registered")

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
        user_agent: Optional[str] = None
    ) -> Tuple[TokenResponse, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
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
        user_agent: Optional[str] = None
    ) -> Tuple[TokenResponse, str]:
        token_hash = hash_token(raw_refresh_token)
        token_record = await self.user_repo.get_refresh_token_by_hash(token_hash)

        if not token_record:
            raise TokenRevokedOrExpiredException("Invalid refresh token")

        # REUSE DETECTION: If token already revoked, someone is replaying it!
        # Revoke the ENTIRE chain for this user as a security measure.
        if token_record.revoked_at is not None:
            await self.user_repo.revoke_all_user_tokens(token_record.user_id)
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

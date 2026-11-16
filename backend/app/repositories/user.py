import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, RefreshToken


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        query = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email == email.lower(), User.is_active == True)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        display_name: str,
        timezone: str = "Asia/Kolkata"
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            display_name=display_name,
            timezone=timezone,
            is_active=True
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = update(User).where(User.id == user_id).values(last_login_at=now)
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_profile(
        self,
        user_id: uuid.UUID,
        display_name: Optional[str] = None,
        timezone: Optional[str] = None
    ) -> Optional[User]:
        values = {}
        if display_name is not None:
            values["display_name"] = display_name
        if timezone is not None:
            values["timezone"] = timezone
        if values:
            stmt = update(User).where(User.id == user_id).values(**values)
            await self.db.execute(stmt)
            await self.db.commit()
        return await self.get_by_id(user_id)

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: Optional[str] = None
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent
        )
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_id: uuid.UUID, replaced_by_id: Optional[uuid.UUID] = None) -> None:
        now = datetime.now(timezone.utc)
        stmt = update(RefreshToken).where(RefreshToken.id == token_id).values(
            revoked_at=now,
            replaced_by_id=replaced_by_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revokes entire chain if token reuse or breach is detected."""
        now = datetime.now(timezone.utc)
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None
        ).values(revoked_at=now)
        await self.db.execute(stmt)
        await self.db.commit()

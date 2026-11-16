import uuid
from typing import Optional, Tuple
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.errors import (
    AuthenticationFailedException,
    ResourceNotFoundException,
    ForbiddenException,
)
from app.models.user import User
from app.models.family import FamilyMember, FamilyRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Authenticates user via short-lived JWT."""
    if not auth or not auth.credentials:
        raise AuthenticationFailedException("Authentication required")

    try:
        payload = decode_access_token(auth.credentials)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationFailedException("Invalid token payload")
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise AuthenticationFailedException("Invalid or expired token")

    query = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationFailedException("User not found or inactive")

    return user


class FamilyAccessChecker:
    def __init__(self, require_admin: bool = False):
        self.require_admin = require_admin

    async def __call__(
        self,
        id: uuid.UUID,  # matches family group id path param {id}
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> Tuple[User, FamilyMember]:
        query = select(FamilyMember).where(
            FamilyMember.family_group_id == id,
            FamilyMember.user_id == current_user.id
        )
        result = await db.execute(query)
        membership = result.scalar_one_or_none()

        # If user is not in group, return 404 to avoid leaking existence
        if not membership:
            raise ResourceNotFoundException("FamilyGroup", "Group not found")

        # If admin is required and user is only member, return 403
        if self.require_admin and membership.role != FamilyRole.ADMIN.value:
            raise ForbiddenException("Admin privileges required for this group action")

        return current_user, membership


require_family_member = FamilyAccessChecker(require_admin=False)
require_family_admin = FamilyAccessChecker(require_admin=True)

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.family import FamilyGroup, FamilyMember, FamilyInvitation, FamilyRole, InvitationStatus
from app.models.user import User


class FamilyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_group(
        self,
        group_name: str,
        timezone_str: str,
        creator_user_id: uuid.UUID
    ) -> FamilyGroup:
        group = FamilyGroup(
            group_name=group_name,
            timezone=timezone_str,
            created_by_user_id=creator_user_id
        )
        self.db.add(group)
        await self.db.flush()

        # Creator automatically becomes first ADMIN
        admin_membership = FamilyMember(
            user_id=creator_user_id,
            family_group_id=group.id,
            role=FamilyRole.ADMIN.value
        )
        self.db.add(admin_membership)
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def get_group_by_id(self, group_id: uuid.UUID) -> Optional[FamilyGroup]:
        query = select(FamilyGroup).where(
            FamilyGroup.id == group_id,
            FamilyGroup.deleted_at == None
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_groups(self, user_id: uuid.UUID) -> List[Tuple[FamilyGroup, str, int]]:
        """Returns list of (FamilyGroup, user_role, member_count)."""
        query = (
            select(
                FamilyGroup,
                FamilyMember.role,
                func.count(FamilyMember.id).over(partition_by=FamilyGroup.id).label("count")
            )
            .join(FamilyMember, FamilyMember.family_group_id == FamilyGroup.id)
            .where(
                FamilyMember.user_id == user_id,
                FamilyGroup.deleted_at == None
            )
        )
        result = await self.db.execute(query)
        groups = []
        for row in result.all():
            groups.append((row[0], row[1], row[2]))
        return groups

    async def update_group(
        self,
        group_id: uuid.UUID,
        group_name: Optional[str] = None,
        timezone_str: Optional[str] = None
    ) -> Optional[FamilyGroup]:
        values = {}
        if group_name is not None:
            values["group_name"] = group_name
        if timezone_str is not None:
            values["timezone"] = timezone_str
        if values:
            stmt = update(FamilyGroup).where(FamilyGroup.id == group_id).values(**values)
            await self.db.execute(stmt)
            await self.db.commit()
        return await self.get_group_by_id(group_id)

    async def get_membership(self, group_id: uuid.UUID, user_id: uuid.UUID) -> Optional[FamilyMember]:
        query = select(FamilyMember).where(
            FamilyMember.family_group_id == group_id,
            FamilyMember.user_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_group_members(self, group_id: uuid.UUID) -> List[Tuple[FamilyMember, User]]:
        query = (
            select(FamilyMember, User)
            .join(User, User.id == FamilyMember.user_id)
            .where(FamilyMember.family_group_id == group_id)
            .order_by(FamilyMember.joined_at.asc())
        )
        result = await self.db.execute(query)
        return result.all()

    async def count_admins(self, group_id: uuid.UUID) -> int:
        query = select(func.count(FamilyMember.id)).where(
            FamilyMember.family_group_id == group_id,
            FamilyMember.role == FamilyRole.ADMIN.value
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def add_member(self, group_id: uuid.UUID, user_id: uuid.UUID, role: FamilyRole = FamilyRole.MEMBER) -> FamilyMember:
        member = FamilyMember(
            user_id=user_id,
            family_group_id=group_id,
            role=role.value
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_role(self, group_id: uuid.UUID, target_user_id: uuid.UUID, new_role: FamilyRole) -> Optional[FamilyMember]:
        member = await self.get_membership(group_id, target_user_id)
        if not member:
            return None
        member.role = new_role.value
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, group_id: uuid.UUID, target_user_id: uuid.UUID) -> bool:
        stmt = delete(FamilyMember).where(
            FamilyMember.family_group_id == group_id,
            FamilyMember.user_id == target_user_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def create_invitation(
        self,
        group_id: uuid.UUID,
        email: str,
        token_hash: str,
        invited_by_user_id: uuid.UUID,
        expires_at: datetime
    ) -> FamilyInvitation:
        # Revoke any prior pending invitation for this group and email
        stmt = update(FamilyInvitation).where(
            FamilyInvitation.family_group_id == group_id,
            FamilyInvitation.email == email.lower(),
            FamilyInvitation.status == InvitationStatus.PENDING.value
        ).values(status=InvitationStatus.REVOKED.value)
        await self.db.execute(stmt)

        invitation = FamilyInvitation(
            family_group_id=group_id,
            email=email.lower(),
            token_hash=token_hash,
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
            status=InvitationStatus.PENDING.value
        )
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def get_invitation_by_hash(self, token_hash: str) -> Optional[FamilyInvitation]:
        query = select(FamilyInvitation).where(FamilyInvitation.token_hash == token_hash)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_group_invitations(self, group_id: uuid.UUID) -> List[FamilyInvitation]:
        query = (
            select(FamilyInvitation)
            .where(FamilyInvitation.family_group_id == group_id)
            .order_by(FamilyInvitation.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def revoke_invitation(self, group_id: uuid.UUID, invitation_id: uuid.UUID) -> bool:
        stmt = (
            update(FamilyInvitation)
            .where(
                FamilyInvitation.id == invitation_id,
                FamilyInvitation.family_group_id == group_id,
                FamilyInvitation.status == InvitationStatus.PENDING.value
            )
            .values(status=InvitationStatus.REVOKED.value)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_invitation_accepted(self, invitation_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(FamilyInvitation)
            .where(FamilyInvitation.id == invitation_id)
            .values(status=InvitationStatus.ACCEPTED.value, accepted_at=now)
        )
        await self.db.execute(stmt)
        await self.db.commit()

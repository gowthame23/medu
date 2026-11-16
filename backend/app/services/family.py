import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_secure_token, hash_token
from app.core.errors import (
    ConflictException,
    ForbiddenException,
    ResourceNotFoundException,
)
from app.models.family import FamilyGroup, FamilyMember, FamilyInvitation, FamilyRole, InvitationStatus
from app.models.user import User
from app.repositories.family import FamilyRepository
from app.repositories.user import UserRepository
from app.repositories.audit import AuditRepository
from app.schemas.family import (
    FamilyGroupResponse,
    FamilyMemberResponse,
    FamilyInvitationResponse,
)


class FamilyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.family_repo = FamilyRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    async def create_group(
        self,
        group_name: str,
        timezone_str: str,
        creator: User
    ) -> FamilyGroupResponse:
        group = await self.family_repo.create_group(
            group_name=group_name,
            timezone_str=timezone_str,
            creator_user_id=creator.id
        )
        return FamilyGroupResponse(
            id=group.id,
            group_name=group.group_name,
            timezone=group.timezone,
            created_by_user_id=group.created_by_user_id,
            created_at=group.created_at,
            member_count=1,
            my_role=FamilyRole.ADMIN.value
        )

    async def get_user_groups(self, user_id: uuid.UUID) -> List[FamilyGroupResponse]:
        tuples = await self.family_repo.get_user_groups(user_id)
        result = []
        for group, role, count in tuples:
            result.append(
                FamilyGroupResponse(
                    id=group.id,
                    group_name=group.group_name,
                    timezone=group.timezone,
                    created_by_user_id=group.created_by_user_id,
                    created_at=group.created_at,
                    member_count=count,
                    my_role=role
                )
            )
        return result

    async def get_group_details(self, group_id: uuid.UUID, user_id: uuid.UUID) -> FamilyGroupResponse:
        group = await self.family_repo.get_group_by_id(group_id)
        if not group:
            raise ResourceNotFoundException("FamilyGroup", "Group not found")

        membership = await self.family_repo.get_membership(group_id, user_id)
        if not membership:
            raise ResourceNotFoundException("FamilyGroup", "Group not found")

        members = await self.family_repo.get_group_members(group_id)
        return FamilyGroupResponse(
            id=group.id,
            group_name=group.group_name,
            timezone=group.timezone,
            created_by_user_id=group.created_by_user_id,
            created_at=group.created_at,
            member_count=len(members),
            my_role=membership.role
        )

    async def get_members(self, group_id: uuid.UUID) -> List[FamilyMemberResponse]:
        rows = await self.family_repo.get_group_members(group_id)
        result = []
        for member, user in rows:
            result.append(
                FamilyMemberResponse(
                    id=member.id,
                    user_id=user.id,
                    email=user.email,
                    display_name=user.display_name,
                    role=member.role,
                    joined_at=member.joined_at
                )
            )
        return result

    async def invite_member(
        self,
        group_id: uuid.UUID,
        email: str,
        acting_admin: User,
        ip_address: Optional[str] = None
    ) -> FamilyInvitationResponse:
        # Check if already a member
        target_user = await self.user_repo.get_by_email(email)
        if target_user:
            existing_member = await self.family_repo.get_membership(group_id, target_user.id)
            if existing_member:
                raise ConflictException("ALREADY_MEMBER", "User is already a member of this household group.")

        raw_token, token_hash = generate_secure_token(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = await self.family_repo.create_invitation(
            group_id=group_id,
            email=email,
            token_hash=token_hash,
            invited_by_user_id=acting_admin.id,
            expires_at=expires_at
        )

        email_hash = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()
        await self.audit_repo.log_action(
            action="INVITATION_CREATED",
            entity_type="invitation",
            entity_id=str(invitation.id),
            user_id=acting_admin.id,
            metadata_json={
                "family_group_id": str(group_id),
                "email_hash": email_hash
            },
            ip_address=ip_address,
            commit=True
        )

        return FamilyInvitationResponse(
            id=invitation.id,
            family_group_id=invitation.family_group_id,
            email=invitation.email,
            status=invitation.status,
            expires_at=invitation.expires_at,
            invited_by_user_id=invitation.invited_by_user_id,
            created_at=invitation.created_at,
            invite_token=raw_token  # Shown ONLY upon creation
        )

    async def accept_invitation(
        self,
        raw_token: str,
        accepting_user: User,
        ip_address: Optional[str] = None
    ) -> FamilyGroupResponse:
        token_hash = hash_token(raw_token)
        invitation = await self.family_repo.get_invitation_by_hash(token_hash)

        if not invitation:
            raise ResourceNotFoundException("Invitation", "Invalid invitation token.")

        # Email-bound security verification
        if accepting_user.email.lower() != invitation.email.lower():
            raise ForbiddenException("This invitation was issued to a different email address.")

        if invitation.status != InvitationStatus.PENDING.value:
            raise ConflictException("INVALID_INVITATION", f"Invitation has already been {invitation.status.lower()}.")

        now = datetime.now(timezone.utc)
        exp = invitation.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise ConflictException("INVITATION_EXPIRED", "Invitation link has expired.")

        # Check if already a member
        existing = await self.family_repo.get_membership(invitation.family_group_id, accepting_user.id)
        if existing:
            await self.family_repo.mark_invitation_accepted(invitation.id)
            await self.audit_repo.log_action(
                action="INVITATION_ACCEPTED",
                entity_type="invitation",
                entity_id=str(invitation.id),
                user_id=accepting_user.id,
                metadata_json={
                    "family_group_id": str(invitation.family_group_id)
                },
                ip_address=ip_address,
                commit=True
            )
            return await self.get_group_details(invitation.family_group_id, accepting_user.id)

        # Add as MEMBER
        await self.family_repo.add_member(
            group_id=invitation.family_group_id,
            user_id=accepting_user.id,
            role=FamilyRole.MEMBER
        )
        await self.family_repo.mark_invitation_accepted(invitation.id)

        await self.audit_repo.log_action(
            action="INVITATION_ACCEPTED",
            entity_type="invitation",
            entity_id=str(invitation.id),
            user_id=accepting_user.id,
            metadata_json={
                "family_group_id": str(invitation.family_group_id)
            },
            ip_address=ip_address,
            commit=True
        )

        return await self.get_group_details(invitation.family_group_id, accepting_user.id)

    async def update_member_role(
        self,
        group_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: FamilyRole,
        acting_admin: User,
        ip_address: Optional[str] = None
    ) -> FamilyMemberResponse:
        target_membership = await self.family_repo.get_membership(group_id, target_user_id)
        if not target_membership:
            raise ResourceNotFoundException("Member", "Target member not found in this group.")

        # LAST ADMIN GUARD
        if target_membership.role == FamilyRole.ADMIN.value and new_role == FamilyRole.MEMBER:
            admin_count = await self.family_repo.count_admins(group_id)
            if admin_count <= 1:
                raise ConflictException(
                    "LAST_ADMIN_GUARD",
                    "Cannot demote the last remaining admin. Promote another member first."
                )

        updated = await self.family_repo.update_member_role(group_id, target_user_id, new_role)
        target_user = await self.user_repo.get_by_id(target_user_id)

        role_str = new_role.value if hasattr(new_role, "value") else str(new_role)
        await self.audit_repo.log_action(
            action="MEMBER_ROLE_CHANGED",
            entity_type="family_member",
            entity_id=str(target_user_id),
            user_id=acting_admin.id,
            metadata_json={
                "family_group_id": str(group_id),
                "new_role": role_str
            },
            ip_address=ip_address,
            commit=True
        )

        return FamilyMemberResponse(
            id=updated.id,
            user_id=target_user.id,
            email=target_user.email,
            display_name=target_user.display_name,
            role=updated.role,
            joined_at=updated.joined_at
        )

    async def remove_member(
        self,
        group_id: uuid.UUID,
        target_user_id: uuid.UUID,
        acting_admin: User,
        ip_address: Optional[str] = None
    ) -> None:
        target_membership = await self.family_repo.get_membership(group_id, target_user_id)
        if not target_membership:
            raise ResourceNotFoundException("Member", "Target member not found in this group.")

        # LAST ADMIN GUARD
        if target_membership.role == FamilyRole.ADMIN.value:
            admin_count = await self.family_repo.count_admins(group_id)
            if admin_count <= 1:
                raise ConflictException(
                    "LAST_ADMIN_GUARD",
                    "Cannot remove the last remaining admin of the group."
                )

        await self.family_repo.remove_member(group_id, target_user_id)
        await self.audit_repo.log_action(
            action="MEMBER_REMOVED",
            entity_type="family_member",
            entity_id=str(target_user_id),
            user_id=acting_admin.id,
            metadata_json={
                "family_group_id": str(group_id)
            },
            ip_address=ip_address,
            commit=True
        )

    async def leave_group(
        self,
        group_id: uuid.UUID,
        acting_user: User
    ) -> None:
        membership = await self.family_repo.get_membership(group_id, acting_user.id)
        if not membership:
            raise ResourceNotFoundException("FamilyGroup", "Group not found")

        # LAST ADMIN GUARD
        if membership.role == FamilyRole.ADMIN.value:
            admin_count = await self.family_repo.count_admins(group_id)
            members = await self.family_repo.get_group_members(group_id)
            if admin_count <= 1 and len(members) > 1:
                raise ConflictException(
                    "LAST_ADMIN_GUARD",
                    "You are the sole admin. You must promote another member to Admin before leaving."
                )

        await self.family_repo.remove_member(group_id, acting_user.id)

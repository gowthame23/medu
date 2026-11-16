import uuid
from typing import List, Tuple
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_family_member, require_family_admin
from app.models.user import User
from app.models.family import FamilyMember
from app.services.family import FamilyService
from app.schemas.family import (
    FamilyGroupCreateRequest,
    FamilyGroupUpdateRequest,
    FamilyGroupResponse,
    FamilyMemberResponse,
    FamilyInviteRequest,
    FamilyInvitationResponse,
    AcceptInvitationRequest,
    MemberRoleUpdateRequest,
)

router = APIRouter(tags=["Families"])


@router.post("/families", response_model=FamilyGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_family_group(
    data: FamilyGroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = FamilyService(db)
    return await service.create_group(
        group_name=data.group_name,
        timezone_str=data.timezone or "Asia/Kolkata",
        creator=current_user
    )


@router.get("/families", response_model=List[FamilyGroupResponse])
async def list_my_family_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = FamilyService(db)
    return await service.get_user_groups(current_user.id)


@router.get("/families/{id}", response_model=FamilyGroupResponse)
async def get_family_group(
    id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    user, _ = auth_data
    service = FamilyService(db)
    return await service.get_group_details(id, user.id)


@router.patch("/families/{id}", response_model=FamilyGroupResponse)
async def update_family_group(
    id: uuid.UUID,
    data: FamilyGroupUpdateRequest,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    user, _ = auth_data
    service = FamilyService(db)
    await service.family_repo.update_group(
        group_id=id,
        group_name=data.group_name,
        timezone_str=data.timezone
    )
    return await service.get_group_details(id, user.id)


@router.get("/families/{id}/members", response_model=List[FamilyMemberResponse])
async def list_family_members(
    id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    service = FamilyService(db)
    return await service.get_members(id)


@router.post("/families/{id}/invitations", response_model=FamilyInvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    id: uuid.UUID,
    data: FamilyInviteRequest,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    admin_user, _ = auth_data
    service = FamilyService(db)
    return await service.invite_member(id, data.email, admin_user)


@router.get("/families/{id}/invitations", response_model=List[FamilyInvitationResponse])
async def list_invitations(
    id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    service = FamilyService(db)
    invites = await service.family_repo.get_group_invitations(id)
    return [FamilyInvitationResponse.model_validate(inv) for inv in invites]


@router.delete("/families/{id}/invitations/{inv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    id: uuid.UUID,
    inv_id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    service = FamilyService(db)
    await service.family_repo.revoke_invitation(id, inv_id)


@router.post("/invitations/accept", response_model=FamilyGroupResponse)
async def accept_invitation(
    data: AcceptInvitationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = FamilyService(db)
    return await service.accept_invitation(data.token, current_user)


@router.patch("/families/{id}/members/{uid}", response_model=FamilyMemberResponse)
async def update_member_role(
    id: uuid.UUID,
    uid: uuid.UUID,
    data: MemberRoleUpdateRequest,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    admin_user, _ = auth_data
    service = FamilyService(db)
    return await service.update_member_role(id, uid, data.role, admin_user)


@router.delete("/families/{id}/members/{uid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    id: uuid.UUID,
    uid: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    admin_user, _ = auth_data
    service = FamilyService(db)
    await service.remove_member(id, uid, admin_user)


@router.post("/families/{id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_family_group(
    id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    user, _ = auth_data
    service = FamilyService(db)
    await service.leave_group(id, user)

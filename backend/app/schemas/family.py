import uuid
import zoneinfo
from datetime import datetime
from typing import Optional, List
from pydantic import EmailStr, Field, field_validator

from app.schemas.common import StrictBaseModel
from app.models.family import FamilyRole, InvitationStatus


class FamilyGroupCreateRequest(StrictBaseModel):
    group_name: str = Field(min_length=1, max_length=100)
    timezone: Optional[str] = "Asia/Kolkata"

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid IANA timezone: '{v}'")
        return v


class FamilyGroupUpdateRequest(StrictBaseModel):
    group_name: Optional[str] = Field(None, min_length=1, max_length=100)
    timezone: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid IANA timezone: '{v}'")
        return v


class FamilyMemberResponse(StrictBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: str
    joined_at: datetime


class FamilyGroupResponse(StrictBaseModel):
    id: uuid.UUID
    group_name: str
    timezone: str
    created_by_user_id: Optional[uuid.UUID]
    created_at: datetime
    member_count: int = 1
    my_role: Optional[str] = None


class FamilyInviteRequest(StrictBaseModel):
    email: EmailStr


class FamilyInvitationResponse(StrictBaseModel):
    id: uuid.UUID
    family_group_id: uuid.UUID
    email: str
    status: str
    expires_at: datetime
    invited_by_user_id: uuid.UUID
    created_at: datetime
    invite_token: Optional[str] = None  # Returned ONLY on creation!


class AcceptInvitationRequest(StrictBaseModel):
    token: str


class MemberRoleUpdateRequest(StrictBaseModel):
    role: FamilyRole

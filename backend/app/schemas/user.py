import uuid
import zoneinfo
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field, field_validator

from app.schemas.common import StrictBaseModel


class UserRegisterRequest(StrictBaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    timezone: Optional[str] = "Asia/Kolkata"

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid IANA timezone: '{v}'")
        return v


class UserLoginRequest(StrictBaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(StrictBaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class RefreshTokenRequest(StrictBaseModel):
    refresh_token: Optional[str] = None


class TokenResponse(StrictBaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes
    user_id: uuid.UUID
    email: str
    display_name: str


class UserResponse(StrictBaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    timezone: str
    is_active: bool
    created_at: datetime


class UserUpdateRequest(StrictBaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    timezone: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid IANA timezone: '{v}'")
        return v

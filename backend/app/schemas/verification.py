from typing import Optional
from pydantic import Field
from app.schemas.common import StrictBaseModel


class VerificationSendResponse(StrictBaseModel):
    status: str = "accepted"
    message: str = "Verification code dispatched if eligible."


class PhoneSendRequest(StrictBaseModel):
    phone: str = Field(..., min_length=7, max_length=30, description="Phone number to verify")


class VerificationConfirmRequest(StrictBaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Verification code")


class VerificationConfirmResponse(StrictBaseModel):
    status: str = "confirmed"
    channel: str


class VerificationStatusResponse(StrictBaseModel):
    email_verified: bool
    phone_verified: bool
    phone_e164: Optional[str] = None

from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import get_client_ip, verification_rate_limiter
from app.core.errors import ResourceNotFoundException
from app.models.user import User
from app.schemas.verification import (
    VerificationSendResponse,
    VerificationConfirmRequest,
    VerificationConfirmResponse,
    PhoneSendRequest,
)
from app.services.verification import VerificationService, get_last_test_code

router = APIRouter(prefix="/verification", tags=["Verification"])


@router.post(
    "/email/send",
    response_model=VerificationSendResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verification_rate_limiter)]
)
async def send_email_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_addr = get_client_ip(request)
    service = VerificationService(db)
    return await service.send_email_code(current_user, ip_address=ip_addr)


@router.post(
    "/email/confirm",
    response_model=VerificationConfirmResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verification_rate_limiter)]
)
async def confirm_email_verification(
    request: Request,
    data: VerificationConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_addr = get_client_ip(request)
    service = VerificationService(db)
    return await service.confirm_email_code(current_user, data.code, ip_address=ip_addr)


@router.post(
    "/phone/send",
    response_model=VerificationSendResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verification_rate_limiter)]
)
async def send_phone_verification(
    request: Request,
    data: PhoneSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_addr = get_client_ip(request)
    service = VerificationService(db)
    return await service.send_phone_code(current_user, data.phone, ip_address=ip_addr)


@router.post(
    "/phone/confirm",
    response_model=VerificationConfirmResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verification_rate_limiter)]
)
async def confirm_phone_verification(
    request: Request,
    data: VerificationConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_addr = get_client_ip(request)
    service = VerificationService(db)
    return await service.confirm_phone_code(current_user, data.code, ip_address=ip_addr)


@router.get(
    "/test-last-code",
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
async def get_test_last_code(
    channel: str = "email",
    current_user: User = Depends(get_current_user),
):
    """Test-only endpoint to retrieve the last issued code for E2E testing."""
    if settings.APP_ENV == "production":
        raise ResourceNotFoundException("Test endpoint not available in production.")
    code = get_last_test_code(current_user.id, channel)
    if not code:
        raise ResourceNotFoundException("No active test code found.")
    return {"code": code, "channel": channel}

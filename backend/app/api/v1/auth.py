from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import login_rate_limiter, register_rate_limiter, refresh_rate_limiter
from app.models.user import User
from app.services.auth import AuthService
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
    ChangePasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_refresh_cookie(response: Response, request: Request, raw_refresh: str):
    is_secure = settings.APP_ENV == "production" or request.url.scheme == "https"
    response.set_cookie(
        key="mend_refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limiter)]
)
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    return await service.register(
        email=data.email,
        password=data.password,
        display_name=data.display_name,
        timezone_str=data.timezone or "Asia/Kolkata"
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(login_rate_limiter)]
)
async def login(
    data: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    user_agent = request.headers.get("user-agent")
    token_resp, raw_refresh = await service.login(
        email=data.email,
        password=data.password,
        user_agent=user_agent
    )

    # Set httpOnly refresh cookie
    set_refresh_cookie(response, request, raw_refresh)
    return token_resp


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(refresh_rate_limiter)])
async def refresh_token(
    request: Request,
    response: Response,
    data: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    cookie_token = request.cookies.get("mend_refresh_token")
    raw_token = (data.refresh_token if data and data.refresh_token else None) or cookie_token

    if not raw_token:
        from app.core.errors import AuthenticationFailedException
        raise AuthenticationFailedException("No refresh token provided")

    service = AuthService(db)
    user_agent = request.headers.get("user-agent")
    token_resp, new_raw_refresh = await service.refresh_token(raw_token, user_agent=user_agent)

    # Only update cookie if a new token was issued (outside grace window)
    if new_raw_refresh:
        set_refresh_cookie(response, request, new_raw_refresh)
    return token_resp


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    cookie_token = request.cookies.get("mend_refresh_token")
    service = AuthService(db)
    await service.logout(cookie_token)
    is_secure = settings.APP_ENV == "production" or request.url.scheme == "https"
    response.delete_cookie(
        "mend_refresh_token",
        path="/api/v1/auth",
        httponly=True,
        secure=is_secure,
        samesite="lax"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    await service.logout_all(current_user.id)
    response.delete_cookie("mend_refresh_token", path="/api/v1/auth")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    await service.change_password(
        user_id=current_user.id,
        current_password=data.current_password,
        new_password=data.new_password
    )
    # Clear cookie since all refresh sessions are revoked
    response.delete_cookie("mend_refresh_token", path="/api/v1/auth")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

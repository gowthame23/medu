from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.auth import AuthService
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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


@router.post("/login", response_model=TokenResponse)
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
    response.set_cookie(
        key="mend_refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=False,  # Set True in production over HTTPS
        samesite="lax",
        max_age=30 * 86400
    )
    return token_resp


@router.post("/refresh", response_model=TokenResponse)
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

    response.set_cookie(
        key="mend_refresh_token",
        value=new_raw_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 86400
    )
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
    response.delete_cookie("mend_refresh_token")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

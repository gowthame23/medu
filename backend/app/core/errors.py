from typing import Any, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class MendAppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details


class AuthenticationFailedException(MendAppException):
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_FAILED",
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenRevokedOrExpiredException(MendAppException):
    def __init__(self, message: str = "Token expired or revoked"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_REVOKED_OR_EXPIRED",
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ResourceNotFoundException(MendAppException):
    def __init__(self, resource_name: str = "Resource", message: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=message or f"{resource_name} not found",
        )


class ForbiddenException(MendAppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
        )


class ConflictException(MendAppException):
    def __init__(self, code: str = "CONFLICT", message: str = "Conflict detected"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code=code,
            message=message,
        )


class RateLimitExceededException(MendAppException):
    def __init__(self, retry_after_seconds: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please slow down and try again.",
            headers={"Retry-After": str(retry_after_seconds)},
        )


class UnprocessableFinancialEntityException(MendAppException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_FINANCIAL_FORMAT",
            message=message,
        )

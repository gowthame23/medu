from decimal import Decimal
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Mend"
    APP_ENV: str = "development"  # development, testing, production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./mend.db"
    DATABASE_URL_SYNC: str = "sqlite:///./mend.db"

    # Security
    SECRET_KEY: str = "dev-insecure-secret-key-change-in-production-mend-2026-xyz"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MIN_PASSWORD_LENGTH: int = 10

    # Rate Limiting
    RATE_LIMIT_LOGIN_PER_MIN: int = 5
    RATE_LIMIT_REGISTER_PER_MIN: int = 5

    # Payments & Sandbox
    ENABLE_SANDBOX_PAYMENTS: bool = True

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Timezone
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    @field_validator("ENABLE_SANDBOX_PAYMENTS")
    @classmethod
    def validate_sandbox_in_production(cls, v: bool, info) -> bool:
        env = info.data.get("APP_ENV")
        if env == "production" and v is True:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "ENABLE_SANDBOX_PAYMENTS cannot be true when APP_ENV is production."
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key_in_production(cls, v: str, info) -> str:
        env = info.data.get("APP_ENV")
        if env == "production" and ("dev-insecure" in v or len(v) < 32):
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "Production requires a strong SECRET_KEY of at least 32 characters."
            )
        return v


settings = Settings()

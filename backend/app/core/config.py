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
    DEBUG: bool = False
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
    RATE_LIMIT_REFRESH_PER_MIN: int = 30
    RATE_LIMIT_INVITE_ACCEPT_PER_MIN: int = 10
    RATE_LIMIT_MAX_TRACKED_IPS: int = 10000

    # Reverse Proxy & Network Security
    TRUSTED_PROXIES: List[str] = ["127.0.0.1", "::1"]

    # Payments & Sandbox
    PAYMENT_PROVIDER: str = "SANDBOX_UPI"
    ENABLE_SANDBOX_PAYMENTS: bool = True
    WEBHOOK_SECRET: str = "dev-insecure-webhook-secret-2026"

    # Verification & Notification Providers
    EMAIL_PROVIDER: str = "console"  # console, smtp
    SMS_PROVIDER: str = "console"    # console

    # SMTP Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@mend.local"
    SMTP_USE_TLS: bool = True

    # Verification Policies & Bounds
    VERIFICATION_CODE_TTL_MINUTES: int = 10
    VERIFICATION_MAX_ATTEMPTS: int = 5
    VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60
    VERIFICATION_HOURLY_CAP: int = 5

    # Payment Gating Policies
    REQUIRE_EMAIL_VERIFICATION_FOR_PAYMENTS: bool = True
    REQUIRE_PHONE_VERIFICATION_FOR_PAYMENTS: bool = False

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

    @field_validator("WEBHOOK_SECRET")
    @classmethod
    def validate_webhook_secret_in_production(cls, v: str, info) -> str:
        env = info.data.get("APP_ENV")
        if env == "production" and ("dev-insecure" in v or len(v) < 32):
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "Production requires a strong WEBHOOK_SECRET of at least 32 characters."
            )
        return v

    @field_validator("EMAIL_PROVIDER")
    @classmethod
    def validate_email_provider_in_production(cls, v: str, info) -> str:
        env = info.data.get("APP_ENV")
        if env == "production" and v == "console":
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "EMAIL_PROVIDER cannot be 'console' when APP_ENV is production."
            )
        return v

    @field_validator("SMS_PROVIDER")
    @classmethod
    def validate_sms_provider_in_production(cls, v: str, info) -> str:
        env = info.data.get("APP_ENV")
        if env == "production" and v == "console":
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "SMS_PROVIDER cannot be 'console' when APP_ENV is production."
            )
        return v


settings = Settings()

import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "sarah@example.com",
        "password": "StrongPassword2026!",
        "display_name": "Sarah Connor",
        "timezone": "Asia/Kolkata"
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "sarah@example.com"
    assert user_data["display_name"] == "Sarah Connor"
    assert "password" not in user_data
    assert "password_hash" not in user_data

    # 2. Login
    login_payload = {
        "email": "sarah@example.com",
        "password": "StrongPassword2026!"
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert "mend_refresh_token" in login_res.cookies

    refresh_token = login_res.cookies["mend_refresh_token"]

    # 3. Refresh with rotation
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_res.status_code == 200
    new_token_data = refresh_res.json()
    assert "access_token" in new_token_data
    new_refresh_token = refresh_res.cookies["mend_refresh_token"]
    assert new_refresh_token != refresh_token

    # 4. GRACE WINDOW: Replay within grace window returns fresh access token without touching cookie
    grace_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert grace_res.status_code == 200
    assert "access_token" in grace_res.json()
    assert "mend_refresh_token" not in grace_res.cookies  # Cookie is untouched in grace window

    # 5. REUSE DETECTION: Replaying token outside grace window MUST revoke entire chain!
    # Artificially age the revoked token beyond the 30s grace window
    from tests.conftest import TestAsyncSessionLocal
    from app.core.security import hash_token
    from app.models.user import RefreshToken
    from sqlalchemy import update
    from datetime import datetime, timezone, timedelta

    async with TestAsyncSessionLocal() as session:
        old_hash = hash_token(refresh_token)
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == old_hash)
            .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=60))
        )
        await session.commit()

    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert replay_res.status_code == 401
    assert "Revoked token reuse detected" in replay_res.json()["error"]["message"]

    # Now even the newest token is invalid due to chain revocation
    newest_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh_token}
    )
    assert newest_res.status_code == 401


@pytest.mark.asyncio
async def test_registration_enumeration_safe(client: AsyncClient):
    payload = {
        "email": "enum_safe@example.com",
        "password": "StrongPassword2026!",
        "display_name": "Enum Safe",
        "timezone": "Asia/Kolkata"
    }
    # 1st registration
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201
    assert res1.json()["email"] == "enum_safe@example.com"

    # 2nd registration with same email returns 201 without revealing prior existence
    # and NEVER leaks the real user id or original created_at
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 201
    assert res2.json()["email"] == "enum_safe@example.com"
    assert res2.json()["id"] != res1.json()["id"]  # Real account UUID is not leaked!
    assert set(res1.json().keys()) == set(res2.json().keys())


@pytest.mark.asyncio
async def test_invalid_timezone_validation(client: AsyncClient):
    payload = {
        "email": "mars@example.com",
        "password": "StrongPassword2026!",
        "display_name": "Martian User",
        "timezone": "Mars/Olympus"
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422
    assert "Invalid IANA timezone" in str(res.json())


@pytest.mark.asyncio
async def test_rate_limiting_login(client: AsyncClient):
    login_payload = {
        "email": "ratelimit_target@example.com",
        "password": "WrongPassword123!"
    }
    headers = {"X-Forwarded-For": "198.51.100.42"}

    # First 5 attempts return 401
    for _ in range(5):
        res = await client.post("/api/v1/auth/login", json=login_payload, headers=headers)
        assert res.status_code == 401

    # 6th attempt trips rate limit returning 429
    res6 = await client.post("/api/v1/auth/login", json=login_payload, headers=headers)
    assert res6.status_code == 429
    assert "Too many attempts" in res6.json()["error"]["message"]


@pytest.mark.asyncio
async def test_origin_csrf_check(client: AsyncClient):
    # 1. Untrusted cross-origin request rejected with 403
    headers = {"Origin": "https://malicious-attacker.com"}
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "attacker@example.com", "password": "Password123!"},
        headers=headers
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 2. In production, missing Origin/Referer is rejected with 403
    orig_env = settings.APP_ENV
    try:
        settings.APP_ENV = "production"
        res_no_origin = await client.post(
            "/api/v1/auth/login",
            json={"email": "attacker@example.com", "password": "Password123!"}
        )
        assert res_no_origin.status_code == 403
        # 3. Only the exact `/api/v1/payments/webhook` route is exempt from Origin check;
        # arbitrary endpoints ending with `/webhook` are strictly NOT exempt in production
        fake_webhook_res = await client.post(
            "/api/v1/fake/webhook",
            json={"fake": True}
        )
        assert fake_webhook_res.status_code == 403
        assert "Missing Origin header" in fake_webhook_res.json()["error"]["message"]
    finally:
        settings.APP_ENV = orig_env


def test_production_guards_against_insecure_secrets():
    import pytest
    from app.core.config import Settings

    # Refuses to start in production with default dev SECRET_KEY
    with pytest.raises(ValueError, match="Production requires a strong SECRET_KEY"):
        Settings(
            APP_ENV="production",
            ENABLE_SANDBOX_PAYMENTS=False,
            SECRET_KEY="dev-insecure-key",
            WEBHOOK_SECRET="secure-prod-webhook-secret-min-32-chars-long"
        )

    # Refuses to start in production with default dev WEBHOOK_SECRET
    with pytest.raises(ValueError, match="Production requires a strong WEBHOOK_SECRET"):
        Settings(
            APP_ENV="production",
            ENABLE_SANDBOX_PAYMENTS=False,
            SECRET_KEY="secure-prod-secret-key-minimum-32-chars-long",
            WEBHOOK_SECRET="dev-insecure-webhook-secret-2026"
        )

    # Refuses to start in production with console EMAIL_PROVIDER
    with pytest.raises(ValueError, match="EMAIL_PROVIDER cannot be 'console'"):
        Settings(
            APP_ENV="production",
            ENABLE_SANDBOX_PAYMENTS=False,
            SECRET_KEY="secure-prod-secret-key-minimum-32-chars-long",
            WEBHOOK_SECRET="secure-prod-webhook-secret-min-32-chars-long",
            EMAIL_PROVIDER="console",
            SMS_PROVIDER="dummy"
        )

    # Refuses to start in production with console SMS_PROVIDER
    with pytest.raises(ValueError, match="SMS_PROVIDER cannot be 'console'"):
        Settings(
            APP_ENV="production",
            ENABLE_SANDBOX_PAYMENTS=False,
            SECRET_KEY="secure-prod-secret-key-minimum-32-chars-long",
            WEBHOOK_SECRET="secure-prod-webhook-secret-min-32-chars-long",
            EMAIL_PROVIDER="smtp",
            SMS_PROVIDER="console"
        )


@pytest.mark.asyncio
async def test_users_me_verification_status(client: AsyncClient, create_user_fixture):
    """Asserts that GET /users/me and GET /me expose email_verified and phone_verified booleans."""
    user, token = await create_user_fixture("status_check@example.com", "Status User")
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # Initially unverified
    res1 = await client.get("/api/v1/users/me", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["email_verified"] is False
    assert data1["phone_verified"] is False

    res_alias = await client.get("/api/v1/me", headers=headers)
    assert res_alias.status_code == 200
    assert res_alias.json()["email_verified"] is False

    # Send and confirm email
    await client.post("/api/v1/verification/email/send", headers=headers)
    code_res = await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)
    code = code_res.json()["code"]
    await client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)

    # Now email_verified is True
    res2 = await client.get("/api/v1/users/me", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["email_verified"] is True
    assert data2["phone_verified"] is False

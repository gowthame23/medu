import pytest
from httpx import AsyncClient


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

    # 4. REUSE DETECTION: Replaying old revoked token MUST revoke entire chain!
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

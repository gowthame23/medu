import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_unverified_email_blocked_on_pay_and_mark_paid(client: AsyncClient, create_user_fixture):
    """Unverified email user receives 403 with EMAIL_NOT_VERIFIED on pay and mark-paid."""
    user, token = await create_user_fixture("unverified_payer@example.com", "Unverified Payer", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # Create bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Wifi Broadband", "amount": "999.00", "due_date": "2026-11-28"},
        headers=headers
    )
    assert bill_res.status_code in (200, 201)
    bill_id = bill_res.json()["id"]

    # Attempt pay -> 403 EMAIL_NOT_VERIFIED
    pay_res = await client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "unver_pay_key_1"}
    )
    assert pay_res.status_code == 403
    err_body = pay_res.json()["error"]
    assert err_body["code"] == "EMAIL_NOT_VERIFIED"

    # Attempt mark-paid -> 403 EMAIL_NOT_VERIFIED
    mark_res = await client.post(f"/api/v1/bills/{bill_id}/mark-paid", headers=headers)
    assert mark_res.status_code == 403
    assert mark_res.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_verified_user_passes_pay_and_mark_paid(client: AsyncClient, create_user_fixture):
    """Verified user succeeds on pay and mark-paid."""
    user, token = await create_user_fixture("verified_payer@example.com", "Verified Payer", email_verified=True)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # Create bill 1 to pay
    b1_res = await client.post(
        "/api/v1/bills",
        json={"title": "Electricity", "amount": "1200.00", "due_date": "2026-11-28"},
        headers=headers
    )
    assert b1_res.status_code in (200, 201)
    b1_id = b1_res.json()["id"]

    pay_res = await client.post(
        f"/api/v1/bills/{b1_id}/pay",
        headers={**headers, "Idempotency-Key": "ver_pay_key_1"}
    )
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "SUCCESS"

    # Create bill 2 to mark paid
    b2_res = await client.post(
        "/api/v1/bills",
        json={"title": "Water", "amount": "300.00", "due_date": "2026-11-28"},
        headers=headers
    )
    assert b2_res.status_code in (200, 201)
    b2_id = b2_res.json()["id"]

    mark_res = await client.post(f"/api/v1/bills/{b2_id}/mark-paid", headers=headers)
    assert mark_res.status_code == 200
    assert mark_res.json()["is_paid"] is True


@pytest.mark.asyncio
async def test_flags_off_means_no_gating(client: AsyncClient, create_user_fixture, monkeypatch):
    """When REQUIRE_EMAIL_VERIFICATION_FOR_PAYMENTS=False, unverified user is not blocked."""
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION_FOR_PAYMENTS", False)
    monkeypatch.setattr(settings, "REQUIRE_PHONE_VERIFICATION_FOR_PAYMENTS", False)

    user, token = await create_user_fixture("ungated_unver@example.com", "Ungated User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    b_res = await client.post(
        "/api/v1/bills",
        json={"title": "Gas Cylinder", "amount": "850.00", "due_date": "2026-11-28"},
        headers=headers
    )
    assert b_res.status_code in (200, 201)
    b_id = b_res.json()["id"]

    pay_res = await client.post(
        f"/api/v1/bills/{b_id}/pay",
        headers={**headers, "Idempotency-Key": "ungated_pay_1"}
    )
    assert pay_res.status_code == 200


@pytest.mark.asyncio
async def test_phone_gating_flag(client: AsyncClient, create_user_fixture, monkeypatch):
    """When REQUIRE_PHONE_VERIFICATION_FOR_PAYMENTS=True, phone unverified user is blocked."""
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION_FOR_PAYMENTS", True)
    monkeypatch.setattr(settings, "REQUIRE_PHONE_VERIFICATION_FOR_PAYMENTS", True)

    # User with verified email but unverified phone
    user, token = await create_user_fixture(
        "phone_check@example.com", "Phone Payer",
        email_verified=True,
        phone_e164="+919876543210",
        phone_verified=False
    )
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    b_res = await client.post(
        "/api/v1/bills",
        json={"title": "Mobile Bill", "amount": "499.00", "due_date": "2026-11-28"},
        headers=headers
    )
    assert b_res.status_code in (200, 201)
    b_id = b_res.json()["id"]

    pay_res = await client.post(
        f"/api/v1/bills/{b_id}/pay",
        headers={**headers, "Idempotency-Key": "phone_gated_pay_1"}
    )
    assert pay_res.status_code == 403
    assert pay_res.json()["error"]["code"] == "PHONE_NOT_VERIFIED"

    # User with both email and phone verified
    user2, token2 = await create_user_fixture(
        "both_ver@example.com", "Both Ver Payer",
        email_verified=True,
        phone_e164="+919876543211",
        phone_verified=True
    )
    headers2 = {"Authorization": f"Bearer {token2}", "Origin": "http://testserver"}

    b2_res = await client.post(
        "/api/v1/bills",
        json={"title": "Mobile Bill 2", "amount": "499.00", "due_date": "2026-11-28"},
        headers=headers2
    )
    assert b2_res.status_code in (200, 201)
    b2_id = b2_res.json()["id"]

    pay2_res = await client.post(
        f"/api/v1/bills/{b2_id}/pay",
        headers={**headers2, "Idempotency-Key": "both_ver_pay_1"}
    )
    assert pay2_res.status_code == 200


@pytest.mark.asyncio
async def test_login_and_other_endpoints_stay_allowed_for_unverified(client: AsyncClient):
    """Unverified users can log in, create daily logs, manage families, etc."""
    # Register a new user (which starts unverified)
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "unverified_active@example.com",
            "password": "SecurePassword123!",
            "display_name": "Active Unverified"
        },
        headers={"Origin": "http://testserver"}
    )
    assert reg_res.status_code in (200, 201)

    # Login works
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "unverified_active@example.com", "password": "SecurePassword123!"},
        headers={"Origin": "http://testserver"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # Profile works
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email_verified"] is False

    # Create bill works
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Gym Membership", "amount": "2500.00", "due_date": "2026-12-01"},
        headers=headers
    )
    assert bill_res.status_code in (200, 201)

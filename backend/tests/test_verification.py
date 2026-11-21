import os
import uuid
import asyncio
import json
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.models.verification import VerificationChallenge
from app.models.audit import AuditLog
from app.models.outbox import OutboxEvent
from backend.tests.conftest import TestAsyncSessionLocal


@pytest.mark.asyncio
async def test_happy_path_email_verification(client: AsyncClient, create_user_fixture):
    """Happy path: send email code, retrieve via test helper, confirm successfully."""
    user, token = await create_user_fixture("happy_email@example.com", "Happy Email", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # 1. Send code -> 202
    send_res = await client.post("/api/v1/verification/email/send", headers=headers)
    assert send_res.status_code == 202
    assert send_res.json()["status"] == "accepted"

    # 2. Get code
    code_res = await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)
    assert code_res.status_code == 200
    code = code_res.json()["code"]
    assert len(code) == 6

    # 3. Confirm code -> 200
    confirm_res = await client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "confirmed"
    assert confirm_res.json()["channel"] == "email"

    # 4. Check user profile
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_happy_path_phone_verification(client: AsyncClient, create_user_fixture):
    """Happy path: send phone code, retrieve via test helper, confirm successfully."""
    user, token = await create_user_fixture("happy_phone@example.com", "Happy Phone", email_verified=True)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # 1. Send code to 10-digit number (normalized to +91)
    send_res = await client.post(
        "/api/v1/verification/phone/send",
        json={"phone": "9876543210"},
        headers=headers
    )
    assert send_res.status_code == 202

    # 2. Get code
    code_res = await client.get("/api/v1/verification/test-last-code?channel=phone", headers=headers)
    assert code_res.status_code == 200
    code = code_res.json()["code"]

    # 3. Confirm code
    confirm_res = await client.post("/api/v1/verification/phone/confirm", json={"code": code}, headers=headers)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "confirmed"
    assert confirm_res.json()["channel"] == "phone"

    # 4. Check user profile
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["phone_verified"] is True
    assert me_res.json()["phone_e164"] == "+919876543210"


@pytest.mark.asyncio
async def test_wrong_code_increments_attempts_and_locks_after_5(client: AsyncClient, create_user_fixture):
    """Wrong code increments attempts; on 5th attempt locks challenge and blocks subsequent attempts."""
    user, token = await create_user_fixture("lock_test@example.com", "Lock User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    await client.post("/api/v1/verification/email/send", headers=headers)
    code = (await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)).json()["code"]

    # Attempts 1 to 4 with wrong code
    for i in range(1, 5):
        res = await client.post("/api/v1/verification/email/confirm", json={"code": "000000"}, headers=headers)
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"

        # Check DB attempts
        async with TestAsyncSessionLocal() as session:
            c = (await session.execute(
                select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
            )).scalar_one()
            assert c.attempts == i

    # 5th wrong attempt -> locks
    res5 = await client.post("/api/v1/verification/email/confirm", json={"code": "000000"}, headers=headers)
    assert res5.status_code == 400
    assert res5.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"

    async with TestAsyncSessionLocal() as session:
        c = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalar_one()
        assert c.attempts == 5

    # 6th attempt with the CORRECT code is now rejected because it's locked
    res_correct = await client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)
    assert res_correct.status_code == 400
    assert res_correct.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"


@pytest.mark.asyncio
async def test_expired_code_rejected(client: AsyncClient, create_user_fixture):
    """Expired challenge returns 400 INVALID_OR_EXPIRED_CODE."""
    user, token = await create_user_fixture("exp_test@example.com", "Exp User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    await client.post("/api/v1/verification/email/send", headers=headers)
    code = (await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)).json()["code"]

    # Expire challenge in database
    async with TestAsyncSessionLocal() as session:
        c = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalar_one()
        c.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        await session.commit()

    confirm_res = await client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)
    assert confirm_res.status_code == 400
    assert confirm_res.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"


@pytest.mark.asyncio
async def test_resend_cooldown_and_hourly_cap(client: AsyncClient, create_user_fixture):
    """Resend cooldown (60s) suppresses immediate second send; hourly cap limits to 5/hr."""
    user, token = await create_user_fixture("cooldown_test@example.com", "Cooldown User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # 1. First send -> succeeds
    res1 = await client.post("/api/v1/verification/email/send", headers=headers)
    assert res1.status_code == 202

    # Immediate second send within 60s cooldown -> returns 202, but does NOT create new challenge
    res2 = await client.post("/api/v1/verification/email/send", headers=headers)
    assert res2.status_code == 202

    async with TestAsyncSessionLocal() as session:
        challenges = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalars().all()
        assert len(challenges) == 1

    # Simulate fast-forwarding time to test hourly cap
    for i in range(2, 6):
        # Age all previous challenges by 70 seconds
        async with TestAsyncSessionLocal() as session:
            all_c = (await session.execute(
                select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
            )).scalars().all()
            for c in all_c:
                c.created_at = c.created_at - timedelta(seconds=70)
            await session.commit()

        send_res = await client.post("/api/v1/verification/email/send", headers=headers)
        assert send_res.status_code == 202

    # Now we have 5 challenges in the 1-hour window
    async with TestAsyncSessionLocal() as session:
        challenges = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalars().all()
        assert len(challenges) == 5

    # Age them by 70s so cooldown is cleared, but all 5 remain within the last 1 hour
    async with TestAsyncSessionLocal() as session:
        all_c = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalars().all()
        for c in all_c:
            c.created_at = c.created_at - timedelta(seconds=70)
        await session.commit()

    # 6th send is blocked by hourly cap -> returns 202 but challenge count stays 5
    res6 = await client.post("/api/v1/verification/email/send", headers=headers)
    assert res6.status_code == 202

    async with TestAsyncSessionLocal() as session:
        challenges = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalars().all()
        assert len(challenges) == 5


@pytest.mark.asyncio
async def test_new_send_invalidates_old_code(client: AsyncClient, create_user_fixture):
    """Issuing a new verification challenge invalidates the previous challenge code."""
    user, token = await create_user_fixture("inval_test@example.com", "Inval User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # Send first code
    await client.post("/api/v1/verification/email/send", headers=headers)
    code1 = (await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)).json()["code"]

    # Clear cooldown by aging challenge
    async with TestAsyncSessionLocal() as session:
        c = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalar_one()
        c.created_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        await session.commit()

    # Send second code
    await client.post("/api/v1/verification/email/send", headers=headers)
    code2 = (await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)).json()["code"]
    assert code1 != code2

    # Attempt to confirm code1 -> fails
    res1 = await client.post("/api/v1/verification/email/confirm", json={"code": code1}, headers=headers)
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"

    # Confirm code2 -> succeeds
    res2 = await client.post("/api/v1/verification/email/confirm", json={"code": code2}, headers=headers)
    assert res2.status_code == 200


@pytest.mark.asyncio
async def test_replay_of_consumed_code_fails(client: AsyncClient, create_user_fixture):
    """A successfully consumed verification code cannot be replayed."""
    user, token = await create_user_fixture("replay_test@example.com", "Replay User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    await client.post("/api/v1/verification/email/send", headers=headers)
    code = (await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)).json()["code"]

    # First confirm -> 200 OK
    res1 = await client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)
    assert res1.status_code == 200

    # Second confirm with same code -> 400 INVALID_OR_EXPIRED_CODE
    res2 = await client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "INVALID_OR_EXPIRED_CODE"


@pytest.mark.asyncio
async def test_phone_taken_by_another_verified_user_is_enumeration_safe(client: AsyncClient, create_user_fixture):
    """A phone already verified by another user returns generic 202 and sends nothing."""
    # User A verifies phone
    user_a, token_a = await create_user_fixture(
        "user_a@example.com", "User A",
        phone_e164="+919999988888",
        phone_verified=True
    )

    # User B attempts to verify the same phone
    user_b, token_b = await create_user_fixture("user_b@example.com", "User B", phone_verified=False)
    headers_b = {"Authorization": f"Bearer {token_b}", "Origin": "http://testserver"}

    send_res = await client.post(
        "/api/v1/verification/phone/send",
        json={"phone": "+91 99999-88888"},
        headers=headers_b
    )
    # Generic 202 response
    assert send_res.status_code == 202
    assert send_res.json()["status"] == "accepted"

    # Verify that NO challenge was created for user B
    async with TestAsyncSessionLocal() as session:
        challenges_b = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user_b.id)
        )).scalars().all()
        assert len(challenges_b) == 0


@pytest.mark.asyncio
async def test_phone_normalization_and_validation(client: AsyncClient, create_user_fixture):
    """Phone normalization handles bare 10-digits, spaces, hyphens, and rejects invalid formats."""
    user, token = await create_user_fixture("norm_test@example.com", "Norm User")
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    # Bare 10-digit number -> accepted and normalized to +91
    res1 = await client.post("/api/v1/verification/phone/send", json={"phone": "9812345678"}, headers=headers)
    assert res1.status_code == 202

    # Clear cooldown
    async with TestAsyncSessionLocal() as session:
        c = (await session.execute(
            select(VerificationChallenge).where(VerificationChallenge.user_id == user.id)
        )).scalar_one()
        c.created_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        await session.commit()

    # Formatted with spaces and dashes -> accepted
    res2 = await client.post("/api/v1/verification/phone/send", json={"phone": "+91 98123-45679"}, headers=headers)
    assert res2.status_code == 202

    # Invalid string -> 422
    res_inv1 = await client.post("/api/v1/verification/phone/send", json={"phone": "123"}, headers=headers)
    assert res_inv1.status_code == 422

    res_inv2 = await client.post("/api/v1/verification/phone/send", json={"phone": "not-a-number"}, headers=headers)
    assert res_inv2.status_code == 422


@pytest.mark.asyncio
async def test_production_guard_on_test_last_code_returns_404(client: AsyncClient, create_user_fixture, monkeypatch):
    """The test-only helper endpoint must be impossible in production and return 404."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "APP_ENV", "production")

    user, token = await create_user_fixture("prod_guard@example.com", "Prod Guard User")
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    res = await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_concurrent_confirm_race_condition(client: AsyncClient, create_user_fixture):
    """
    Two simultaneous confirms of the exact same code give exactly one 200 and one 400.
    Validated with row-level locks on PostgreSQL.
    """
    user, token = await create_user_fixture("race_confirm@example.com", "Race Confirm User", email_verified=False)
    headers = {"Authorization": f"Bearer {token}", "Origin": "http://testserver"}

    await client.post("/api/v1/verification/email/send", headers=headers)
    code = (await client.get("/api/v1/verification/test-last-code?channel=email", headers=headers)).json()["code"]

    req1 = client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)
    req2 = client.post("/api/v1/verification/email/confirm", json={"code": code}, headers=headers)

    res1, res2 = await asyncio.gather(req1, req2)
    status_codes = sorted([res1.status_code, res2.status_code])
    assert status_codes == [200, 400], f"Expected exactly one 200 and one 400, got {status_codes}"

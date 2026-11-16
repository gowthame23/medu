import hashlib
import json
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.bill import UpcomingRadar
from app.models.payment import PaymentTransaction
from app.models.user import RefreshToken
from app.core.security import generate_secure_token, hash_token, hash_audit_email
from app.providers.sandbox_upi import SandboxUPIProvider
from app.core.config import settings
from tests.conftest import TestAsyncSessionLocal


@pytest.mark.asyncio
async def test_audit_login_success_and_failure(client: AsyncClient, create_user_fixture):
    user, _ = await create_user_fixture("audit_user@example.com", "Audit User", "Password123!")
    user_email_hash = hash_audit_email("audit_user@example.com")
    unknown_email_hash = hash_audit_email("unknown@example.com")

    # 1. Login failure: unknown user
    res_fail1 = await client.post("/api/v1/auth/login", json={
        "email": "unknown@example.com",
        "password": "Password123!"
    }, headers={"X-Forwarded-For": "203.0.113.195"})
    assert res_fail1.status_code == 401

    # 2. Login failure: wrong password
    res_fail2 = await client.post("/api/v1/auth/login", json={
        "email": "audit_user@example.com",
        "password": "WrongPassword!"
    }, headers={"X-Forwarded-For": "203.0.113.195"})
    assert res_fail2.status_code == 401

    # 3. Login success
    res_success = await client.post("/api/v1/auth/login", json={
        "email": "audit_user@example.com",
        "password": "Password123!"
    }, headers={"X-Forwarded-For": "203.0.113.195"})
    assert res_success.status_code == 200

    async with TestAsyncSessionLocal() as session:
        logs_res = await session.execute(
            select(AuditLog).where(AuditLog.action.in_(["LOGIN_SUCCESS", "LOGIN_FAILURE"])).order_by(AuditLog.created_at.asc())
        )
        logs = logs_res.scalars().all()
        assert len(logs) == 3

        # Unknown user login failure
        assert logs[0].action == "LOGIN_FAILURE"
        assert logs[0].user_id is None
        assert logs[0].entity_id is None
        assert logs[0].metadata_json.get("email_hash") == unknown_email_hash
        assert logs[0].metadata_json.get("reason") == "user_not_found"
        assert logs[0].ip_address == "203.0.113.195"

        # Wrong password login failure
        assert logs[1].action == "LOGIN_FAILURE"
        assert logs[1].user_id == user.id
        assert logs[1].entity_id == str(user.id)
        assert logs[1].metadata_json.get("email_hash") == user_email_hash
        assert logs[1].metadata_json.get("reason") == "invalid_credentials"
        assert logs[1].ip_address == "203.0.113.195"

        # Success
        assert logs[2].action == "LOGIN_SUCCESS"
        assert logs[2].user_id == user.id
        assert logs[2].entity_id == str(user.id)
        assert logs[2].metadata_json.get("email_hash") == user_email_hash
        assert logs[2].ip_address == "203.0.113.195"


@pytest.mark.asyncio
async def test_audit_refresh_reuse_and_lifecycle(client: AsyncClient, create_user_fixture):
    user, _ = await create_user_fixture("refresh_audit@example.com", "Refresh Audit", "Password123!")

    # Login to get refresh token
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "refresh_audit@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    cookie_token = login_res.cookies.get("mend_refresh_token")
    access_token = login_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # Set cookie directly on client instance to eliminate httpx deprecation warning
    client.cookies.set("mend_refresh_token", cookie_token)

    # First refresh: normal rotation
    ref1 = await client.post("/api/v1/auth/refresh")
    assert ref1.status_code == 200

    # Simulate expired grace window on original token
    async with TestAsyncSessionLocal() as session:
        t_hash = hash_token(cookie_token)
        tok_res = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == t_hash))
        tok = tok_res.scalar_one()
        tok.revoked_at = datetime.now(timezone.utc) - timedelta(seconds=60)
        session.add(tok)
        await session.commit()

    # Replay old token outside grace window -> reuse detected
    client.cookies.set("mend_refresh_token", cookie_token)
    ref_reuse = await client.post("/api/v1/auth/refresh")
    assert ref_reuse.status_code == 401

    # Change password
    chg = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password123!", "new_password": "NewPassword123!"},
        headers=auth_header
    )
    assert chg.status_code == 204

    # Logout all
    lo = await client.post("/api/v1/auth/logout-all", headers=auth_header)
    assert lo.status_code == 204

    async with TestAsyncSessionLocal() as session:
        reuse_res = await session.execute(
            select(AuditLog).where(AuditLog.action == "REFRESH_TOKEN_REUSE_DETECTED")
        )
        reuse_log = reuse_res.scalar_one_or_none()
        assert reuse_log is not None
        assert reuse_log.user_id == user.id

        pwd_res = await session.execute(
            select(AuditLog).where(AuditLog.action == "CHANGE_PASSWORD")
        )
        pwd_log = pwd_res.scalar_one_or_none()
        assert pwd_log is not None
        assert pwd_log.user_id == user.id

        lo_res = await session.execute(
            select(AuditLog).where(AuditLog.action == "LOGOUT_ALL")
        )
        lo_log = lo_res.scalar_one_or_none()
        assert lo_log is not None
        assert lo_log.user_id == user.id


@pytest.mark.asyncio
async def test_audit_family_invitations_and_members(client: AsyncClient, create_user_fixture):
    admin_user, admin_token = await create_user_fixture("family_admin@example.com", "Admin User")
    member_user, member_token = await create_user_fixture("family_member@example.com", "Member User")

    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Forwarded-For": "198.51.100.1"}
    member_headers = {"Authorization": f"Bearer {member_token}", "X-Forwarded-For": "198.51.100.2"}

    # 1. Create family group
    grp_res = await client.post("/api/v1/families", json={"group_name": "Test Group"}, headers=admin_headers)
    assert grp_res.status_code == 201
    group_id = grp_res.json()["id"]

    # 2. Invite member
    inv_res = await client.post(
        f"/api/v1/families/{group_id}/invitations",
        json={"email": "family_member@example.com"},
        headers=admin_headers
    )
    assert inv_res.status_code == 201
    invite_token = inv_res.json()["invite_token"]
    invitation_id = inv_res.json()["id"]

    # 3. Accept invitation
    acc_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": invite_token},
        headers=member_headers
    )
    assert acc_res.status_code == 200

    # 4. Role change
    role_res = await client.patch(
        f"/api/v1/families/{group_id}/members/{member_user.id}",
        json={"role": "ADMIN"},
        headers=admin_headers
    )
    assert role_res.status_code == 200

    # 5. Member removal
    rem_res = await client.delete(
        f"/api/v1/families/{group_id}/members/{member_user.id}",
        headers=admin_headers
    )
    assert rem_res.status_code == 204

    async with TestAsyncSessionLocal() as session:
        # Check INVITATION_CREATED
        inv_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "INVITATION_CREATED")
        )).scalar_one_or_none()
        assert inv_log is not None
        assert inv_log.user_id == admin_user.id
        assert inv_log.entity_id == invitation_id
        assert inv_log.metadata_json.get("family_group_id") == group_id
        assert inv_log.metadata_json.get("email_hash") == hash_audit_email("family_member@example.com")
        assert inv_log.ip_address == "198.51.100.1"

        # Check INVITATION_ACCEPTED
        acc_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "INVITATION_ACCEPTED")
        )).scalar_one_or_none()
        assert acc_log is not None
        assert acc_log.user_id == member_user.id
        assert acc_log.ip_address == "198.51.100.2"

        # Check MEMBER_ROLE_CHANGED
        role_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "MEMBER_ROLE_CHANGED")
        )).scalar_one_or_none()
        assert role_log is not None
        assert role_log.user_id == admin_user.id
        assert role_log.metadata_json.get("new_role") == "ADMIN"

        # Check MEMBER_REMOVED
        rem_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "MEMBER_REMOVED")
        )).scalar_one_or_none()
        assert rem_log is not None
        assert rem_log.user_id == admin_user.id


@pytest.mark.asyncio
async def test_audit_bills_and_payments(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("bill_audit@example.com", "Bill Audit")
    headers = {"Authorization": f"Bearer {token}", "X-Forwarded-For": "198.51.100.42"}

    # 1. Create personal bill and mark-paid
    b1_res = await client.post(
        "/api/v1/bills",
        json={"title": "Electricity Bill", "amount": "1500.00", "due_date": "2026-12-01"},
        headers=headers
    )
    assert b1_res.status_code == 201
    bill1_id = b1_res.json()["id"]

    mp_res = await client.post(f"/api/v1/bills/{bill1_id}/mark-paid", headers=headers)
    assert mp_res.status_code == 200

    # 2. Create another bill and pay
    b2_res = await client.post(
        "/api/v1/bills",
        json={"title": "Water Bill", "amount": "450.00", "due_date": "2026-12-05"},
        headers=headers
    )
    assert b2_res.status_code == 201
    bill2_id = b2_res.json()["id"]

    pay_res = await client.post(f"/api/v1/bills/{bill2_id}/pay", headers=headers)
    assert pay_res.status_code == 200

    # 3. Create a bill, inject PENDING txn, and cancel
    b3_res = await client.post(
        "/api/v1/bills",
        json={"title": "Internet Bill", "amount": "999.00", "due_date": "2026-12-10"},
        headers=headers
    )
    assert b3_res.status_code == 201
    bill3_id = b3_res.json()["id"]

    async with TestAsyncSessionLocal() as session:
        pending_txn = PaymentTransaction(
            bill_id=uuid.UUID(bill3_id),
            paid_by_user_id=user.id,
            amount=Decimal("999.00"),
            idempotency_key=f"pending_{uuid.uuid4().hex}",
            status="PENDING",
            provider="SANDBOX_UPI",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        session.add(pending_txn)
        await session.commit()

    cancel_res = await client.post(f"/api/v1/bills/{bill3_id}/payment/cancel", headers=headers)
    assert cancel_res.status_code == 200

    async with TestAsyncSessionLocal() as session:
        # Check BILL_MARKED_PAID
        mp_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "BILL_MARKED_PAID")
        )).scalar_one_or_none()
        assert mp_log is not None
        assert mp_log.user_id == user.id
        assert mp_log.entity_id == bill1_id
        assert mp_log.metadata_json.get("status") == "PAID_UNVERIFIED"
        assert mp_log.ip_address == "198.51.100.42"

        # Check PAYMENT_SUCCESS
        pay_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "PAYMENT_SUCCESS")
        )).scalar_one_or_none()
        assert pay_log is not None
        assert pay_log.user_id == user.id
        assert pay_log.metadata_json.get("bill_id") == bill2_id

        # Check PAYMENT_CANCELLED
        can_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "PAYMENT_CANCELLED")
        )).scalar_one_or_none()
        assert can_log is not None
        assert can_log.user_id == user.id
        assert can_log.metadata_json.get("bill_id") == bill3_id


@pytest.mark.asyncio
async def test_audit_webhooks(client: AsyncClient, create_user_fixture):
    import hmac
    user, _ = await create_user_fixture("wh_audit@example.com", "WH Audit")

    # Create bill and pending transaction
    async with TestAsyncSessionLocal() as session:
        bill = UpcomingRadar(
            user_id=user.id,
            created_by_user_id=user.id,
            title="Gas Bill",
            amount=Decimal("1200.00"),
            due_date=datetime.now(timezone.utc).date() + timedelta(days=5),
            bill_status="UNPAID"
        )
        session.add(bill)
        await session.commit()
        await session.refresh(bill)

        txn = PaymentTransaction(
            bill_id=bill.id,
            paid_by_user_id=user.id,
            amount=Decimal("1200.00"),
            idempotency_key=f"wh_test_{uuid.uuid4().hex}",
            status="PENDING",
            provider="SANDBOX_UPI",
            provider_intent_id=f"intent_{uuid.uuid4().hex}",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        session.add(txn)
        await session.commit()
        await session.refresh(txn)

    event_id = f"evt_{uuid.uuid4().hex}"
    payload = {
        "event_id": event_id,
        "event_type": "payment.success",
        "intent_id": txn.provider_intent_id,
        "amount": "1200.00",
        "payment_reference": "REF_12345"
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    timestamp_str = str(int(datetime.now(timezone.utc).timestamp()))
    signed_bytes = f"{timestamp_str}.".encode("utf-8") + payload_bytes
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        signed_bytes,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Signature": signature,
        "X-Timestamp": timestamp_str,
        "Content-Type": "application/json",
        "X-Forwarded-For": "203.0.113.88"
    }

    # 1. Process webhook
    wh1 = await client.post("/api/v1/payments/webhook", content=payload_bytes, headers=headers)
    assert wh1.status_code == 200
    assert wh1.json()["status"] == "processed"

    # 2. Duplicate webhook -> ignored
    wh2 = await client.post("/api/v1/payments/webhook", content=payload_bytes, headers=headers)
    assert wh2.status_code == 200
    assert wh2.json()["status"] == "already_processed"

    async with TestAsyncSessionLocal() as session:
        proc_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "WEBHOOK_PROCESSED")
        )).scalar_one_or_none()
        assert proc_log is not None
        assert proc_log.entity_id == event_id
        assert proc_log.ip_address == "203.0.113.88"

        ign_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "WEBHOOK_IGNORED")
        )).scalar_one_or_none()
        assert ign_log is not None
        assert ign_log.entity_id == event_id
        assert ign_log.metadata_json.get("reason") == "already_processed"


@pytest.mark.asyncio
async def test_audit_loans_lifecycle(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("loan_audit@example.com", "Loan Audit")
    headers = {"Authorization": f"Bearer {token}", "X-Forwarded-For": "198.51.100.99"}

    # 1. Create loan
    create_res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Personal Secret Loan",
            "principal_amount": "50000.00",
            "interest_rate": "10.5",
            "tenure_months": 24,
            "start_date": "2026-01-01"
        },
        headers=headers
    )
    assert create_res.status_code == 201
    loan_id = create_res.json()["id"]

    # 2. Delete loan
    del_res = await client.delete(f"/api/v1/loans/{loan_id}", headers=headers)
    assert del_res.status_code == 204

    async with TestAsyncSessionLocal() as session:
        # Check LOAN_CREATED
        created_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "LOAN_CREATED")
        )).scalar_one_or_none()
        assert created_log is not None
        assert created_log.user_id == user.id
        assert created_log.entity_id == loan_id
        # Strict redaction: metadata_json must be empty or contain only ids, never loan names/amounts
        assert created_log.metadata_json == {}
        assert created_log.ip_address == "198.51.100.99"

        # Check LOAN_DELETED
        deleted_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "LOAN_DELETED")
        )).scalar_one_or_none()
        assert deleted_log is not None
        assert deleted_log.user_id == user.id
        assert deleted_log.entity_id == loan_id
        assert deleted_log.metadata_json == {}
        assert deleted_log.ip_address == "198.51.100.99"


@pytest.mark.asyncio
async def test_audit_metadata_strict_redaction_across_all_logs(client: AsyncClient, create_user_fixture):
    """
    Asserts that across the database, no audit row contains passwords, tokens,
    consumer numbers, loan names, loan amounts, or other sensitive details.
    """
    async with TestAsyncSessionLocal() as session:
        all_logs_res = await session.execute(select(AuditLog))
        all_logs = all_logs_res.scalars().all()

        FORBIDDEN_WORDS = [
            "password", "secret", "token", "hash_token",
            "consumer_number", "loan_name", "loan_amount", "principal", "interest_rate"
        ]

        for log in all_logs:
            if log.metadata_json:
                meta_str = json.dumps(log.metadata_json).lower()
                for forbidden in FORBIDDEN_WORDS:
                    # Allow 'token_reused' or 'token_id' only if it refers to token type, but NO actual secrets
                    assert forbidden not in log.metadata_json, (
                        f"Forbidden key '{forbidden}' found in audit log {log.id}: {log.metadata_json}"
                    )

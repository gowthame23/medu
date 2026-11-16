import os
import pytest
from httpx import AsyncClient

# Determine whether tests are running against SQLite or Postgres
is_sqlite = "sqlite" in (os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite")


@pytest.mark.asyncio
async def test_payment_idempotency_and_settlement(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("payer@test.com", "Payer User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a personal bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "BESCOM Electricity", "amount": "2450.00", "due_date": "2026-11-20"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # 2. Pay bill with Idempotency Key
    idempotency_key = "idemp_test_key_12345"
    pay_headers = {**headers, "Idempotency-Key": idempotency_key}
    pay_res = await client.post(f"/api/v1/bills/{bill_id}/pay", headers=pay_headers)
    assert pay_res.status_code == 200
    pay_data = pay_res.json()
    assert pay_data["status"] == "SUCCESS"
    assert "upi_intent_uri" in pay_data
    assert pay_data["amount"] == "2450.00"
    txn_ref = pay_data["payment_reference"]

    # 3. Retrying with SAME Idempotency Key returns the SAME result without reprocessing
    retry_res = await client.post(f"/api/v1/bills/{bill_id}/pay", headers=pay_headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["payment_reference"] == txn_ref

    # 4. Attempting to pay with a DIFFERENT key returns 409 ALREADY_PAID
    diff_key_res = await client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "different_key_999"}
    )
    assert diff_key_res.status_code == 409
    assert "already been paid" in diff_key_res.json()["error"]["message"]

    # 5. Bill is marked PAID with attribution
    detail_res = await client.get(f"/api/v1/bills/{bill_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["is_paid"] is True
    assert detail_data["bill_status"] == "PAID"
    assert detail_data["paid_by_display_name"] == "Payer User"


@pytest.mark.asyncio
async def test_concurrent_payment_race_condition(client: AsyncClient, create_user_fixture):
    """
    NOTE ON SQLITE VS POSTGRES:
    SQLite ignores 'FOR UPDATE' clauses and serializes operations via database-level locking.
    This test confirms that concurrent coroutines executed via asyncio.gather against the ASGI
    client result in one 200 (first settled) and one 409 (conflict). True multi-connection
    row lock contention proof is exercised on PostgreSQL via CI.
    """
    import asyncio
    user, token = await create_user_fixture("race@test.com", "Race User")
    headers = {"Authorization": f"Bearer {token}"}

    # Create bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Airtel Fiber", "amount": "1199.00", "due_date": "2026-11-25"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # Two simultaneous requests with different idempotency keys
    req1 = client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "concurrent_key_alpha"}
    )
    req2 = client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "concurrent_key_beta"}
    )

    res1, res2 = await asyncio.gather(req1, req2)
    status_codes = sorted([res1.status_code, res2.status_code])
    assert status_codes == [200, 409], f"Expected [200, 409], got {status_codes}"


@pytest.mark.asyncio
@pytest.mark.skipif(is_sqlite, reason="Postgres-only: Verifies real PostgreSQL row locking (SELECT ... FOR UPDATE) across concurrent transactions. Skipped on SQLite.")
async def test_postgres_concurrent_payment_race_condition(client: AsyncClient, create_user_fixture):
    """
    Races two concurrent requests against PostgreSQL to verify row-level FOR UPDATE locking.
    """
    import asyncio
    user, token = await create_user_fixture("pg_race@test.com", "Postgres Race User")
    headers = {"Authorization": f"Bearer {token}"}

    # Create bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Postgres Concurrency Gas Bill", "amount": "850.00", "due_date": "2026-12-01"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # Two simultaneous requests with different idempotency keys
    req1 = client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "pg_concurrent_key_alpha"}
    )
    req2 = client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "pg_concurrent_key_beta"}
    )

    res1, res2 = await asyncio.gather(req1, req2)
    status_codes = sorted([res1.status_code, res2.status_code])
    assert status_codes == [200, 409], f"Expected [200, 409], got {status_codes}"


@pytest.mark.asyncio
async def test_mark_paid_safety_and_rejection(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("offline@test.com", "Offline User")
    headers = {"Authorization": f"Bearer {token}"}

    # Create bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Water Utility", "amount": "450.00", "due_date": "2026-11-30"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # 1. Mark paid (self-reported)
    mark_res = await client.post(f"/api/v1/bills/{bill_id}/mark-paid", headers=headers)
    assert mark_res.status_code == 200
    mark_data = mark_res.json()
    assert mark_data["bill_status"] == "PAID_UNVERIFIED"

    # 2. Second click on mark-paid rejected with 409 ALREADY_PAID
    second_mark = await client.post(f"/api/v1/bills/{bill_id}/mark-paid", headers=headers)
    assert second_mark.status_code == 409
    assert second_mark.json()["error"]["code"] == "ALREADY_PAID"

    # 3. Calling /pay on PAID_UNVERIFIED bill is rejected with 409 ALREADY_PAID
    pay_res = await client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "new_pay_key"}
    )
    assert pay_res.status_code == 409
    assert pay_res.json()["error"]["code"] == "ALREADY_PAID"

    # 4. Deleting a bill then attempting mark-paid returns 404
    del_res = await client.delete(f"/api/v1/bills/{bill_id}", headers=headers)
    assert del_res.status_code == 204

    dead_mark = await client.post(f"/api/v1/bills/{bill_id}/mark-paid", headers=headers)
    assert dead_mark.status_code == 404


@pytest.mark.asyncio
async def test_payment_webhook_and_ledger(client: AsyncClient, create_user_fixture):
    import uuid
    import time
    import hmac
    import hashlib
    import json
    from app.core.config import settings

    user, token = await create_user_fixture("webhook@test.com", "Webhook User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Jio Fiber", "amount": "999.00", "due_date": "2026-11-28"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # 2. Create an in-flight PENDING transaction in database
    from app.repositories.payment import PaymentRepository
    from backend.tests.conftest import TestAsyncSessionLocal
    from datetime import datetime, timezone, timedelta
    from decimal import Decimal

    async with TestAsyncSessionLocal() as session:
        repo = PaymentRepository(session)
        txn = await repo.create_pending_transaction(
            bill_id=uuid.UUID(bill_id),
            idempotency_key="wh_pending_intent_key",
            amount=Decimal("999.00"),
            paid_by_user_id=user.id,
            paid_by_display_name="Webhook User",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        txn_id = str(txn.id)

    # 3. Build Webhook Payload
    webhook_payload = {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "payment.success",
        "transaction_id": txn_id,
        "payment_reference": "WH_REF_SUCCESS_999",
        "amount": "999.00"
    }
    payload_bytes = json.dumps(webhook_payload).encode("utf-8")
    timestamp_str = str(int(time.time()))

    signed_bytes = f"{timestamp_str}.".encode("utf-8") + payload_bytes
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        signed_bytes,
        hashlib.sha256
    ).hexdigest()

    wh_headers = {
        "X-Signature": signature,
        "X-Timestamp": timestamp_str,
        "Content-Type": "application/json"
    }

    # 4. Valid Webhook succeeds
    wh_res = await client.post("/api/v1/payments/webhook", content=payload_bytes, headers=wh_headers)
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "processed"

    # 5. Replay with SAME event_id returns already_processed (ledger deduplication)
    replay_res = await client.post("/api/v1/payments/webhook", content=payload_bytes, headers=wh_headers)
    assert replay_res.status_code == 200
    assert replay_res.json()["status"] == "already_processed"

    # 6. Invalid signature is rejected with 401
    bad_headers = {**wh_headers, "X-Signature": "invalid_sig_000"}
    bad_res = await client.post("/api/v1/payments/webhook", content=payload_bytes, headers=bad_headers)
    assert bad_res.status_code == 401

    # 7. Amount mismatch is rejected with 400
    mismatch_payload = {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "payment.success",
        "transaction_id": txn_id,
        "amount": "1.00"  # Mismatch: bill was 999.00
    }
    mismatch_bytes = json.dumps(mismatch_payload).encode("utf-8")
    mismatch_ts = str(int(time.time()))
    mismatch_sig = hmac.new(
        settings.WEBHOOK_SECRET.encode("utf-8"),
        f"{mismatch_ts}.".encode("utf-8") + mismatch_bytes,
        hashlib.sha256
    ).hexdigest()
    mismatch_res = await client.post(
        "/api/v1/payments/webhook",
        content=mismatch_bytes,
        headers={"X-Signature": mismatch_sig, "X-Timestamp": mismatch_ts, "Content-Type": "application/json"}
    )
    assert mismatch_res.status_code == 400
    assert "Amount mismatch" in mismatch_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_payment_cancellation(client: AsyncClient, create_user_fixture):
    import uuid
    user, token = await create_user_fixture("cancel@test.com", "Cancel User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Act Fibernet", "amount": "825.00", "due_date": "2026-11-29"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # 2. Directly create a pending transaction in database to simulate in-flight intent
    from app.repositories.payment import PaymentRepository
    from backend.tests.conftest import TestAsyncSessionLocal
    from datetime import datetime, timezone, timedelta
    from decimal import Decimal

    async with TestAsyncSessionLocal() as session:
        repo = PaymentRepository(session)
        await repo.create_pending_transaction(
            bill_id=uuid.UUID(bill_id),
            idempotency_key="pending_cancel_key",
            amount=Decimal("825.00"),
            paid_by_user_id=user.id,
            paid_by_display_name="Cancel User",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )

    # 3. Cancel the payment via API
    cancel_res = await client.post(f"/api/v1/bills/{bill_id}/payment/cancel", headers=headers)
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "FAILED"
    assert cancel_data["failure_reason"] == "CANCELLED_BY_USER"

    # 4. Bill is still unpaid and can now be paid successfully
    pay_res = await client.post(
        f"/api/v1/bills/{bill_id}/pay",
        headers={**headers, "Idempotency-Key": "after_cancel_pay_key"}
    )
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_webhook_on_cancelled_payment_must_not_mark_bill_paid(client: AsyncClient, create_user_fixture):
    import uuid
    import time
    import json
    import hmac
    import hashlib
    from app.core.config import settings
    from app.repositories.payment import PaymentRepository
    from backend.tests.conftest import TestAsyncSessionLocal
    from datetime import datetime, timezone, timedelta
    from decimal import Decimal

    user, token = await create_user_fixture("wh_cancel@test.com", "WH Cancel User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a bill
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Cancelled Webhook Test", "amount": "450.00", "due_date": "2026-11-30"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    # 2. Create pending transaction and cancel it
    async with TestAsyncSessionLocal() as session:
        repo = PaymentRepository(session)
        txn = await repo.create_pending_transaction(
            bill_id=uuid.UUID(bill_id),
            idempotency_key="pending_for_cancel_test",
            amount=Decimal("450.00"),
            paid_by_user_id=user.id,
            paid_by_display_name="WH Cancel User",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        txn_id = str(txn.id)

    cancel_res = await client.post(f"/api/v1/bills/{bill_id}/payment/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "FAILED"

    # 3. Deliver payment.success webhook for the cancelled transaction
    wh_payload = {
        "event_id": f"evt_cancel_{uuid.uuid4().hex}",
        "event_type": "payment.success",
        "transaction_id": txn_id,
        "amount": "450.00",
        "payment_reference": "WH_LATE_SUCCESS"
    }
    payload_bytes = json.dumps(wh_payload).encode("utf-8")
    ts = str(int(time.time()))
    sig = hmac.new(settings.WEBHOOK_SECRET.encode("utf-8"), f"{ts}.".encode("utf-8") + payload_bytes, hashlib.sha256).hexdigest()

    wh_res = await client.post(
        "/api/v1/payments/webhook",
        content=payload_bytes,
        headers={"X-Signature": sig, "X-Timestamp": ts, "Content-Type": "application/json"}
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "ignored_terminal_state"

    # 4. Bill MUST STILL NOT be marked paid!
    bill_check = await client.get(f"/api/v1/bills/{bill_id}", headers=headers)
    assert bill_check.status_code == 200
    assert bill_check.json()["bill_status"] != "PAID"
    assert bill_check.json()["paid_at"] is None


@pytest.mark.asyncio
async def test_simultaneous_webhook_deliveries_handled_gracefully(client: AsyncClient, create_user_fixture):
    import uuid
    import time
    import json
    import hmac
    import hashlib
    import asyncio
    from app.core.config import settings

    user, token = await create_user_fixture("wh_race@test.com", "WH Race User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a bill & pending transaction
    bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Race Webhook Test", "amount": "1500.00", "due_date": "2026-11-30"},
        headers=headers
    )
    bill_id = bill_res.json()["id"]

    from app.repositories.payment import PaymentRepository
    from backend.tests.conftest import TestAsyncSessionLocal
    from datetime import datetime, timezone, timedelta
    from decimal import Decimal

    async with TestAsyncSessionLocal() as session:
        repo = PaymentRepository(session)
        txn = await repo.create_pending_transaction(
            bill_id=uuid.UUID(bill_id),
            idempotency_key="wh_race_key",
            amount=Decimal("1500.00"),
            paid_by_user_id=user.id,
            paid_by_display_name="WH Race User",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
        )
        txn_id = str(txn.id)

    # 2. Build webhook with shared event_id
    shared_event_id = f"evt_race_{uuid.uuid4().hex}"
    wh_payload = {
        "event_id": shared_event_id,
        "event_type": "payment.success",
        "transaction_id": txn_id,
        "amount": "1500.00",
        "payment_reference": "WH_RACE_SUCCESS"
    }
    payload_bytes = json.dumps(wh_payload).encode("utf-8")
    ts = str(int(time.time()))
    sig = hmac.new(settings.WEBHOOK_SECRET.encode("utf-8"), f"{ts}.".encode("utf-8") + payload_bytes, hashlib.sha256).hexdigest()
    wh_headers = {"X-Signature": sig, "X-Timestamp": ts, "Content-Type": "application/json"}

    # 3. Fire simultaneous webhook deliveries with identical event_id
    res1, res2 = await asyncio.gather(
        client.post("/api/v1/payments/webhook", content=payload_bytes, headers=wh_headers),
        client.post("/api/v1/payments/webhook", content=payload_bytes, headers=wh_headers),
    )

    statuses = [res1.json().get("status"), res2.json().get("status")]
    assert res1.status_code == 200
    assert res2.status_code == 200
    # Exactly one processes the event, and the other receives already_processed deduplication
    assert "processed" in statuses
    assert "already_processed" in statuses

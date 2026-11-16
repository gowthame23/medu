import pytest
import uuid
from datetime import date, timedelta
from httpx import AsyncClient

from app.repositories.notification import NotificationRepository
from tests.conftest import TestAsyncSessionLocal


@pytest.mark.asyncio
async def test_daily_logs_range_bounds(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("range_bounds@example.com", "Range Bounds User")
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()

    # 1. start_date > end_date -> 422
    res = await client.get(
        f"/api/v1/daily-logs/range?start_date={(today + timedelta(days=5)).isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "INVALID_DATE_RANGE"

    # 2. span > 366 days -> 422
    res = await client.get(
        f"/api/v1/daily-logs/range?start_date={(today - timedelta(days=368)).isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "DATE_RANGE_TOO_LARGE"

    # 3. span <= 366 days -> 200
    res = await client.get(
        f"/api/v1/daily-logs/range?start_date={(today - timedelta(days=365)).isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_list_endpoints_pagination_and_max_bounds(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("pagination_user@example.com", "Pagination User")
    headers = {"Authorization": f"Bearer {token}"}
    today = date.today()

    # =========================================================================
    # 1. Endpoint: GET /api/v1/bills (Personal Bills)
    # =========================================================================
    # Validation bounds: limit=201 -> 422, limit=0 -> 422, offset=-1 -> 422
    res_b_max = await client.get("/api/v1/bills?limit=201", headers=headers)
    assert res_b_max.status_code == 422
    res_b_zero = await client.get("/api/v1/bills?limit=0", headers=headers)
    assert res_b_zero.status_code == 422
    res_b_neg = await client.get("/api/v1/bills?offset=-1", headers=headers)
    assert res_b_neg.status_code == 422

    # Create 3 personal bills
    b_ids = []
    for i in range(3):
        res = await client.post(
            "/api/v1/bills",
            json={
                "title": f"Personal Bill {i}",
                "amount": f"{100 + i}.00",
                "due_date": (today + timedelta(days=i + 1)).isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 201
        b_ids.append(res.json()["id"])

    # Stable ordering & offset paging (due_date.asc(), id.asc())
    # Page 1: limit=2, offset=0 -> [b0, b1]
    res_b_p1 = await client.get("/api/v1/bills?limit=2&offset=0", headers=headers)
    assert res_b_p1.status_code == 200
    b_p1 = res_b_p1.json()
    assert len(b_p1) == 2
    assert b_p1[0]["id"] == b_ids[0]
    assert b_p1[1]["id"] == b_ids[1]

    # Page 2: limit=2, offset=1 -> [b1, b2] (proves stable overlap at offset 1)
    res_b_p2 = await client.get("/api/v1/bills?limit=2&offset=1", headers=headers)
    assert res_b_p2.status_code == 200
    b_p2 = res_b_p2.json()
    assert len(b_p2) == 2
    assert b_p2[0]["id"] == b_ids[1]
    assert b_p2[1]["id"] == b_ids[2]

    # Page 3: limit=2, offset=2 -> [b2]
    res_b_p3 = await client.get("/api/v1/bills?limit=2&offset=2", headers=headers)
    assert res_b_p3.status_code == 200
    b_p3 = res_b_p3.json()
    assert len(b_p3) == 1
    assert b_p3[0]["id"] == b_ids[2]

    # =========================================================================
    # 2. Endpoint: GET /api/v1/loans (Liabilities Vault)
    # =========================================================================
    # Validation bounds: limit=201 -> 422, limit=0 -> 422, offset=-1 -> 422
    res_l_max = await client.get("/api/v1/loans?limit=201", headers=headers)
    assert res_l_max.status_code == 422
    res_l_zero = await client.get("/api/v1/loans?limit=0", headers=headers)
    assert res_l_zero.status_code == 422
    res_l_neg = await client.get("/api/v1/loans?offset=-1", headers=headers)
    assert res_l_neg.status_code == 422

    # Create 3 loans
    l_ids = []
    for i in range(3):
        res = await client.post(
            "/api/v1/loans",
            json={
                "loan_name": f"Loan {i}",
                "principal_amount": f"{50000 + i * 10000}.00",
                "interest_rate": "8.50",
                "tenure_months": 24 + i * 12,
                "start_date": today.isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 201
        l_ids.append(res.json()["id"])

    # Stable ordering & offset paging (created_at.desc(), id.desc()) -> [l2, l1, l0]
    res_l_p1 = await client.get("/api/v1/loans?limit=2&offset=0", headers=headers)
    assert res_l_p1.status_code == 200
    l_p1 = res_l_p1.json()
    assert len(l_p1) == 2
    assert l_p1[0]["id"] == l_ids[2]
    assert l_p1[1]["id"] == l_ids[1]

    res_l_p2 = await client.get("/api/v1/loans?limit=2&offset=1", headers=headers)
    assert res_l_p2.status_code == 200
    l_p2 = res_l_p2.json()
    assert len(l_p2) == 2
    assert l_p2[0]["id"] == l_ids[1]
    assert l_p2[1]["id"] == l_ids[0]

    res_l_p3 = await client.get("/api/v1/loans?limit=2&offset=2", headers=headers)
    assert res_l_p3.status_code == 200
    l_p3 = res_l_p3.json()
    assert len(l_p3) == 1
    assert l_p3[0]["id"] == l_ids[0]

    # =========================================================================
    # 3. Endpoint: GET /api/v1/notifications (In-App Notifications)
    # =========================================================================
    # Validation bounds: limit=201 -> 422, limit=0 -> 422, offset=-1 -> 422
    res_n_max = await client.get("/api/v1/notifications?limit=201", headers=headers)
    assert res_n_max.status_code == 422
    res_n_zero = await client.get("/api/v1/notifications?limit=0", headers=headers)
    assert res_n_zero.status_code == 422
    res_n_neg = await client.get("/api/v1/notifications?offset=-1", headers=headers)
    assert res_n_neg.status_code == 422

    # Create 3 notifications
    n_ids = []
    async with TestAsyncSessionLocal() as session:
        n_repo = NotificationRepository(session)
        for i in range(3):
            notif = await n_repo.create_notification(
                user_id=user.id,
                type_str="BILL_DUE",
                title=f"Notification {i}",
                message=f"Message for notification {i}"
            )
            n_ids.append(str(notif.id))

    # Stable ordering & offset paging (created_at.desc(), id.desc()) -> [n2, n1, n0]
    res_n_p1 = await client.get("/api/v1/notifications?limit=2&offset=0", headers=headers)
    assert res_n_p1.status_code == 200
    n_p1 = res_n_p1.json()
    assert len(n_p1) == 2
    assert n_p1[0]["id"] == n_ids[2]
    assert n_p1[1]["id"] == n_ids[1]

    res_n_p2 = await client.get("/api/v1/notifications?limit=2&offset=1", headers=headers)
    assert res_n_p2.status_code == 200
    n_p2 = res_n_p2.json()
    assert len(n_p2) == 2
    assert n_p2[0]["id"] == n_ids[1]
    assert n_p2[1]["id"] == n_ids[0]

    res_n_p3 = await client.get("/api/v1/notifications?limit=2&offset=2", headers=headers)
    assert res_n_p3.status_code == 200
    n_p3 = res_n_p3.json()
    assert len(n_p3) == 1
    assert n_p3[0]["id"] == n_ids[0]

    # =========================================================================
    # 4. Endpoint: GET /api/v1/families/{id}/bills (Family Bills)
    # =========================================================================
    # Create family group
    f_res = await client.post(
        "/api/v1/families",
        json={"group_name": "Pagination Family", "timezone": "Asia/Kolkata"},
        headers=headers,
    )
    assert f_res.status_code == 201
    family_id = f_res.json()["id"]

    # Validation bounds: limit=201 -> 422, limit=0 -> 422, offset=-1 -> 422
    res_fb_max = await client.get(f"/api/v1/families/{family_id}/bills?limit=201", headers=headers)
    assert res_fb_max.status_code == 422
    res_fb_zero = await client.get(f"/api/v1/families/{family_id}/bills?limit=0", headers=headers)
    assert res_fb_zero.status_code == 422
    res_fb_neg = await client.get(f"/api/v1/families/{family_id}/bills?offset=-1", headers=headers)
    assert res_fb_neg.status_code == 422

    # Create 3 family bills
    fb_ids = []
    for i in range(3):
        res = await client.post(
            f"/api/v1/families/{family_id}/bills",
            json={
                "title": f"Family Bill {i}",
                "amount": f"{200 + i}.00",
                "due_date": (today + timedelta(days=i + 1)).isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 201
        fb_ids.append(res.json()["id"])

    # Stable ordering & offset paging (due_date.asc(), id.asc()) -> [fb0, fb1, fb2]
    res_fb_p1 = await client.get(f"/api/v1/families/{family_id}/bills?limit=2&offset=0", headers=headers)
    assert res_fb_p1.status_code == 200
    fb_p1 = res_fb_p1.json()
    assert len(fb_p1) == 2
    assert fb_p1[0]["id"] == fb_ids[0]
    assert fb_p1[1]["id"] == fb_ids[1]

    res_fb_p2 = await client.get(f"/api/v1/families/{family_id}/bills?limit=2&offset=1", headers=headers)
    assert res_fb_p2.status_code == 200
    fb_p2 = res_fb_p2.json()
    assert len(fb_p2) == 2
    assert fb_p2[0]["id"] == fb_ids[1]
    assert fb_p2[1]["id"] == fb_ids[2]

    res_fb_p3 = await client.get(f"/api/v1/families/{family_id}/bills?limit=2&offset=2", headers=headers)
    assert res_fb_p3.status_code == 200
    fb_p3 = res_fb_p3.json()
    assert len(fb_p3) == 1
    assert fb_p3[0]["id"] == fb_ids[2]

    # =========================================================================
    # 5. Endpoint: GET /api/v1/families/{id}/payments (Family Payment History)
    # =========================================================================
    # Validation bounds: limit=201 -> 422, limit=0 -> 422, offset=-1 -> 422
    res_fp_max = await client.get(f"/api/v1/families/{family_id}/payments?limit=201", headers=headers)
    assert res_fp_max.status_code == 422
    res_fp_zero = await client.get(f"/api/v1/families/{family_id}/payments?limit=0", headers=headers)
    assert res_fp_zero.status_code == 422
    res_fp_neg = await client.get(f"/api/v1/families/{family_id}/payments?offset=-1", headers=headers)
    assert res_fp_neg.status_code == 422

    # Pay each of the 3 family bills to generate 3 SUCCESS payments
    pay_txn_ids = []
    for i, fb_id in enumerate(fb_ids):
        res = await client.post(
            f"/api/v1/families/{family_id}/bills/{fb_id}/pay",
            headers={**headers, "Idempotency-Key": f"key_fam_pay_{i}_{uuid.uuid4().hex}"}
        )
        assert res.status_code == 200
        pay_txn_ids.append(res.json()["payment_reference"])

    # Payments are listed in reverse chronological order (created_at.desc(), id.desc()) -> [pay2, pay1, pay0]
    res_fp_p1 = await client.get(f"/api/v1/families/{family_id}/payments?limit=2&offset=0", headers=headers)
    assert res_fp_p1.status_code == 200
    fp_p1 = res_fp_p1.json()
    assert len(fp_p1) == 2
    assert fp_p1[0]["payment_reference"] == pay_txn_ids[2]
    assert fp_p1[1]["payment_reference"] == pay_txn_ids[1]

    res_fp_p2 = await client.get(f"/api/v1/families/{family_id}/payments?limit=2&offset=1", headers=headers)
    assert res_fp_p2.status_code == 200
    fp_p2 = res_fp_p2.json()
    assert len(fp_p2) == 2
    assert fp_p2[0]["payment_reference"] == pay_txn_ids[1]
    assert fp_p2[1]["payment_reference"] == pay_txn_ids[0]

    res_fp_p3 = await client.get(f"/api/v1/families/{family_id}/payments?limit=2&offset=2", headers=headers)
    assert res_fp_p3.status_code == 200
    fp_p3 = res_fp_p3.json()
    assert len(fp_p3) == 1
    assert fp_p3[0]["payment_reference"] == pay_txn_ids[0]


@pytest.mark.asyncio
async def test_loan_bounds_rejections(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("loan_bounds@example.com", "Loan Bounds User")
    headers = {"Authorization": f"Bearer {token}"}
    today = date.today()

    # 1. principal_amount > 1,000,000,000.00 -> 422
    res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Megaloan",
            "principal_amount": "1000000000.01",
            "interest_rate": "7.50",
            "tenure_months": 120,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 422

    # 2. principal_amount <= 0 -> 422
    res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Zero loan",
            "principal_amount": "0.00",
            "interest_rate": "7.50",
            "tenure_months": 12,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 422

    # Create a valid loan for payment & prepayment boundary testing
    l_res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Home Loan",
            "principal_amount": "100000.00",
            "interest_rate": "8.00",
            "tenure_months": 60,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert l_res.status_code == 201
    loan_id = l_res.json()["id"]

    # 3. Payment principal > remaining principal (100,000) -> 422
    pay_res = await client.post(
        f"/api/v1/loans/{loan_id}/payments",
        json={
            "payment_date": today.isoformat(),
            "principal_paid": "100000.01",
            "interest_paid": "500.00",
        },
        headers=headers,
    )
    assert pay_res.status_code == 422
    assert pay_res.json()["error"]["code"] == "PAYMENT_EXCEEDS_PRINCIPAL"

    # 4. Prepayment lump sum > remaining principal (100,000) -> 422
    prep_res = await client.post(
        f"/api/v1/loans/{loan_id}/prepayments",
        json={
            "prepayment_date": today.isoformat(),
            "lump_sum_amount": "100000.01",
            "effect": "REDUCE_TENURE",
        },
        headers=headers,
    )
    assert prep_res.status_code == 422
    assert prep_res.json()["error"]["code"] == "PREPAYMENT_EXCEEDS_PRINCIPAL"

    # 5. Prepayment simulate month > tenure_months (60) -> 422
    sim_res1 = await client.post(
        f"/api/v1/loans/{loan_id}/simulate-prepayment",
        json={
            "prepayment_amount": "10000.00",
            "prepayment_month": 61,
            "effect": "REDUCE_TENURE",
        },
        headers=headers,
    )
    assert sim_res1.status_code == 422
    assert sim_res1.json()["error"]["code"] == "PREPAYMENT_MONTH_EXCEEDS_TENURE"

    # 6. Prepayment simulate amount > remaining principal -> 422
    sim_res2 = await client.post(
        f"/api/v1/loans/{loan_id}/simulate-prepayment",
        json={
            "prepayment_amount": "100000.01",
            "prepayment_month": 12,
            "effect": "REDUCE_TENURE",
        },
        headers=headers,
    )
    assert sim_res2.status_code == 422
    assert sim_res2.json()["error"]["code"] == "PREPAYMENT_EXCEEDS_PRINCIPAL"

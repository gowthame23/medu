import pytest
import uuid
from datetime import date, timedelta
from httpx import AsyncClient


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

    # 1. /notifications max limit 200
    res = await client.get("/api/v1/notifications?limit=201", headers=headers)
    assert res.status_code == 422

    res = await client.get("/api/v1/notifications?limit=50&offset=0", headers=headers)
    assert res.status_code == 200

    # 2. /bills max limit 200 and pagination
    res = await client.get("/api/v1/bills?limit=201", headers=headers)
    assert res.status_code == 422

    # Create 3 bills
    today = date.today()
    bill_ids = []
    for i in range(3):
        res = await client.post(
            "/api/v1/bills",
            json={
                "title": f"Bill {i}",
                "amount": f"{100 + i}.00",
                "due_date": (today + timedelta(days=i + 1)).isoformat(),
            },
            headers=headers,
        )
        assert res.status_code == 201
        bill_ids.append(res.json()["id"])

    # Pagination: limit=2, offset=0
    res = await client.get("/api/v1/bills?limit=2&offset=0", headers=headers)
    assert res.status_code == 200
    bills_page1 = res.json()
    assert len(bills_page1) == 2
    assert bills_page1[0]["id"] == bill_ids[0]
    assert bills_page1[1]["id"] == bill_ids[1]

    # Pagination: limit=2, offset=2
    res = await client.get("/api/v1/bills?limit=2&offset=2", headers=headers)
    assert res.status_code == 200
    bills_page2 = res.json()
    assert len(bills_page2) == 1
    assert bills_page2[0]["id"] == bill_ids[2]

    # 3. Create family group for family list pagination tests
    f_res = await client.post(
        "/api/v1/families",
        json={"group_name": "Pagination Family", "timezone": "Asia/Kolkata"},
        headers=headers,
    )
    assert f_res.status_code == 201
    family_id = f_res.json()["id"]

    # /families/{id}/bills max limit 200
    res = await client.get(f"/api/v1/families/{family_id}/bills?limit=201", headers=headers)
    assert res.status_code == 422

    # /families/{id}/payments max limit 200
    res = await client.get(f"/api/v1/families/{family_id}/payments?limit=201", headers=headers)
    assert res.status_code == 422

    # 4. /loans max limit 200
    res = await client.get("/api/v1/loans?limit=201", headers=headers)
    assert res.status_code == 422

    # Create 2 loans
    l1 = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Loan 1",
            "principal_amount": "50000.00",
            "interest_rate": "8.50",
            "tenure_months": 24,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert l1.status_code == 201
    l1_id = l1.json()["id"]

    l2 = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Loan 2",
            "principal_amount": "75000.00",
            "interest_rate": "9.00",
            "tenure_months": 36,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert l2.status_code == 201
    l2_id = l2.json()["id"]

    # Pagination: limit=1, offset=0 (ordered by created_at.desc(), id.desc())
    res = await client.get("/api/v1/loans?limit=1&offset=0", headers=headers)
    assert res.status_code == 200
    loans_page1 = res.json()
    assert len(loans_page1) == 1
    assert loans_page1[0]["id"] == l2_id

    # Pagination: limit=1, offset=1
    res = await client.get("/api/v1/loans?limit=1&offset=1", headers=headers)
    assert res.status_code == 200
    loans_page2 = res.json()
    assert len(loans_page2) == 1
    assert loans_page2[0]["id"] == l1_id


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

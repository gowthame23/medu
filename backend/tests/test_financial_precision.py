import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_financial_precision_and_no_float(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("finance@test.com", "Finance User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Float rejection test: sending a float amount in JSON must fail with 422!
    float_payload = {
        "title": "Float Attempt",
        "amount": 1450.50,  # float!
        "due_date": "2026-11-25"
    }
    float_res = await client.post("/api/v1/bills", json=float_payload, headers=headers)
    assert float_res.status_code == 422
    assert "Floats are strictly forbidden" in str(float_res.json())

    # 2. String representation with more than 2 decimals must fail!
    too_many_decimals = {
        "title": "Three Decimals",
        "amount": "1450.555",
        "due_date": "2026-11-25"
    }
    dec_res = await client.post("/api/v1/bills", json=too_many_decimals, headers=headers)
    assert dec_res.status_code == 422

    # 3. Decimal precision test: 0.10 + 0.20 = 0.30
    cats_res = await client.get("/api/v1/categories", headers=headers)
    cat_id = cats_res.json()[0]["id"]

    await client.post(
        "/api/v1/daily-logs/2026-11-15/entries",
        json={"category_id": cat_id, "amount": "0.10"},
        headers=headers
    )
    res2 = await client.post(
        "/api/v1/daily-logs/2026-11-15/entries",
        json={"category_id": cat_id, "amount": "0.20"},
        headers=headers
    )
    assert res2.status_code == 201
    log_data = res2.json()
    assert log_data["total_spent"] == "0.30"

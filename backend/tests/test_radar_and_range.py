import pytest
from datetime import date, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_daily_logs_range_and_radar(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("range_user@example.com", "Range Tester")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch categories
    cat_res = await client.get("/api/v1/categories", headers=headers)
    assert cat_res.status_code == 200
    categories = cat_res.json()
    assert len(categories) > 0
    cat_id = categories[0]["id"]

    # 2. Add an entry for today
    today = date.today()
    entry_payload = {
        "category_id": cat_id,
        "amount": "450.50"
    }
    add_res = await client.post(
        f"/api/v1/daily-logs/{today.isoformat()}/entries",
        json=entry_payload,
        headers=headers
    )
    assert add_res.status_code == 201

    # 3. Query range endpoint
    start_date = (today - timedelta(days=6)).isoformat()
    end_date = today.isoformat()
    range_res = await client.get(
        f"/api/v1/daily-logs/range?start_date={start_date}&end_date={end_date}",
        headers=headers
    )
    assert range_res.status_code == 200
    range_data = range_res.json()
    assert range_data["total_spent"] == "450.50"
    assert range_data["streak_days"] >= 1
    assert len(range_data["category_totals"]) >= 1
    assert range_data["category_totals"][0]["total_spent"] == "450.50"

    # 4. Create a personal bill due tomorrow
    tomorrow = today + timedelta(days=1)
    bill_payload = {
        "title": "Electricity Bill",
        "amount": "1250.00",
        "due_date": tomorrow.isoformat(),
        "consumer_number": "CA12345678",
        "category": "utility"
    }
    bill_res = await client.post("/api/v1/bills", json=bill_payload, headers=headers)
    assert bill_res.status_code == 201
    bill_id = bill_res.json()["id"]

    # 5. Check radar endpoint
    radar_res = await client.get("/api/v1/bills/radar?horizon_days=7", headers=headers)
    assert radar_res.status_code == 200
    radar_bills = radar_res.json()
    assert len(radar_bills) == 1
    assert radar_bills[0]["id"] == bill_id
    assert radar_bills[0]["bill_status"] == "UNPAID"

    # 6. Test Mark Paid (Self-Reported)
    mark_res = await client.post(f"/api/v1/bills/{bill_id}/mark-paid", headers=headers)
    assert mark_res.status_code == 200
    mark_data = mark_res.json()
    assert mark_data["bill_status"] == "PAID_UNVERIFIED"
    assert mark_data["is_paid"] is True
    assert "Self-Reported" in mark_data["paid_by_display_name"]

    # 7. Radar should no longer show this paid bill
    radar_res_after = await client.get("/api/v1/bills/radar?horizon_days=7", headers=headers)
    assert radar_res_after.status_code == 200
    assert len(radar_res_after.json()) == 0

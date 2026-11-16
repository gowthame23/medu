import pytest
from httpx import AsyncClient


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

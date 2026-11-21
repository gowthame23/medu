import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_permission_matrix_and_privacy_isolation(client: AsyncClient, create_user_fixture):
    admin, admin_token = await create_user_fixture("admin_p@test.com", "Admin Pam")
    member, member_token = await create_user_fixture("member_j@test.com", "Member Jim")
    outsider, outsider_token = await create_user_fixture("outsider_d@test.com", "Outsider Dwight")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    member_headers = {"Authorization": f"Bearer {member_token}"}
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    # 1. Admin creates family group
    group_res = await client.post(
        "/api/v1/families",
        json={"group_name": "Scranton Family", "timezone": "Asia/Kolkata"},
        headers=admin_headers
    )
    group_id = group_res.json()["id"]

    # 2. Add Jim as Member
    inv_res = await client.post(
        f"/api/v1/families/{group_id}/invitations",
        json={"email": "member_j@test.com"},
        headers=admin_headers
    )
    await client.post(
        "/api/v1/invitations/accept",
        json={"token": inv_res.json()["invite_token"]},
        headers=member_headers
    )

    # 3. Create family bill (Admin creates)
    bill_res = await client.post(
        f"/api/v1/families/{group_id}/bills",
        json={"title": "Electric Dunder", "amount": "1450.00", "due_date": "2026-11-20"},
        headers=admin_headers
    )
    assert bill_res.status_code == 201
    bill_id = bill_res.json()["id"]

    # -------------------------------------------------------------
    # MATRIX CHECK: Family Bill Creation
    # Admin -> 201
    # Member -> 403 Forbidden (knows group exists)
    # Outsider -> 404 Not Found (NEVER 403, group existence hidden!)
    # -------------------------------------------------------------
    member_bill_create = await client.post(
        f"/api/v1/families/{group_id}/bills",
        json={"title": "Unauthorized Bill", "amount": "500.00", "due_date": "2026-11-20"},
        headers=member_headers
    )
    assert member_bill_create.status_code == 403

    outsider_bill_create = await client.post(
        f"/api/v1/families/{group_id}/bills",
        json={"title": "Unauthorized Bill", "amount": "500.00", "due_date": "2026-11-20"},
        headers=outsider_headers
    )
    assert outsider_bill_create.status_code == 404

    # -------------------------------------------------------------
    # MATRIX CHECK: Family Bill Read
    # Admin -> 200
    # Member -> 200
    # Outsider -> 404 Not Found
    # -------------------------------------------------------------
    assert (await client.get(f"/api/v1/families/{group_id}/bills", headers=admin_headers)).status_code == 200
    assert (await client.get(f"/api/v1/families/{group_id}/bills", headers=member_headers)).status_code == 200
    assert (await client.get(f"/api/v1/families/{group_id}/bills", headers=outsider_headers)).status_code == 404

    # -------------------------------------------------------------
    # MATRIX CHECK: Personal Data Sandboxing (Loans & Daily Logs)
    # Admin has private loan
    # -------------------------------------------------------------
    loan_res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Personal Secret Loan",
            "principal_amount": "500000.00",
            "interest_rate": "8.5",
            "tenure_months": 60
        },
        headers=admin_headers
    )
    assert loan_res.status_code == 201
    loan_id = loan_res.json()["id"]

    # Member and Outsider trying to access Admin's loan -> 404 Not Found
    assert (await client.get(f"/api/v1/loans/{loan_id}", headers=member_headers)).status_code == 404
    assert (await client.get(f"/api/v1/loans/{loan_id}", headers=outsider_headers)).status_code == 404

    # Schema Test: Family bill endpoints NEVER contain loan fields
    family_bills_data = (await client.get(f"/api/v1/families/{group_id}/bills", headers=member_headers)).json()
    for b in family_bills_data:
        assert "principal_amount" not in b
        assert "interest_rate" not in b
        assert "monthly_emi" not in b
        assert "loan_name" not in b

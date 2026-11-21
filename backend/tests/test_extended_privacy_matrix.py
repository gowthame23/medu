import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_extended_privacy_and_isolation_matrix(client: AsyncClient, create_user_fixture):
    """
    Exhaustive verification of the strict dual-account privacy boundary across
    Personal Bills, Daily Logs, Loans/Liabilities Vault, and Family Membership revocation.
    """
    alice, alice_tok = await create_user_fixture("alice_priv@test.com", "Alice Admin")
    bob, bob_tok = await create_user_fixture("bob_priv@test.com", "Bob Member")
    eve, eve_tok = await create_user_fixture("eve_priv@test.com", "Eve Outsider")

    alice_h = {"Authorization": f"Bearer {alice_tok}"}
    bob_h = {"Authorization": f"Bearer {bob_tok}"}
    eve_h = {"Authorization": f"Bearer {eve_tok}"}

    # =========================================================================
    # 1. FAMILY SETUP & INVITATION
    # =========================================================================
    fam_res = await client.post(
        "/api/v1/families",
        json={"group_name": "Matrix Household", "timezone": "Asia/Kolkata"},
        headers=alice_h
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["id"]

    inv_res = await client.post(
        f"/api/v1/families/{family_id}/invitations",
        json={"email": "bob_priv@test.com"},
        headers=alice_h
    )
    assert inv_res.status_code == 201
    invite_token = inv_res.json()["invite_token"]

    accept_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": invite_token},
        headers=bob_h
    )
    assert accept_res.status_code == 200

    # Retrieve Bob's member ID
    members_res = await client.get(f"/api/v1/families/{family_id}/members", headers=alice_h)
    assert members_res.status_code == 200
    bob_member_id = next(m["id"] for m in members_res.json() if m["user_id"] == str(bob.id))

    # =========================================================================
    # 2. PERSONAL BILLS ISOLATION
    # =========================================================================
    p_bill_res = await client.post(
        "/api/v1/bills",
        json={"title": "Alice Private Medical Bill", "amount": "12000.00", "due_date": "2026-12-01"},
        headers=alice_h
    )
    assert p_bill_res.status_code == 201
    alice_bill_id = p_bill_res.json()["id"]

    # Bob (family member) and Eve (outsider) CANNOT read Alice's personal bill
    assert (await client.get(f"/api/v1/bills/{alice_bill_id}", headers=bob_h)).status_code == 404
    assert (await client.get(f"/api/v1/bills/{alice_bill_id}", headers=eve_h)).status_code == 404

    # Bob and Eve CANNOT pay Alice's personal bill
    assert (await client.post(f"/api/v1/bills/{alice_bill_id}/pay", headers=bob_h)).status_code == 404
    assert (await client.post(f"/api/v1/bills/{alice_bill_id}/pay", headers=eve_h)).status_code == 404

    # Bob and Eve CANNOT mark Alice's personal bill paid
    assert (await client.post(f"/api/v1/bills/{alice_bill_id}/mark-paid", headers=bob_h)).status_code == 404
    assert (await client.post(f"/api/v1/bills/{alice_bill_id}/mark-paid", headers=eve_h)).status_code == 404

    # Bob and Eve CANNOT cancel Alice's payment
    assert (await client.post(f"/api/v1/bills/{alice_bill_id}/payment/cancel", headers=bob_h)).status_code == 404
    assert (await client.post(f"/api/v1/bills/{alice_bill_id}/payment/cancel", headers=eve_h)).status_code == 404

    # Alice's personal bill NEVER appears in family radar or family bills
    fam_bills = (await client.get(f"/api/v1/families/{family_id}/bills", headers=bob_h)).json()
    assert all(b["id"] != alice_bill_id for b in fam_bills)

    fam_radar_res = await client.get(f"/api/v1/families/{family_id}/bills/radar", headers=bob_h)
    assert fam_radar_res.status_code == 200
    fam_radar = fam_radar_res.json()
    assert all(b["id"] != alice_bill_id for b in fam_radar)

    # =========================================================================
    # 3. DAILY LOGS & EXPENSE PRIVACY
    # =========================================================================
    # Alice adds a personal daily log entry
    cats_res = await client.get("/api/v1/categories", headers=alice_h)
    assert cats_res.status_code == 200
    cat_id = cats_res.json()[0]["id"]

    add_entry_res = await client.post(
        "/api/v1/daily-logs/2026-11-16/entries",
        json={"category_id": cat_id, "amount": "450.00"},
        headers=alice_h
    )
    assert add_entry_res.status_code == 201

    await client.put(
        "/api/v1/daily-logs/2026-11-16/notes",
        json={"notes": "Confidential therapy session notes"},
        headers=alice_h
    )

    # Bob queries daily logs for 2026-11-16 -> receives Bob's own empty log, zero Alice data
    bob_log_res = await client.get("/api/v1/daily-logs?date=2026-11-16", headers=bob_h)
    assert bob_log_res.status_code == 200
    bob_log = bob_log_res.json()
    assert bob_log["notes"] is None or bob_log["notes"] == ""
    assert len(bob_log["entries"]) == 0

    # Eve queries range -> sees zero Alice data
    eve_range_res = await client.get(
        "/api/v1/daily-logs/range?start_date=2026-11-10&end_date=2026-11-17",
        headers=eve_h
    )
    assert eve_range_res.status_code == 200
    for day_log in eve_range_res.json()["logs"]:
        assert day_log["notes"] is None or day_log["notes"] == ""
        assert len(day_log["entries"]) == 0

    # =========================================================================
    # 4. ZERO DEBT LEAKAGE — LIABILITIES VAULT (100% PRIVATE)
    # =========================================================================
    loan_res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Alice Private Education Loan",
            "principal_amount": "2500000.00",
            "interest_rate": "9.25",
            "tenure_months": 120
        },
        headers=alice_h
    )
    assert loan_res.status_code == 201
    alice_loan_id = loan_res.json()["id"]

    # Bob and Eve trying to access loan details -> 404
    assert (await client.get(f"/api/v1/loans/{alice_loan_id}", headers=bob_h)).status_code == 404
    assert (await client.get(f"/api/v1/loans/{alice_loan_id}", headers=eve_h)).status_code == 404

    # Bob and Eve trying to query daily cost -> 404
    assert (await client.get(f"/api/v1/loans/{alice_loan_id}/daily-cost", headers=bob_h)).status_code == 404
    assert (await client.get(f"/api/v1/loans/{alice_loan_id}/daily-cost", headers=eve_h)).status_code == 404

    # Bob and Eve trying to query amortization schedule -> 404
    assert (await client.get(f"/api/v1/loans/{alice_loan_id}/amortization", headers=bob_h)).status_code == 404
    assert (await client.get(f"/api/v1/loans/{alice_loan_id}/amortization", headers=eve_h)).status_code == 404

    # Bob and Eve trying to record payment on Alice's loan -> 404
    pay_tamper = await client.post(
        f"/api/v1/loans/{alice_loan_id}/payments",
        json={"payment_date": "2026-11-16", "principal_paid": "5000.00", "interest_paid": "10000.00"},
        headers=bob_h
    )
    assert pay_tamper.status_code == 404

    # Bob and Eve trying to record prepayment on Alice's loan -> 404
    prep_tamper = await client.post(
        f"/api/v1/loans/{alice_loan_id}/prepayments",
        json={"prepayment_date": "2026-11-16", "lump_sum_amount": "50000.00", "effect": "REDUCE_TENURE"},
        headers=bob_h
    )
    assert prep_tamper.status_code == 404

    # Bob and Eve trying to PATCH Alice's loan -> 404
    patch_tamper = await client.patch(
        f"/api/v1/loans/{alice_loan_id}",
        json={"interest_rate": "7.50"},
        headers=bob_h
    )
    assert patch_tamper.status_code == 404

    # Bob and Eve listing their own loans -> see []
    assert (await client.get("/api/v1/loans", headers=bob_h)).json() == []
    assert (await client.get("/api/v1/loans", headers=eve_h)).json() == []

    # =========================================================================
    # 5. IMMEDIATE FAMILY ACCESS TERMINATION UPON MEMBER REMOVAL
    # =========================================================================
    # Bob currently has access to family bills
    assert (await client.get(f"/api/v1/families/{family_id}/bills", headers=bob_h)).status_code == 200

    # Alice removes Bob from the household group
    remove_res = await client.delete(
        f"/api/v1/families/{family_id}/members/{bob.id}",
        headers=alice_h
    )
    assert remove_res.status_code == 204

    # Bob IMMEDIATELY gets 404 (not 403, group existence hidden from non-members!)
    assert (await client.get(f"/api/v1/families/{family_id}/bills", headers=bob_h)).status_code == 404
    assert (await client.get(f"/api/v1/families/{family_id}/bills/radar", headers=bob_h)).status_code == 404
    assert (await client.get(f"/api/v1/families/{family_id}", headers=bob_h)).status_code == 404

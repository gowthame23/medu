from decimal import Decimal
import pytest
from httpx import AsyncClient
from app.services.liability import calculate_monthly_emi, generate_amortization_schedule
from datetime import date


def test_emi_reference_math():
    # 1. Standard ₹10,00,000 at 8.5% for 120 months (10 years)
    principal = Decimal("1000000.00")
    rate = Decimal("8.50")
    tenure = 120
    emi = calculate_monthly_emi(principal, rate, tenure)
    assert emi == Decimal("12398.57")

    # Amortization final installment clears balance to 0.00 exactly!
    schedule, total_p, total_i = generate_amortization_schedule(
        principal=principal,
        annual_rate=rate,
        tenure_months=tenure,
        start_date=date(2026, 1, 1),
        monthly_emi=emi
    )
    assert schedule[-1].remaining_balance == Decimal("0.00")
    assert total_p == principal


@pytest.mark.asyncio
async def test_liability_api_endpoints(client: AsyncClient, create_user_fixture):
    user, token = await create_user_fixture("loan_user@test.com", "Loan Tester")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/loans",
        json={
            "loan_name": "SBI Home Loan",
            "principal_amount": "4500000.00",
            "interest_rate": "8.5",
            "tenure_months": 240
        },
        headers=headers
    )
    assert create_res.status_code == 201
    loan_id = create_res.json()["id"]

    # Daily Cost: (45,00,000 * 8.5) / 36500 = 1047.95
    daily_res = await client.get(f"/api/v1/loans/{loan_id}/daily-cost", headers=headers)
    assert daily_res.status_code == 200
    assert daily_res.json()["daily_interest_cost"] == "1047.95"

    # Prepayment Simulator: prepay 2,00,000 at month 12
    sim_res = await client.post(
        f"/api/v1/loans/{loan_id}/simulate-prepayment",
        json={
            "prepayment_amount": "200000.00",
            "prepayment_month": 12,
            "effect": "REDUCE_TENURE"
        },
        headers=headers
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["months_saved"] > 0
    assert Decimal(sim_data["interest_saved"]) > Decimal("0.00")

    # 1. Record regular payment of 15,000 principal
    pay_res = await client.post(
        f"/api/v1/loans/{loan_id}/payments",
        json={
            "payment_date": "2026-02-01",
            "principal_paid": "15000.00",
            "interest_paid": "31875.00"
        },
        headers=headers
    )
    assert pay_res.status_code == 201
    assert pay_res.json()["remaining_balance"] == "4485000.00"

    # 2. Record lump-sum prepayment of 5,00,000
    prep_res = await client.post(
        f"/api/v1/loans/{loan_id}/prepayments",
        json={
            "prepayment_date": "2026-03-01",
            "lump_sum_amount": "500000.00",
            "effect": "REDUCE_TENURE"
        },
        headers=headers
    )
    assert prep_res.status_code == 201
    assert prep_res.json()["lump_sum_amount"] == "500000.00"

    # 3. Dynamic remaining principal in list_loans is reduced from 45,00,000 to 39,85,000
    list_res = await client.get("/api/v1/loans", headers=headers)
    assert list_res.status_code == 200
    loans_list = list_res.json()
    assert len(loans_list) == 1
    assert loans_list[0]["remaining_principal"] == "3985000.00"

    # 4. Daily cost is dynamically recalculated based on 39,85,000
    daily_after = await client.get(f"/api/v1/loans/{loan_id}/daily-cost", headers=headers)
    assert daily_after.status_code == 200
    # (3985000 * 8.5) / 36500 = 928.01
    assert daily_after.json()["daily_interest_cost"] == "928.01"

    # 5. PATCH loan updates interest rate to 8.25% and recalculates monthly EMI
    patch_res = await client.patch(
        f"/api/v1/loans/{loan_id}",
        json={"interest_rate": "8.25", "loan_name": "SBI Concession Loan"},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["loan_name"] == "SBI Concession Loan"
    assert patch_res.json()["interest_rate"] == "8.25"

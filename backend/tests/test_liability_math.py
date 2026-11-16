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

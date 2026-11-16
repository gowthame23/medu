import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundException
from app.models.liability import LiabilitiesVault
from app.repositories.liability import LiabilityRepository
from app.schemas.liability import (
    LoanResponse,
    DailyCostResponse,
    AmortizationScheduleResponse,
    AmortizationInstallment,
    PrepaymentSimulateResponse,
)


def quantize_money(amount: Decimal) -> Decimal:
    """Rounds to 2 decimal places using ROUND_HALF_UP."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_monthly_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """
    Computes monthly EMI using pure Decimal.
    Zero-interest loans handled as principal / tenure_months.
    Formula: P * r * (1+r)^n / ((1+r)^n - 1)
    """
    if tenure_months <= 0:
        raise ValueError("Tenure months must be positive.")

    if annual_rate == Decimal("0"):
        return quantize_money(principal / Decimal(tenure_months))

    # r = annual rate / 12 / 100
    monthly_rate = annual_rate / Decimal("1200")
    one_plus_r = Decimal("1") + monthly_rate
    pow_factor = one_plus_r ** tenure_months

    numerator = principal * monthly_rate * pow_factor
    denominator = pow_factor - Decimal("1")

    emi = numerator / denominator
    return quantize_money(emi)


def generate_amortization_schedule(
    principal: Decimal,
    annual_rate: Decimal,
    tenure_months: int,
    start_date: date,
    monthly_emi: Decimal
) -> Tuple[List[AmortizationInstallment], Decimal, Decimal]:
    """
    Generates monthly amortization schedule.
    Keeps full precision internally and rounds each month consistently,
    with final installment adjusting for residual cents to ensure zero balance.
    """
    schedule = []
    balance = principal
    monthly_rate = annual_rate / Decimal("1200")
    total_interest = Decimal("0.00")
    total_principal = Decimal("0.00")

    for month in range(1, tenure_months + 1):
        if balance <= Decimal("0"):
            break

        # Interest for the month
        interest_part = quantize_money(balance * monthly_rate) if annual_rate > 0 else Decimal("0.00")

        # In final month, or if balance is less than principal part, adjust
        if month == tenure_months or balance + interest_part <= monthly_emi:
            principal_part = balance
            actual_emi = principal_part + interest_part
            balance = Decimal("0.00")
        else:
            principal_part = monthly_emi - interest_part
            balance = balance - principal_part

        total_interest += interest_part
        total_principal += principal_part

        # Advance month date
        payment_year = start_date.year + (start_date.month + month - 1) // 12
        payment_month = (start_date.month + month - 1) % 12 + 1
        payment_day = min(start_date.day, 28)
        payment_date = date(payment_year, payment_month, payment_day)

        schedule.append(
            AmortizationInstallment(
                month_number=month,
                payment_date=payment_date,
                emi=quantize_money(actual_emi if month == tenure_months else monthly_emi),
                principal_paid=quantize_money(principal_part),
                interest_paid=quantize_money(interest_part),
                remaining_balance=quantize_money(balance)
            )
        )

    return schedule, quantize_money(total_principal), quantize_money(total_interest)


class LiabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.liability_repo = LiabilityRepository(db)

    async def create_loan(
        self,
        user_id: uuid.UUID,
        loan_name: str,
        principal_amount: Decimal,
        interest_rate: Decimal,
        tenure_months: int,
        start_date: Optional[date] = None,
        currency: str = "INR"
    ) -> LoanResponse:
        s_date = start_date or date.today()
        emi = calculate_monthly_emi(principal_amount, interest_rate, tenure_months)

        loan = await self.liability_repo.create_loan(
            user_id=user_id,
            loan_name=loan_name,
            principal_amount=principal_amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            start_date=s_date,
            monthly_emi=emi,
            currency=currency
        )
        return LoanResponse(
            id=loan.id,
            loan_name=loan.loan_name,
            principal_amount=loan.principal_amount,
            interest_rate=loan.interest_rate,
            tenure_months=loan.tenure_months,
            start_date=loan.start_date,
            monthly_emi=loan.monthly_emi,
            currency=loan.currency,
            created_at=loan.created_at
        )

    async def get_loans(self, user_id: uuid.UUID) -> List[LoanResponse]:
        loans = await self.liability_repo.get_loans(user_id)
        return [
            LoanResponse(
                id=l.id,
                loan_name=l.loan_name,
                principal_amount=l.principal_amount,
                interest_rate=l.interest_rate,
                tenure_months=l.tenure_months,
                start_date=l.start_date,
                monthly_emi=l.monthly_emi,
                currency=l.currency,
                created_at=l.created_at
            )
            for l in loans
        ]

    async def get_daily_cost(self, user_id: uuid.UUID, loan_id: uuid.UUID) -> DailyCostResponse:
        loan = await self.liability_repo.get_loan_by_id(user_id, loan_id)
        if not loan:
            raise ResourceNotFoundException("Loan", "Loan not found in private vault")

        # Daily Cost = balance * annual_rate / 365 / 100
        daily_interest = (loan.principal_amount * loan.interest_rate) / Decimal("36500")

        return DailyCostResponse(
            loan_id=loan.id,
            loan_name=loan.loan_name,
            remaining_principal=loan.principal_amount,
            annual_rate=loan.interest_rate,
            daily_interest_cost=quantize_money(daily_interest),
            currency=loan.currency
        )

    async def get_amortization_schedule(
        self,
        user_id: uuid.UUID,
        loan_id: uuid.UUID
    ) -> AmortizationScheduleResponse:
        loan = await self.liability_repo.get_loan_by_id(user_id, loan_id)
        if not loan:
            raise ResourceNotFoundException("Loan", "Loan not found in private vault")

        schedule, total_p, total_i = generate_amortization_schedule(
            principal=loan.principal_amount,
            annual_rate=loan.interest_rate,
            tenure_months=loan.tenure_months,
            start_date=loan.start_date,
            monthly_emi=loan.monthly_emi
        )

        return AmortizationScheduleResponse(
            loan_id=loan.id,
            monthly_emi=loan.monthly_emi,
            total_principal=total_p,
            total_interest=total_i,
            total_payment=quantize_money(total_p + total_i),
            tenure_months=loan.tenure_months,
            schedule=schedule
        )

    async def simulate_prepayment(
        self,
        user_id: uuid.UUID,
        loan_id: uuid.UUID,
        prepayment_amount: Decimal,
        prepayment_month: int,
        effect: str = "REDUCE_TENURE"
    ) -> PrepaymentSimulateResponse:
        loan = await self.liability_repo.get_loan_by_id(user_id, loan_id)
        if not loan:
            raise ResourceNotFoundException("Loan", "Loan not found in private vault")

        # Baseline schedule
        _, _, baseline_interest = generate_amortization_schedule(
            principal=loan.principal_amount,
            annual_rate=loan.interest_rate,
            tenure_months=loan.tenure_months,
            start_date=loan.start_date,
            monthly_emi=loan.monthly_emi
        )

        monthly_rate = loan.interest_rate / Decimal("1200")
        balance = loan.principal_amount
        new_interest = Decimal("0.00")
        current_month = 1
        new_emi = loan.monthly_emi

        # Advance until prepayment month
        while current_month < prepayment_month and balance > Decimal("0"):
            interest_p = quantize_money(balance * monthly_rate)
            principal_p = loan.monthly_emi - interest_p
            balance -= principal_p
            new_interest += interest_p
            current_month += 1

        # Apply lump sum prepayment
        balance = max(Decimal("0.00"), balance - prepayment_amount)

        if effect == "REDUCE_EMI":
            remaining_tenure = max(1, loan.tenure_months - current_month + 1)
            new_emi = calculate_monthly_emi(balance, loan.interest_rate, remaining_tenure)
            while balance > Decimal("0"):
                interest_p = quantize_money(balance * monthly_rate)
                if balance + interest_p <= new_emi:
                    new_interest += interest_p
                    break
                principal_p = new_emi - interest_p
                balance -= principal_p
                new_interest += interest_p
                current_month += 1
            new_tenure = current_month
        else:
            # REDUCE_TENURE: keep EMI unchanged, tenure shaves off
            while balance > Decimal("0"):
                interest_p = quantize_money(balance * monthly_rate)
                if balance + interest_p <= loan.monthly_emi:
                    new_interest += interest_p
                    break
                principal_p = loan.monthly_emi - interest_p
                balance -= principal_p
                new_interest += interest_p
                current_month += 1
            new_tenure = current_month

        months_saved = max(0, loan.tenure_months - new_tenure)
        interest_saved = max(Decimal("0.00"), baseline_interest - quantize_money(new_interest))

        return PrepaymentSimulateResponse(
            original_tenure_months=loan.tenure_months,
            original_total_interest=baseline_interest,
            new_tenure_months=new_tenure,
            new_total_interest=quantize_money(new_interest),
            months_saved=months_saved,
            interest_saved=interest_saved,
            new_monthly_emi=new_emi,
            effect_applied=effect
        )

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import Field, field_validator

from app.schemas.common import StrictBaseModel, Money


class LoanCreateRequest(StrictBaseModel):
    loan_name: str = Field(min_length=1, max_length=100)
    principal_amount: Money
    interest_rate: Decimal = Field(ge=0, le=50)  # Annual % bounded between 0% and 50%
    tenure_months: int = Field(gt=0, le=600)  # Bounded to at most 600 months (50 years)
    start_date: Optional[date] = None

    @field_validator("interest_rate")
    @classmethod
    def validate_rate(cls, v: Decimal) -> Decimal:
        if isinstance(v, float):
            raise ValueError("Interest rate must not be float.")
        return Decimal(str(v))


class LoanResponse(StrictBaseModel):
    id: uuid.UUID
    loan_name: str
    principal_amount: Money
    remaining_principal: Optional[Money] = None
    interest_rate: Decimal
    tenure_months: int
    start_date: date
    monthly_emi: Money
    currency: str
    created_at: datetime


class LoanUpdateRequest(StrictBaseModel):
    loan_name: Optional[str] = Field(None, min_length=1, max_length=100)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    tenure_months: Optional[int] = Field(None, gt=0, le=600)


class LoanPaymentCreateRequest(StrictBaseModel):
    payment_date: date
    principal_paid: Money
    interest_paid: Money


class LoanPaymentResponse(StrictBaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    payment_date: date
    principal_paid: Money
    interest_paid: Money
    remaining_balance: Money
    created_at: datetime


class LoanPrepaymentCreateRequest(StrictBaseModel):
    prepayment_date: date
    lump_sum_amount: Money
    effect: str = "REDUCE_TENURE"  # REDUCE_TENURE or REDUCE_EMI


class LoanPrepaymentResponse(StrictBaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    prepayment_date: date
    lump_sum_amount: Money
    effect: str
    created_at: datetime


class DailyCostResponse(StrictBaseModel):
    loan_id: uuid.UUID
    loan_name: str
    remaining_principal: Money
    annual_rate: Decimal
    daily_interest_cost: Money  # balance * rate / 365
    currency: str


class AmortizationInstallment(StrictBaseModel):
    month_number: int
    payment_date: date
    emi: Money
    principal_paid: Money
    interest_paid: Money
    remaining_balance: Money


class AmortizationScheduleResponse(StrictBaseModel):
    loan_id: uuid.UUID
    monthly_emi: Money
    total_principal: Money
    total_interest: Money
    total_payment: Money
    tenure_months: int
    schedule: List[AmortizationInstallment]


class PrepaymentSimulateRequest(StrictBaseModel):
    prepayment_amount: Money
    prepayment_month: int = Field(ge=1)
    effect: str = "REDUCE_TENURE"  # REDUCE_TENURE or REDUCE_EMI


class PrepaymentSimulateResponse(StrictBaseModel):
    original_tenure_months: int
    original_total_interest: Money
    new_tenure_months: int
    new_total_interest: Money
    months_saved: int
    interest_saved: Money
    new_monthly_emi: Money
    effect_applied: str

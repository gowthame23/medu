import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.liability import LiabilityService
from app.schemas.liability import (
    LoanCreateRequest,
    LoanResponse,
    DailyCostResponse,
    AmortizationScheduleResponse,
    PrepaymentSimulateRequest,
    PrepaymentSimulateResponse,
)

router = APIRouter(prefix="/loans", tags=["Liabilities Vault (100% Private)"])


@router.get("", response_model=List[LoanResponse])
async def list_loans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    return await service.get_loans(current_user.id)


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    data: LoanCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    return await service.create_loan(
        user_id=current_user.id,
        loan_name=data.loan_name,
        principal_amount=data.principal_amount,
        interest_rate=data.interest_rate,
        tenure_months=data.tenure_months,
        start_date=data.start_date
    )


@router.get("/{id}", response_model=LoanResponse)
async def get_loan_details(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    loan = await service.liability_repo.get_loan_by_id(current_user.id, id)
    if not loan:
        from app.core.errors import ResourceNotFoundException
        raise ResourceNotFoundException("Loan", "Loan not found in private vault")
    return LoanResponse.model_validate(loan)


@router.get("/{id}/daily-cost", response_model=DailyCostResponse)
async def get_daily_cost(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    return await service.get_daily_cost(current_user.id, id)


@router.get("/{id}/amortization", response_model=AmortizationScheduleResponse)
async def get_amortization_schedule(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    return await service.get_amortization_schedule(current_user.id, id)


@router.post("/{id}/simulate-prepayment", response_model=PrepaymentSimulateResponse)
async def simulate_prepayment(
    id: uuid.UUID,
    data: PrepaymentSimulateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    return await service.simulate_prepayment(
        user_id=current_user.id,
        loan_id=id,
        prepayment_amount=data.prepayment_amount,
        prepayment_month=data.prepayment_month,
        effect=data.effect
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LiabilityService(db)
    await service.liability_repo.delete_loan(current_user.id, id)

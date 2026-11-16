import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import get_client_ip
from app.models.user import User
from app.services.bill import BillService
from app.services.payment import PaymentService
from app.schemas.bill import (
    UpcomingRadarCreateRequest,
    UpcomingRadarUpdateRequest,
    UpcomingRadarResponse,
    UpcomingRadarDetailResponse,
)
from app.schemas.payment import PaymentResponse

router = APIRouter(prefix="/bills", tags=["Personal Bills"])


@router.get("", response_model=List[UpcomingRadarResponse])
async def list_personal_bills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.get_personal_bills(current_user.id)


@router.get("/radar", response_model=List[UpcomingRadarResponse])
async def get_personal_radar(
    horizon_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.get_personal_radar(current_user.id, horizon_days=horizon_days)


@router.post("", response_model=UpcomingRadarResponse, status_code=status.HTTP_201_CREATED)
async def create_personal_bill(
    data: UpcomingRadarCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.create_personal_bill(
        user_id=current_user.id,
        title=data.title,
        amount=data.amount,
        due_date=data.due_date,
        consumer_number=data.consumer_number,
        category=data.category or "utility",
        recurrence_interval=data.recurrence_interval or "NONE"
    )


@router.get("/{id}", response_model=UpcomingRadarDetailResponse)
async def get_personal_bill_details(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.get_personal_bill(current_user.id, id)


@router.patch("/{id}", response_model=UpcomingRadarResponse)
async def update_personal_bill(
    id: uuid.UUID,
    data: UpcomingRadarUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    # Confirm ownership
    await service.get_personal_bill(current_user.id, id)
    updated = await service.bill_repo.update_bill(
        bill_id=id,
        title=data.title,
        amount=data.amount,
        due_date=data.due_date,
        consumer_number=data.consumer_number,
        category=data.category,
        recurrence_interval=data.recurrence_interval
    )
    return await service._enrich_bill_response(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_personal_bill(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    await service.get_personal_bill(current_user.id, id)
    await service.bill_repo.soft_delete_bill(id)


@router.post("/{id}/pay", response_model=PaymentResponse)
async def pay_personal_bill(
    id: uuid.UUID,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not idempotency_key:
        idempotency_key = f"key_{uuid.uuid4().hex}"

    service = PaymentService(db)
    ip_addr = get_client_ip(request)
    return await service.pay_bill(
        bill_id=id,
        idempotency_key=idempotency_key,
        payer=current_user,
        family_group_id=None,
        ip_address=ip_addr
    )


@router.post("/{id}/mark-paid", response_model=UpcomingRadarResponse)
async def mark_personal_bill_paid(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    ip_addr = get_client_ip(request)
    return await service.mark_personal_bill_paid(
        user=current_user,
        bill_id=id,
        ip_address=ip_addr
    )


@router.post("/{id}/payment/cancel", response_model=PaymentResponse)
async def cancel_personal_bill_payment(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PaymentService(db)
    ip_addr = get_client_ip(request)
    return await service.cancel_pending_payment(bill_id=id, user=current_user, ip_address=ip_addr)

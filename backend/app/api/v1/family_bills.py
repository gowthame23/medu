import uuid
from typing import List, Tuple, Optional
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_family_member, require_family_admin
from app.models.user import User
from app.models.family import FamilyMember
from app.services.bill import BillService
from app.services.payment import PaymentService
from app.schemas.bill import (
    UpcomingRadarCreateRequest,
    UpcomingRadarUpdateRequest,
    UpcomingRadarResponse,
    UpcomingRadarDetailResponse,
    MockBBPSFetchRequest,
    FetchedBillResponse,
)
from app.schemas.payment import (
    PaymentResponse,
    PaymentHistoryItemResponse,
)

router = APIRouter(prefix="/families/{id}", tags=["Family Bills & Payments"])


@router.get("/bills", response_model=List[UpcomingRadarResponse])
async def list_family_bills(
    id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.get_family_bills(id)


@router.get("/bills/radar", response_model=List[UpcomingRadarResponse])
async def get_family_radar(
    id: uuid.UUID,
    horizon_days: int = 7,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.get_family_radar(id, horizon_days=horizon_days)


@router.post("/bills", response_model=UpcomingRadarResponse, status_code=status.HTTP_201_CREATED)
async def create_family_bill(
    id: uuid.UUID,
    data: UpcomingRadarCreateRequest,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    admin_user, _ = auth_data
    service = BillService(db)
    return await service.create_family_bill(
        family_group_id=id,
        created_by_user_id=admin_user.id,
        title=data.title,
        amount=data.amount,
        due_date=data.due_date,
        consumer_number=data.consumer_number,
        category=data.category or "utility",
        recurrence_interval=data.recurrence_interval or "NONE"
    )


@router.get("/bills/{bid}", response_model=UpcomingRadarDetailResponse)
async def get_family_bill_details(
    id: uuid.UUID,
    bid: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.get_family_bill(id, bid)


@router.patch("/bills/{bid}", response_model=UpcomingRadarResponse)
async def update_family_bill(
    id: uuid.UUID,
    bid: uuid.UUID,
    data: UpcomingRadarUpdateRequest,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.update_family_bill(
        family_group_id=id,
        bill_id=bid,
        title=data.title,
        amount=data.amount,
        due_date=data.due_date,
        consumer_number=data.consumer_number,
        category=data.category,
        recurrence_interval=data.recurrence_interval
    )


@router.delete("/bills/{bid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family_bill(
    id: uuid.UUID,
    bid: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    await service.delete_family_bill(id, bid)


@router.post("/bills/{bid}/pay", response_model=PaymentResponse)
async def pay_family_bill(
    id: uuid.UUID,
    bid: uuid.UUID,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    payer, _ = auth_data
    if not idempotency_key:
        idempotency_key = f"key_{uuid.uuid4().hex}"

    service = PaymentService(db)
    return await service.pay_bill(
        bill_id=bid,
        idempotency_key=idempotency_key,
        payer=payer,
        family_group_id=id
    )


@router.post("/bills/{bid}/mark-paid", response_model=UpcomingRadarResponse)
async def mark_family_bill_paid(
    id: uuid.UUID,
    bid: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    payer, _ = auth_data
    service = BillService(db)
    return await service.mark_family_bill_paid(
        family_group_id=id,
        bill_id=bid,
        user=payer
    )


@router.post("/bills/{bid}/payment/cancel", response_model=PaymentResponse)
async def cancel_family_bill_payment(
    id: uuid.UUID,
    bid: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    payer, _ = auth_data
    service = PaymentService(db)
    return await service.cancel_pending_payment(
        bill_id=bid,
        user=payer,
        family_group_id=id
    )


@router.get("/payments", response_model=List[PaymentHistoryItemResponse])
async def list_family_payments(
    id: uuid.UUID,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_member),
    db: AsyncSession = Depends(get_db)
):
    service = PaymentService(db)
    rows = await service.payment_repo.get_family_payment_history(id)
    return [
        PaymentHistoryItemResponse(
            transaction_id=txn.id,
            bill_id=txn.bill_id,
            bill_title=title,
            amount=txn.amount,
            status=txn.status,
            payment_reference=txn.payment_reference,
            paid_by_display_name=txn.paid_by_display_name_snapshot,
            verified_timestamp=txn.verified_timestamp,
            created_at=txn.created_at
        )
        for txn, title in rows
    ]


@router.post("/bills/fetch-bbps", response_model=FetchedBillResponse)
async def fetch_bbps_bill(
    id: uuid.UUID,
    data: MockBBPSFetchRequest,
    auth_data: Tuple[User, FamilyMember] = Depends(require_family_admin),
    db: AsyncSession = Depends(get_db)
):
    service = BillService(db)
    return await service.fetch_bbps_mock_bill(data.biller_id, data.consumer_number)

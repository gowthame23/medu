import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundException, ForbiddenException
from app.models.bill import UpcomingRadar
from app.repositories.bill import BillRepository, mask_consumer_number
from app.repositories.payment import PaymentRepository
from app.schemas.bill import (
    UpcomingRadarResponse,
    UpcomingRadarDetailResponse,
    FetchedBillResponse,
)


class BillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bill_repo = BillRepository(db)
        self.payment_repo = PaymentRepository(db)

    async def _enrich_bill_response(self, bill: UpcomingRadar, include_full_consumer: bool = False) -> UpcomingRadarResponse:
        payment = await self.bill_repo.get_latest_successful_payment(bill.id)
        is_paid = (bill.bill_status in ("PAID", "PAID_UNVERIFIED"))
        masked = mask_consumer_number(bill.consumer_number)

        base_data = {
            "id": bill.id,
            "user_id": bill.user_id,
            "family_group_id": bill.family_group_id,
            "created_by_user_id": bill.created_by_user_id,
            "title": bill.title,
            "amount": bill.amount,
            "due_date": bill.due_date,
            "consumer_number_masked": masked,
            "category": bill.category,
            "bill_status": bill.bill_status,
            "recurrence_interval": bill.recurrence_interval,
            "is_paid": is_paid,
            "paid_at": bill.paid_at,
            "created_at": bill.created_at,
            "paid_by_display_name": payment.paid_by_display_name_snapshot if payment else None,
            "payment_reference": payment.payment_reference if payment else None,
        }

        if include_full_consumer:
            return UpcomingRadarDetailResponse(
                **base_data,
                consumer_number_full=bill.consumer_number
            )
        return UpcomingRadarResponse(**base_data)

    async def create_personal_bill(
        self,
        user_id: uuid.UUID,
        title: str,
        amount: Decimal,
        due_date: date,
        consumer_number: Optional[str] = None,
        category: str = "utility",
        recurrence_interval: str = "NONE"
    ) -> UpcomingRadarResponse:
        bill = await self.bill_repo.create_personal_bill(
            user_id=user_id,
            title=title,
            amount=amount,
            due_date=due_date,
            consumer_number=consumer_number,
            category=category,
            recurrence_interval=recurrence_interval
        )
        return await self._enrich_bill_response(bill)

    async def get_personal_bills(self, user_id: uuid.UUID) -> List[UpcomingRadarResponse]:
        bills = await self.bill_repo.get_personal_bills(user_id)
        return [await self._enrich_bill_response(b) for b in bills]

    async def get_personal_bill(self, user_id: uuid.UUID, bill_id: uuid.UUID) -> UpcomingRadarDetailResponse:
        bill = await self.bill_repo.get_personal_bill(user_id, bill_id)
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found")
        return await self._enrich_bill_response(bill, include_full_consumer=True)

    async def get_personal_radar(self, user_id: uuid.UUID, horizon_days: int = 7) -> List[UpcomingRadarResponse]:
        bills = await self.bill_repo.get_personal_radar(user_id, horizon_days)
        return [await self._enrich_bill_response(b) for b in bills]

    async def mark_personal_bill_paid(
        self,
        user: User,
        bill_id: uuid.UUID,
        ip_address: Optional[str] = None
    ) -> UpcomingRadarResponse:
        from app.services.payment import PaymentService
        payment_service = PaymentService(self.db)
        updated = await payment_service.settle_self_reported_payment(
            bill_id=bill_id,
            payer=user,
            family_group_id=None,
            ip_address=ip_address
        )
        return await self._enrich_bill_response(updated)

    async def create_family_bill(
        self,
        family_group_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        title: str,
        amount: Decimal,
        due_date: date,
        consumer_number: Optional[str] = None,
        category: str = "utility",
        recurrence_interval: str = "NONE"
    ) -> UpcomingRadarResponse:
        bill = await self.bill_repo.create_family_bill(
            family_group_id=family_group_id,
            created_by_user_id=created_by_user_id,
            title=title,
            amount=amount,
            due_date=due_date,
            consumer_number=consumer_number,
            category=category,
            recurrence_interval=recurrence_interval
        )
        return await self._enrich_bill_response(bill)

    async def get_family_bills(self, family_group_id: uuid.UUID) -> List[UpcomingRadarResponse]:
        bills = await self.bill_repo.get_family_bills(family_group_id)
        return [await self._enrich_bill_response(b) for b in bills]

    async def get_family_bill(self, family_group_id: uuid.UUID, bill_id: uuid.UUID) -> UpcomingRadarDetailResponse:
        bill = await self.bill_repo.get_family_bill(family_group_id, bill_id)
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found")
        return await self._enrich_bill_response(bill, include_full_consumer=True)

    async def get_family_radar(self, family_group_id: uuid.UUID, horizon_days: int = 7) -> List[UpcomingRadarResponse]:
        bills = await self.bill_repo.get_family_radar(family_group_id, horizon_days)
        return [await self._enrich_bill_response(b) for b in bills]

    async def mark_family_bill_paid(
        self,
        family_group_id: uuid.UUID,
        bill_id: uuid.UUID,
        user: User,
        ip_address: Optional[str] = None
    ) -> UpcomingRadarResponse:
        from app.services.payment import PaymentService
        payment_service = PaymentService(self.db)
        updated = await payment_service.settle_self_reported_payment(
            bill_id=bill_id,
            payer=user,
            family_group_id=family_group_id,
            ip_address=ip_address
        )
        return await self._enrich_bill_response(updated)

    async def update_family_bill(
        self,
        family_group_id: uuid.UUID,
        bill_id: uuid.UUID,
        title: Optional[str] = None,
        amount: Optional[Decimal] = None,
        due_date: Optional[date] = None,
        consumer_number: Optional[str] = None,
        category: Optional[str] = None,
        recurrence_interval: Optional[str] = None
    ) -> UpcomingRadarResponse:
        bill = await self.bill_repo.get_family_bill(family_group_id, bill_id)
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found")

        updated = await self.bill_repo.update_bill(
            bill_id=bill_id,
            title=title,
            amount=amount,
            due_date=due_date,
            consumer_number=consumer_number,
            category=category,
            recurrence_interval=recurrence_interval
        )
        return await self._enrich_bill_response(updated)

    async def delete_family_bill(self, family_group_id: uuid.UUID, bill_id: uuid.UUID) -> None:
        bill = await self.bill_repo.get_family_bill(family_group_id, bill_id)
        if not bill:
            raise ResourceNotFoundException("Bill", "Bill not found")
        await self.bill_repo.soft_delete_bill(bill_id)

    async def fetch_bbps_mock_bill(self, biller_id: str, consumer_number: str) -> FetchedBillResponse:
        """Simulates BBPS bill lookup."""
        from app.providers.mock_bbps import MockBBPSProvider
        provider = MockBBPSProvider()
        return await provider.fetch_bill(biller_id, consumer_number)

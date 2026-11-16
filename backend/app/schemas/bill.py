import uuid
from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from pydantic import Field

from app.schemas.common import StrictBaseModel, Money


class BillCategory(str, Enum):
    UTILITY = "utility"
    HOUSING = "housing"
    TELECOM = "telecom"
    SUBSCRIPTION = "subscription"
    OTHER = "other"


class RecurrenceInterval(str, Enum):
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class UpcomingRadarCreateRequest(StrictBaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: Money
    due_date: date
    consumer_number: Optional[str] = Field(None, max_length=100)
    category: Optional[BillCategory] = BillCategory.UTILITY
    recurrence_interval: Optional[RecurrenceInterval] = RecurrenceInterval.NONE


class UpcomingRadarUpdateRequest(StrictBaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[Money] = None
    due_date: Optional[date] = None
    consumer_number: Optional[str] = None
    category: Optional[BillCategory] = None
    recurrence_interval: Optional[RecurrenceInterval] = None


class UpcomingRadarResponse(StrictBaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    family_group_id: Optional[uuid.UUID]
    created_by_user_id: Optional[uuid.UUID]
    title: str
    amount: Money
    due_date: date
    consumer_number_masked: Optional[str] = None
    category: str
    bill_status: str  # UNPAID, PAID, OVERDUE
    recurrence_interval: str
    is_paid: bool
    paid_at: Optional[datetime]
    created_at: datetime

    # Attributions
    paid_by_display_name: Optional[str] = None
    payment_reference: Optional[str] = None


class UpcomingRadarDetailResponse(UpcomingRadarResponse):
    consumer_number_full: Optional[str] = None


class MockBBPSFetchRequest(StrictBaseModel):
    biller_id: str
    consumer_number: str


class FetchedBillResponse(StrictBaseModel):
    biller_name: str
    consumer_number: str
    amount: Money
    due_date: date
    category: str

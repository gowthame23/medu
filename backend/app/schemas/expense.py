import uuid
from datetime import date, datetime
from typing import Optional, List
from pydantic import Field

from app.schemas.common import StrictBaseModel, Money


class CategoryResponse(StrictBaseModel):
    id: uuid.UUID
    name: str
    icon: Optional[str] = None
    sort_order: int
    is_system_default: bool


class CategoryCreateRequest(StrictBaseModel):
    name: str = Field(min_length=1, max_length=50)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = 0


class DailyLogEntryCreateRequest(StrictBaseModel):
    category_id: uuid.UUID
    amount: Money


class DailyLogEntryResponse(StrictBaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_icon: Optional[str]
    amount: Money
    created_at: datetime


class DailyLogUpdateRequest(StrictBaseModel):
    notes: Optional[str] = None


class DailyLogResponse(StrictBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    log_date: date
    notes: Optional[str]
    total_spent: Money  # Computed dynamically from entries (SUM), no drift!
    entries: List[DailyLogEntryResponse]
    created_at: datetime

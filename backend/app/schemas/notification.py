import uuid
from datetime import datetime
from typing import Optional
from app.schemas.common import StrictBaseModel


class NotificationResponse(StrictBaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    related_bill_id: Optional[uuid.UUID]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

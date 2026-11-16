import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import Field

from app.schemas.common import StrictBaseModel, Money


class PaymentInitiateRequest(StrictBaseModel):
    # Idempotency Key passed via Header or Body
    payment_method: Optional[str] = "UPI"


class PaymentResponse(StrictBaseModel):
    transaction_id: uuid.UUID
    bill_id: uuid.UUID
    amount: Money
    status: str  # PENDING, SUCCESS, FAILED
    payment_reference: Optional[str]
    paid_by_display_name: Optional[str]
    verified_timestamp: Optional[datetime]
    failure_reason: Optional[str]
    sandbox: bool = False
    upi_intent_uri: Optional[str] = None


class PaymentHistoryItemResponse(StrictBaseModel):
    transaction_id: uuid.UUID
    bill_id: uuid.UUID
    bill_title: str
    amount: Money
    status: str
    payment_reference: Optional[str]
    paid_by_display_name: Optional[str]
    verified_timestamp: Optional[datetime]
    created_at: datetime

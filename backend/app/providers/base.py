from abc import ABC, abstractmethod
from decimal import Decimal
from typing import NamedTuple, Optional
from datetime import date


class PaymentIntent(NamedTuple):
    intent_id: str
    upi_intent_uri: str
    amount: Decimal


class PaymentResult(NamedTuple):
    success: bool
    payment_reference: Optional[str]
    failure_reason: Optional[str]


class FetchedBill(NamedTuple):
    biller_name: str
    consumer_number: str
    amount: Decimal
    due_date: date
    category: str


class PaymentProvider(ABC):
    @abstractmethod
    async def create_intent(self, amount: Decimal, reference_hint: str) -> PaymentIntent:
        pass

    @abstractmethod
    async def verify(self, intent_id: str) -> PaymentResult:
        pass


class BillFetchProvider(ABC):
    @abstractmethod
    async def fetch_bill(self, biller_id: str, consumer_number: str) -> FetchedBill:
        pass

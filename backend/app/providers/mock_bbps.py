from datetime import date, timedelta
from decimal import Decimal
from app.providers.base import BillFetchProvider, FetchedBill
from app.schemas.bill import FetchedBillResponse


class MockBBPSProvider(BillFetchProvider):
    async def fetch_bill(self, biller_id: str, consumer_number: str) -> FetchedBillResponse:
        biller_map = {
            "BESCOM": ("Electricity Bill (BESCOM)", Decimal("2450.00"), "Utilities"),
            "AIRTEL": ("Airtel Fiber Broadband", Decimal("1179.00"), "Utilities"),
            "GAIL": ("PNG Cooking Gas (GAIL)", Decimal("890.00"), "Utilities"),
            "SOCIETY": ("Apartment Maintenance", Decimal("4200.00"), "Housing"),
            "NETFLIX": ("Netflix Premium (Family)", Decimal("649.00"), "Subscriptions"),
        }

        b_key = biller_id.upper()
        if b_key in biller_map:
            name, amount, cat = biller_map[b_key]
        else:
            name = f"Utility Bill ({biller_id})"
            amount = Decimal("1500.00")
            cat = "Utilities"

        tomorrow = date.today() + timedelta(days=1)
        return FetchedBillResponse(
            biller_name=name,
            consumer_number=consumer_number,
            amount=amount,
            due_date=tomorrow,
            category=cat
        )

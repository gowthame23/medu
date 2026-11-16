import secrets
from decimal import Decimal
from urllib.parse import quote
from app.core.config import settings
from app.providers.base import PaymentProvider, PaymentIntent, PaymentResult


class SandboxUPIProvider(PaymentProvider):
    def __init__(self):
        if settings.APP_ENV == "production" and settings.ENABLE_SANDBOX_PAYMENTS:
            raise RuntimeError("CRITICAL SECURITY ERROR: Sandbox payments cannot be enabled in production.")

    async def create_intent(self, amount: Decimal, reference_hint: str) -> PaymentIntent:
        intent_id = f"intent_{secrets.token_hex(12)}"
        txn_ref = f"MEND-{secrets.token_hex(4).upper()}"
        payee_vpa = "mend.bbps@yesbank"
        payee_name = quote("Mend Household Bills")
        note = quote(f"Payment for {reference_hint}")

        # Standard NPCI UPI Intent URI
        upi_intent_uri = (
            f"upi://pay?pa={payee_vpa}&pn={payee_name}&am={amount:.2f}&cu=INR&tr={txn_ref}&tn={note}"
        )

        return PaymentIntent(
            intent_id=intent_id,
            upi_intent_uri=upi_intent_uri,
            amount=amount
        )

    async def verify(self, intent_id: str, force_outcome: str = "SUCCESS") -> PaymentResult:
        if force_outcome == "FAILED":
            return PaymentResult(
                success=False,
                payment_reference=None,
                failure_reason="Simulated bank rejection or insufficient balance"
            )

        txn_ref = f"UPI-VERIFIED-{secrets.token_hex(6).upper()}"
        return PaymentResult(
            success=True,
            payment_reference=txn_ref,
            failure_reason=None
        )

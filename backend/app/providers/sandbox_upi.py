import hmac
import hashlib
import time
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

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
        timestamp_str: str,
        secret: str
    ) -> bool:
        """
        Verifies HMAC-SHA256 signature and protects against replay attacks (5 min tolerance).
        """
        try:
            ts = int(timestamp_str)
            now = int(time.time())
            # 5-minute replay window tolerance
            if abs(now - ts) > 300:
                return False

            # Signed string format: {timestamp}.{payload}
            signed_payload = f"{ts}.".encode("utf-8") + payload_bytes
            expected_sig = hmac.new(
                secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_sig, signature)
        except Exception:
            return False

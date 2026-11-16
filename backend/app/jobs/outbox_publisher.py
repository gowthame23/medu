from datetime import datetime, timezone, timedelta
import uuid
import smtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.models.notification import Notification
from app.models.family import FamilyMember
from app.core.security import decrypt_outbox_payload
from app.providers.notify import get_email_sender, get_sms_sender


async def publish_pending_outbox_events(session: AsyncSession) -> int:
    """
    Polls pending OutboxEvents and dispatches them (notifications, verification email/SMS).
    Uses SKIP LOCKED for safe concurrent multi-worker processing
    and exponential backoff retry.
    Wipes encrypted verification payload upon successful delivery.
    """
    now = datetime.now(timezone.utc)
    query = (
        select(OutboxEvent)
        .where(
            OutboxEvent.status == "PENDING",
            OutboxEvent.next_attempt_at <= now
        )
        .order_by(OutboxEvent.created_at.asc())
        .limit(20)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(query)
    events = result.scalars().all()
    published_count = 0

    for event in events:
        try:
            if event.event_type in ("PAYMENT_SUCCEEDED", "BILL_MARKED_PAID"):
                payload = event.payload
                family_group_id_str = payload.get("family_group_id")
                payer_id_str = payload.get("payer_id")

                if family_group_id_str:
                    # Notify every group member EXCEPT payer
                    group_id = uuid.UUID(family_group_id_str)
                    payer_id = uuid.UUID(payer_id_str) if payer_id_str else None

                    mem_query = select(FamilyMember).where(FamilyMember.family_group_id == group_id)
                    mem_res = await session.execute(mem_query)
                    members = mem_res.scalars().all()

                    for member in members:
                        if member.user_id != payer_id:
                            notif = Notification(
                                user_id=member.user_id,
                                type="PAYMENT_SUCCESS",
                                title="Household Bill Settled",
                                message=f"✓ {payload.get('bill_title')} was paid by {payload.get('payer_name')} (₹{payload.get('amount')})",
                                related_bill_id=uuid.UUID(payload.get("bill_id")),
                                is_read=False
                            )
                            session.add(notif)
                else:
                    # Personal bill
                    if payer_id_str:
                        notif = Notification(
                            user_id=uuid.UUID(payer_id_str),
                            type="PAYMENT_SUCCESS",
                            title="Bill Paid",
                            message=f"✓ {payload.get('bill_title')} was paid successfully (₹{payload.get('amount')})",
                            related_bill_id=uuid.UUID(payload.get("bill_id")),
                            is_read=False
                        )
                        session.add(notif)

            elif event.event_type == "VERIFICATION_EMAIL_DISPATCH":
                decrypted = decrypt_outbox_payload(event.payload)
                sender = get_email_sender()
                await sender.send_email(
                    to_email=decrypted["to_email"],
                    subject=decrypted.get("subject", "Mend Verification Code"),
                    body=decrypted["body"]
                )
                # Sensitive payload wiped on delivery
                event.payload = {}

            elif event.event_type == "VERIFICATION_PHONE_DISPATCH":
                decrypted = decrypt_outbox_payload(event.payload)
                sender = get_sms_sender()
                await sender.send_sms(
                    to_phone_e164=decrypted["to_phone_e164"],
                    message=decrypted["message"]
                )
                # Sensitive payload wiped on delivery
                event.payload = {}

            event.status = "DELIVERED"
            event.processed_at = datetime.now(timezone.utc)
            published_count += 1
        except Exception as e:
            event.attempts += 1
            if isinstance(e, smtplib.SMTPAuthenticationError):
                err_msg = "SMTPAuthenticationError: Authentication failed"
            else:
                err_msg = str(e)
            event.last_error = err_msg
            backoff_seconds = (2 ** event.attempts) * 15
            event.next_attempt_at = now + timedelta(seconds=backoff_seconds)
            if event.attempts >= 5:
                event.status = "DEAD"

    if published_count > 0 or len(events) > 0:
        await session.commit()

    return published_count

import pytest
import uuid
import smtplib
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.core.security import encrypt_outbox_payload, decrypt_outbox_payload
from app.models.outbox import OutboxEvent
from app.jobs.outbox_publisher import publish_pending_outbox_events
from app.providers.notify import (
    ConsoleEmailSender,
    ConsoleSmsSender,
    SmtpEmailSender,
    TwilioSmsSender,
    Msg91SmsSender,
    get_email_sender,
    get_sms_sender,
)


@pytest.mark.asyncio
async def test_console_senders():
    email_sender = ConsoleEmailSender()
    sms_sender = ConsoleSmsSender()

    with patch("app.providers.notify.logger.info") as mock_info:
        await email_sender.send_email("test@example.com", "Test Subject", "Hello World")
        await sms_sender.send_sms("+919876543210", "Your code is 123456")

        assert mock_info.call_count == 2
        calls = [call.args[0] for call in mock_info.call_args_list]
        assert any("test@example.com" in c for c in calls)
        assert any("+919876543210" in c for c in calls)


@pytest.mark.asyncio
async def test_smtp_sender_refuses_plaintext():
    sender = SmtpEmailSender(use_tls=False)
    with pytest.raises(ValueError, match="Plaintext SMTP transmission is refused"):
        await sender.send_email("test@example.com", "Subject", "Body")


@pytest.mark.asyncio
async def test_smtp_sender_tls_and_timeout():
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        user="testuser",
        password="secretpassword",
        from_email="noreply@example.com",
        use_tls=True,
        timeout=10.0
    )

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        await sender.send_email("recipient@example.com", "Subj", "Message Body")

        mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=10.0)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("testuser", "secretpassword")
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_sms_gateway_stubs_raise_not_implemented():
    twilio = TwilioSmsSender()
    msg91 = Msg91SmsSender()

    with pytest.raises(NotImplementedError, match="NOT RUN"):
        await twilio.send_sms("+919876543210", "code")

    with pytest.raises(NotImplementedError, match="NOT RUN"):
        await msg91.send_sms("+919876543210", "code")


@pytest.mark.asyncio
async def test_outbox_verification_email_delivery_and_payload_wiped(db_session):
    encrypted = encrypt_outbox_payload({
        "to_email": "user@example.com",
        "subject": "Verification Code",
        "body": "Your code is 654321"
    })
    event_id = uuid.uuid4()
    event = OutboxEvent(
        id=event_id,
        event_type="VERIFICATION_EMAIL_DISPATCH",
        aggregate_type="VERIFICATION",
        aggregate_id=str(uuid.uuid4()),
        payload=encrypted,
        dedupe_key=f"ver_email_{uuid.uuid4()}",
        status="PENDING",
        attempts=0,
        next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    db_session.add(event)
    await db_session.commit()

    fake_sender = AsyncMock()
    with patch("app.jobs.outbox_publisher.get_email_sender", return_value=fake_sender):
        published = await publish_pending_outbox_events(db_session)
        assert published == 1

    fake_sender.send_email.assert_awaited_once_with(
        to_email="user@example.com",
        subject="Verification Code",
        body="Your code is 654321"
    )

    # Check database state: payload must be cleared to {}
    res = await db_session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
    delivered_event = res.scalar_one()
    assert delivered_event.status == "DELIVERED"
    assert delivered_event.payload == {}
    assert delivered_event.processed_at is not None


@pytest.mark.asyncio
async def test_outbox_verification_phone_delivery_and_payload_wiped(db_session):
    encrypted = encrypt_outbox_payload({
        "to_phone_e164": "+919876543210",
        "message": "Your code is 123456"
    })
    event_id = uuid.uuid4()
    event = OutboxEvent(
        id=event_id,
        event_type="VERIFICATION_PHONE_DISPATCH",
        aggregate_type="VERIFICATION",
        aggregate_id=str(uuid.uuid4()),
        payload=encrypted,
        dedupe_key=f"ver_phone_{uuid.uuid4()}",
        status="PENDING",
        attempts=0,
        next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    db_session.add(event)
    await db_session.commit()

    fake_sender = AsyncMock()
    with patch("app.jobs.outbox_publisher.get_sms_sender", return_value=fake_sender):
        published = await publish_pending_outbox_events(db_session)
        assert published == 1

    fake_sender.send_sms.assert_awaited_once_with(
        to_phone_e164="+919876543210",
        message="Your code is 123456"
    )

    res = await db_session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
    delivered_event = res.scalar_one()
    assert delivered_event.status == "DELIVERED"
    assert delivered_event.payload == {}


@pytest.mark.asyncio
async def test_outbox_verification_retry_and_dead_letter(db_session):
    encrypted = encrypt_outbox_payload({
        "to_email": "fail@example.com",
        "body": "Your code"
    })
    event_id = uuid.uuid4()
    event = OutboxEvent(
        id=event_id,
        event_type="VERIFICATION_EMAIL_DISPATCH",
        aggregate_type="VERIFICATION",
        aggregate_id=str(uuid.uuid4()),
        payload=encrypted,
        dedupe_key=f"ver_fail_{uuid.uuid4()}",
        status="PENDING",
        attempts=4,  # Next failure will push it to 5 (DEAD)
        next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    db_session.add(event)
    await db_session.commit()

    failing_sender = AsyncMock()
    failing_sender.send_email.side_effect = smtplib.SMTPAuthenticationError(535, b"Invalid credentials")

    with patch("app.jobs.outbox_publisher.get_email_sender", return_value=failing_sender):
        published = await publish_pending_outbox_events(db_session)
        assert published == 0

    res = await db_session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
    dead_event = res.scalar_one()
    assert dead_event.status == "DEAD"
    assert dead_event.attempts == 5
    assert "Authentication failed" in dead_event.last_error
    # Sensitive password or raw bytes must not appear in last_error
    assert "Invalid credentials" not in dead_event.last_error

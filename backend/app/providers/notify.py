import abc
import asyncio
import logging
import ssl
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSender(abc.ABC):
    @abc.abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str) -> None:
        """Sends an email message to the target recipient."""
        pass


class SmsSender(abc.ABC):
    @abc.abstractmethod
    async def send_sms(self, to_phone_e164: str, message: str) -> None:
        """Sends an SMS message to the target E.164 phone number."""
        pass


class ConsoleEmailSender(EmailSender):
    """Dev/Test email sender that logs to console without network dispatch."""
    async def send_email(self, to_email: str, subject: str, body: str) -> None:
        logger.info(f"[CONSOLE EMAIL] To: {to_email} | Subject: {subject} | Body: {body}")


class SmtpEmailSender(EmailSender):
    """Production/Staging SMTP email sender utilizing Python standard library smtplib with TLS."""
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: Optional[bool] = None,
        timeout: float = 10.0,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.SMTP_FROM
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.timeout = timeout

    def _send_sync(self, to_email: str, subject: str, body: str) -> None:
        if not self.use_tls:
            raise ValueError("Plaintext SMTP transmission is refused: TLS (STARTTLS) is required.")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            server.starttls(context=context)
            if self.user and self.password:
                server.login(self.user, self.password)
            server.send_message(msg)

    async def send_email(self, to_email: str, subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_sync, to_email, subject, body)


class ConsoleSmsSender(SmsSender):
    """Dev/Test SMS sender that logs to console without network dispatch."""
    async def send_sms(self, to_phone_e164: str, message: str) -> None:
        logger.info(f"[CONSOLE SMS] To: {to_phone_e164} | Message: {message}")


# Stubs for real gateways
class TwilioSmsSender(SmsSender):
    """Stub gateway implementation for Twilio Programmable Messaging."""
    def __init__(self, account_sid: str = "", auth_token: str = "", from_number: str = ""):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send_sms(self, to_phone_e164: str, message: str) -> None:
        raise NotImplementedError(
            "Twilio SMS gateway requires live credentials and external API connectivity (NOT RUN in sandbox/offline)."
        )


class Msg91SmsSender(SmsSender):
    """Stub gateway implementation for MSG91 Indian SMS Gateway."""
    def __init__(self, auth_key: str = "", sender_id: str = ""):
        self.auth_key = auth_key
        self.sender_id = sender_id

    async def send_sms(self, to_phone_e164: str, message: str) -> None:
        raise NotImplementedError(
            "MSG91 SMS gateway requires live credentials and DLT template approval (NOT RUN in sandbox/offline)."
        )


def get_email_sender() -> EmailSender:
    """Factory returning configured email sender."""
    if settings.EMAIL_PROVIDER == "smtp":
        return SmtpEmailSender()
    return ConsoleEmailSender()


def get_sms_sender() -> SmsSender:
    """Factory returning configured SMS sender."""
    if settings.SMS_PROVIDER == "twilio":
        return TwilioSmsSender()
    elif settings.SMS_PROVIDER == "msg91":
        return Msg91SmsSender()
    return ConsoleSmsSender()

"""Manual smoke script for Gmail/SMTP verification delivery.
Usage:
    python scripts/smtp_smoke.py <recipient>

Reads SMTP credentials strictly from environment variables:
    SMTP_HOST (default: smtp.gmail.com)
    SMTP_PORT (default: 587)
    SMTP_USER
    SMTP_PASSWORD
    SMTP_FROM (default: noreply@mend.local)
    SMTP_USE_TLS (default: True)

DO NOT COMMIT OR LOG CREDENTIALS.
"""
import os
import sys
import ssl
import smtplib
from email.message import EmailMessage


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/smtp_smoke.py <recipient_email>")
        sys.exit(1)

    recipient = sys.argv[1].strip()
    if not recipient or "@" not in recipient:
        print(f"Error: Invalid recipient email '{recipient}'")
        sys.exit(1)

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("SMTP_FROM", user or "noreply@mend.local")
    use_tls_str = os.environ.get("SMTP_USE_TLS", "true").lower()
    use_tls = use_tls_str in ("true", "1", "yes")

    if not use_tls:
        print("Error: Plaintext SMTP is forbidden. TLS (STARTTLS) is required.")
        sys.exit(1)

    if not user or not password:
        print("Error: SMTP_USER and SMTP_PASSWORD must be provided in environment.")
        sys.exit(1)

    msg = EmailMessage()
    msg["Subject"] = "Mend SMTP Smoke Test"
    msg["From"] = from_email
    msg["To"] = recipient
    msg.set_content(
        "This is an automated verification smoke test message from Mend.\n"
        "If you received this, Gmail SMTP integration is functioning properly."
    )

    print(f"Connecting to SMTP server at {host}:{port} (TLS required, timeout=10s)...")
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(host, port, timeout=10.0) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
        print("Smoke test email successfully sent.")
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP Authentication failed. Check your SMTP_USER and App Password.")
        sys.exit(1)
    except Exception as e:
        print(f"Error sending email: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

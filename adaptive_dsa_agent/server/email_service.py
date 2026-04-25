# Send OTP email via Gmail SMTP using an App Password.

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from smtplib import SMTPAuthenticationError, SMTPException

from .settings import get_api_settings


class SmtpNotConfiguredError(Exception):
    # raised when GMAIL_USER / GMAIL_APP_PASSWORD are empty.
    pass


def send_otp_email(to_addr: str, code: str) -> None:
    s = get_api_settings()
    # google app passwords often get copied with spaces; SMTP wants 16 chars, no spaces.
    app_pw = (s.gmail_app_password or "").replace(" ", "").strip()
    user = (s.gmail_user or "").strip()
    if not user or not app_pw:
        raise SmtpNotConfiguredError("Set GMAIL_USER and GMAIL_APP_PASSWORD in adaptive_dsa_agent/.env")

    msg = EmailMessage()
    msg["Subject"] = "Your DSA By NOVA sign-in code"
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(
        f"Your DSA By NOVA one-time code is: {code}\n\n"
        "It expires in a few minutes. If you didn't request this, ignore this email."
    )

    host = s.gmail_smtp_host
    port = s.gmail_smtp_port
    timeout = s.gmail_smtp_timeout_seconds
    context = ssl.create_default_context()

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=timeout) as server:
                server.login(user, app_pw)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.starttls(context=context)
                server.login(user, app_pw)
                server.send_message(msg)
    except SMTPAuthenticationError as e:
        raise RuntimeError(
            "Gmail rejected the sign-in. Use a 16-character App Password (Google Account -> "
            "Security -> 2-Step Verification -> App passwords), not your normal password. "
            f"Details: {e!s}"
        ) from e
    except (OSError, SMTPException) as e:
        # timeouts, connection refused, TLS issues — turn into a short message.
        raise RuntimeError(
            f"Could not reach Gmail SMTP at {host}:{port} within {timeout}s. "
            "If port 587 is blocked, try GMAIL_SMTP_PORT=465 in .env. "
            f"Error: {e!s}"
        ) from e

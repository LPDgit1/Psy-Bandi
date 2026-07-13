from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    delivery_mode: str
    provider_message_id: str | None = None
    error_message: str | None = None


def _message(*, recipient: str, subject: str, body_text: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body_text)
    return message


def _write_to_outbox(message: EmailMessage) -> str:
    outbox = Path(settings.email_outbox_dir)
    outbox.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = outbox / f"{timestamp}.eml"
    path.write_text(message.as_string(), encoding="utf-8")
    return str(path)


def send_email(*, recipient: str, subject: str, body_text: str) -> EmailDeliveryResult:
    mode = settings.email_delivery_mode.strip().lower()
    message = _message(recipient=recipient, subject=subject, body_text=body_text)

    if mode in {"disabled", "none"}:
        return EmailDeliveryResult(status="skipped", delivery_mode=mode)

    if mode == "smtp":
        if not settings.smtp_host:
            return EmailDeliveryResult(
                status="failed",
                delivery_mode=mode,
                error_message="SMTP_HOST non configurato.",
            )
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
            return EmailDeliveryResult(status="sent", delivery_mode=mode)
        except Exception as exc:
            return EmailDeliveryResult(
                status="failed",
                delivery_mode=mode,
                error_message=str(exc),
            )

    path = _write_to_outbox(message)
    return EmailDeliveryResult(status="sent", delivery_mode="file", provider_message_id=path)

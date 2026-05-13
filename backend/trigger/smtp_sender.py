from __future__ import annotations

import smtplib
from email.message import EmailMessage

from backend.config import Settings


def send_reply(settings: Settings, *, to: str, subject: str, body: str) -> str:
    if not (
        settings.smtp_host
        and settings.smtp_username
        and settings.smtp_password
        and settings.smtp_from
    ):
        raise RuntimeError("SMTP not configured")

    normalized_subject = _reply_subject(subject)
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = normalized_subject
    message.set_content(body)

    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

    return normalized_subject


def _reply_subject(subject: str) -> str:
    stripped = subject.strip()
    if stripped.casefold().startswith("re:"):
        return stripped
    return f"Re: {stripped}"

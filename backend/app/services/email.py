"""Email delivery via SMTP (stdlib smtplib, thread offloaded)."""
from __future__ import annotations

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings


def _send_sync(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        return
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = formataddr((settings.app_name, settings.smtp_from))
    message["To"] = to_email
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to_email], message.as_string())


async def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        return
    await asyncio.to_thread(_send_sync, to_email, subject, body)

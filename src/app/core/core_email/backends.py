"""Direct email delivery backends."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage as SMTPMessage
from typing import Protocol

from app.core.core_email.models import EmailMessage
from app.core.core_email.settings import EmailSettings

logger = logging.getLogger("app_logger")


class EmailBackend(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailBackend:
    """Safe development backend that logs metadata without message contents."""

    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "Email accepted by console backend: subject=%r recipients=%s", message.subject, len(message.recipients)
        )


class SMTPEmailBackend:
    def __init__(self, settings: EmailSettings) -> None:
        self._settings = settings

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        settings = self._settings
        host = settings.EMAIL_SMTP_HOST
        if host is None:
            raise RuntimeError("SMTP host is not configured")
        smtp_message = SMTPMessage()
        smtp_message["Subject"] = message.subject
        smtp_message["From"] = settings.EMAIL_FROM
        smtp_message["To"] = ", ".join(message.recipients)
        if message.reply_to:
            smtp_message["Reply-To"] = message.reply_to
        for name, value in message.headers.items():
            smtp_message[name] = value
        smtp_message.set_content(message.text)
        if message.html:
            smtp_message.add_alternative(message.html, subtype="html")

        smtp_class = smtplib.SMTP_SSL if settings.EMAIL_SMTP_SSL else smtplib.SMTP
        with smtp_class(
            host,
            settings.EMAIL_SMTP_PORT,
            timeout=settings.EMAIL_TIMEOUT_SECONDS,
        ) as client:
            if settings.EMAIL_SMTP_STARTTLS and not settings.EMAIL_SMTP_SSL:
                client.starttls()
            if settings.EMAIL_SMTP_USERNAME:
                password = settings.EMAIL_SMTP_PASSWORD.get_secret_value() if settings.EMAIL_SMTP_PASSWORD else ""
                client.login(settings.EMAIL_SMTP_USERNAME, password)
            client.send_message(smtp_message)


__all__ = ["ConsoleEmailBackend", "EmailBackend", "SMTPEmailBackend"]

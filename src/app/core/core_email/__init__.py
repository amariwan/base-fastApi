"""Public API for queue-aware email delivery."""

from app.core.core_email.backends import ConsoleEmailBackend, EmailBackend, SMTPEmailBackend
from app.core.core_email.celery import CeleryTaskRegistrar, register_celery_email_task
from app.core.core_email.dispatcher import CeleryEmailQueue, EmailDeliveryMode, EmailDispatcher, EmailQueue
from app.core.core_email.factory import build_email_backend, close_email_dispatcher, get_email_dispatcher
from app.core.core_email.models import EmailMessage
from app.core.core_email.settings import EmailBackendName, EmailSettings, get_email_settings

__all__ = [
    "CeleryEmailQueue",
    "CeleryTaskRegistrar",
    "ConsoleEmailBackend",
    "EmailBackend",
    "EmailBackendName",
    "EmailDeliveryMode",
    "EmailDispatcher",
    "EmailMessage",
    "EmailQueue",
    "EmailSettings",
    "SMTPEmailBackend",
    "build_email_backend",
    "close_email_dispatcher",
    "get_email_dispatcher",
    "get_email_settings",
    "register_celery_email_task",
]

"""Email delivery settings."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailBackendName(StrEnum):
    CONSOLE = "console"
    SMTP = "smtp"


class EmailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.dev"), case_sensitive=False, extra="ignore")

    EMAIL_BACKEND: EmailBackendName = EmailBackendName.CONSOLE
    EMAIL_FROM: str = "noreply@localhost"
    EMAIL_SMTP_HOST: str | None = None
    EMAIL_SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    EMAIL_SMTP_USERNAME: str | None = None
    EMAIL_SMTP_PASSWORD: SecretStr | None = None
    EMAIL_SMTP_STARTTLS: bool = True
    EMAIL_SMTP_SSL: bool = False
    EMAIL_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)
    EMAIL_USE_CELERY: bool = False
    EMAIL_CELERY_BROKER_URL: str | None = None
    EMAIL_CELERY_TASK_NAME: str = "app.core.email.send"

    @model_validator(mode="after")
    def validate_selected_backends(self) -> EmailSettings:
        if self.EMAIL_BACKEND is EmailBackendName.SMTP and not self.EMAIL_SMTP_HOST:
            raise ValueError("EMAIL_SMTP_HOST is required for the SMTP backend")
        if self.EMAIL_USE_CELERY and not self.EMAIL_CELERY_BROKER_URL:
            raise ValueError("EMAIL_CELERY_BROKER_URL is required when EMAIL_USE_CELERY=true")
        return self


@lru_cache(maxsize=1)
def get_email_settings() -> EmailSettings:
    return EmailSettings()


__all__ = ["EmailBackendName", "EmailSettings", "get_email_settings"]

"""Storage configuration via environment variables."""

from collections.abc import Mapping
from enum import StrEnum
from functools import lru_cache
from typing import cast

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageBackend(StrEnum):
    """Supported storage backends."""

    FILESYSTEM = "filesystem"
    S3 = "s3"


class StorageSettings(BaseSettings):
    """S3-compatible storage configuration.

    Env vars
    --------
    STORAGE_BACKEND       s3 | filesystem (default: s3)
    S3_ENDPOINT           Custom endpoint URL (e.g. MinIO)
    accessKey | S3_ACCESS_KEY_ID           Access key
    secretKey | S3_SECRET_ACCESS_KEY       Secret key
    S3_BUCKET             S3 bucket name
    S3_REGION             AWS region
    S3_SECURE             Use HTTPS (default: True)
    S3_ADDRESSING_STYLE   path | virtual | auto (default: auto)
    S3_PREFIX             Key prefix for logical isolation
    FILESYSTEM_ROOT       Root directory for filesystem backend (default: /data)
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.dev"),
        case_sensitive=False,
        extra="ignore",
    )

    # Default to S3 for environments without local storage.
    STORAGE_BACKEND: StorageBackend = StorageBackend.S3

    # S3 settings
    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY_ID: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("accessKey", "S3_ACCESS_KEY_ID"),
    )
    S3_SECRET_ACCESS_KEY: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("secretKey", "S3_SECRET_ACCESS_KEY"),
    )
    S3_BUCKET: str = ""
    S3_REGION: str | None = None
    S3_SECURE: bool = True
    S3_ADDRESSING_STYLE: str = "auto"
    S3_PREFIX: str = ""

    # Filesystem settings
    FILESYSTEM_ROOT: str = "/data"

    @model_validator(mode="before")
    @classmethod
    def _normalize_s3_credential_aliases(cls, data: object) -> object:
        """Map cluster-provided legacy S3 credential keys to canonical fields."""
        if not isinstance(data, Mapping):
            return data

        mapping = cast(Mapping[object, object], data)
        normalized: dict[str, object] = {str(key): value for key, value in mapping.items()}
        lowered = {str(key).lower(): value for key, value in normalized.items()}

        if normalized.get("S3_ACCESS_KEY_ID") in (None, ""):
            access_key = lowered.get("s3_access_key_id") or lowered.get("accesskey")
            if access_key not in (None, ""):
                normalized["S3_ACCESS_KEY_ID"] = access_key

        if normalized.get("S3_SECRET_ACCESS_KEY") in (None, ""):
            secret_key = lowered.get("s3_secret_access_key") or lowered.get("secretkey")
            if secret_key not in (None, ""):
                normalized["S3_SECRET_ACCESS_KEY"] = secret_key

        return normalized


@lru_cache(maxsize=1)
def get_storage_settings() -> StorageSettings:
    """Return a cached singleton ``StorageSettings`` instance."""
    return StorageSettings()

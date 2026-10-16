"""Tests for storage factory and settings."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.core.core_storage.exceptions import StorageConfigError
from app.core.core_storage.factory import get_storage_client
from app.core.core_storage.filesystem import FilesystemStorageClient
from app.core.core_storage.settings import StorageBackend, StorageSettings, get_storage_settings
from pydantic import ValidationError

# --------------------------------------------------------------------------- #
# StorageSettings
# --------------------------------------------------------------------------- #


def test_settings_accepts_explicit_values(tmp_path: Path) -> None:
    """Verify StorageSettings can be constructed with explicit values."""
    settings = StorageSettings(
        STORAGE_BACKEND=StorageBackend.FILESYSTEM,
        S3_BUCKET="my-bucket",
        FILESYSTEM_ROOT=str(tmp_path),
        S3_ADDRESSING_STYLE="path",
        S3_SECURE=False,
    )
    assert settings.STORAGE_BACKEND == StorageBackend.FILESYSTEM
    assert settings.S3_BUCKET == "my-bucket"
    assert settings.FILESYSTEM_ROOT == str(tmp_path)
    assert settings.S3_ADDRESSING_STYLE == "path"
    assert settings.S3_SECURE is False


@pytest.mark.parametrize(
    ("access_key_var", "secret_key_var"),
    [
        ("accessKey", "secretKey"),
        ("accesskey", "secretkey"),
    ],
)
def test_settings_accepts_cluster_secret_aliases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    access_key_var: str,
    secret_key_var: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("accessKey", raising=False)
    monkeypatch.delenv("secretKey", raising=False)
    monkeypatch.delenv("accesskey", raising=False)
    monkeypatch.delenv("secretkey", raising=False)

    settings = StorageSettings.model_validate(
        {
            "STORAGE_BACKEND": StorageBackend.S3,
            "S3_BUCKET": "my-bucket",
            "S3_ENDPOINT": "http://minio:9000",
            access_key_var: "key",
            secret_key_var: "secret",
        }
    )

    assert settings.S3_ACCESS_KEY_ID is not None
    assert settings.S3_SECRET_ACCESS_KEY is not None
    assert settings.S3_ACCESS_KEY_ID.get_secret_value() == "key"
    assert settings.S3_SECRET_ACCESS_KEY.get_secret_value() == "secret"


@pytest.mark.parametrize(
    ("access_key_var", "secret_key_var"),
    [
        ("S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"),
        ("accessKey", "secretKey"),
    ],
)
def test_settings_from_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    access_key_var: str,
    secret_key_var: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "my-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("S3_REGION", "eu-central-1")
    monkeypatch.setenv(access_key_var, "key")
    monkeypatch.setenv(secret_key_var, "secret")

    settings = StorageSettings()
    assert settings.STORAGE_BACKEND == StorageBackend.S3
    assert settings.S3_BUCKET == "my-bucket"
    assert settings.S3_ENDPOINT == "http://minio:9000"
    assert settings.S3_REGION == "eu-central-1"
    assert settings.S3_ACCESS_KEY_ID is not None
    assert settings.S3_SECRET_ACCESS_KEY is not None
    assert settings.S3_ACCESS_KEY_ID.get_secret_value() == "key"
    assert settings.S3_SECRET_ACCESS_KEY.get_secret_value() == "secret"


# --------------------------------------------------------------------------- #
# Factory — filesystem
# --------------------------------------------------------------------------- #


def test_factory_returns_filesystem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("FILESYSTEM_ROOT", str(tmp_path))

    # Clear caches so factory picks up new settings
    get_storage_settings.cache_clear()
    get_storage_client.cache_clear()

    try:
        client = get_storage_client()
        assert isinstance(client, FilesystemStorageClient)
    finally:
        get_storage_settings.cache_clear()
        get_storage_client.cache_clear()


# --------------------------------------------------------------------------- #
# Factory — s3
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("access_key_var", "secret_key_var"),
    [
        ("S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"),
        ("accessKey", "secretKey"),
    ],
)
def test_factory_returns_s3(
    monkeypatch: pytest.MonkeyPatch,
    access_key_var: str,
    secret_key_var: str,
) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv(access_key_var, "key")
    monkeypatch.setenv(secret_key_var, "secret")
    monkeypatch.setenv("S3_SECURE", "false")

    get_storage_settings.cache_clear()
    get_storage_client.cache_clear()

    fake_client = MagicMock()
    fake_boto3 = MagicMock()
    fake_botocore_config = MagicMock()
    fake_botocore_exceptions = MagicMock()

    fake_boto3.session.Session.return_value.client.return_value = fake_client

    class _FakeClientError(Exception):
        pass

    fake_botocore_exceptions.ClientError = _FakeClientError

    try:
        with patch.dict(
            "sys.modules",
            {
                "boto3": fake_boto3,
                "botocore": MagicMock(),
                "botocore.config": fake_botocore_config,
                "botocore.exceptions": fake_botocore_exceptions,
            },
        ):
            from app.core.core_storage.s3 import S3StorageClient

            client = get_storage_client()
            assert isinstance(client, S3StorageClient)
    finally:
        get_storage_settings.cache_clear()
        get_storage_client.cache_clear()


# --------------------------------------------------------------------------- #
# Factory — invalid backend
# --------------------------------------------------------------------------- #


def test_factory_raises_on_invalid_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "azure")

    get_storage_settings.cache_clear()
    get_storage_client.cache_clear()

    try:
        with pytest.raises(ValidationError):
            # pydantic validation will reject "azure" as not in StorageBackend
            get_storage_client()
    finally:
        get_storage_settings.cache_clear()
        get_storage_client.cache_clear()


def test_factory_raises_on_missing_s3_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "")

    fake_boto3 = MagicMock()
    fake_botocore_config = MagicMock()
    fake_botocore_exceptions = MagicMock()

    class _FakeClientError(Exception):
        pass

    fake_botocore_exceptions.ClientError = _FakeClientError

    get_storage_settings.cache_clear()
    get_storage_client.cache_clear()

    try:
        with (
            patch.dict(
                "sys.modules",
                {
                    "boto3": fake_boto3,
                    "botocore": MagicMock(),
                    "botocore.config": fake_botocore_config,
                    "botocore.exceptions": fake_botocore_exceptions,
                },
            ),
            pytest.raises(StorageConfigError, match="S3_BUCKET"),
        ):
            get_storage_client()
    finally:
        get_storage_settings.cache_clear()
        get_storage_client.cache_clear()

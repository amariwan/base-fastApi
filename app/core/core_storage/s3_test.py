"""Tests for S3StorageClient with mocked boto3."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.core.core_storage.base import FileMetadata
from app.core.core_storage.exceptions import StorageConfigError, StorageError, StorageFileNotFoundError
from app.core.core_storage.s3 import S3StorageClient
from app.core.core_storage.settings import StorageBackend, StorageSettings

# --------------------------------------------------------------------------- #
# Fake boto3 helpers (same pattern as existing docmanager tests)
# --------------------------------------------------------------------------- #


class _FakeClientError(Exception):
    """Minimal stub for botocore.exceptions.ClientError."""

    def __init__(self, code: str) -> None:
        self.response: dict[str, Any] = {"Error": {"Code": code}}
        super().__init__(f"ClientError({code})")


def _make_settings(
    bucket: str = "test-bucket",
    prefix: str = "",
) -> StorageSettings:
    return StorageSettings(
        STORAGE_BACKEND=StorageBackend.S3,
        S3_BUCKET=bucket,
        S3_ENDPOINT="http://minio:9000",
        S3_ACCESS_KEY_ID="key",
        S3_SECRET_ACCESS_KEY="secret",
        S3_ADDRESSING_STYLE="path",
        S3_PREFIX=prefix,
        S3_SECURE=False,
    )


def _make_client(
    bucket: str = "test-bucket",
    prefix: str = "",
) -> tuple[S3StorageClient, MagicMock]:
    """Build S3StorageClient with a fake boto3 client."""
    fake_client = MagicMock()
    fake_boto3 = MagicMock()
    fake_botocore_config = MagicMock()
    fake_botocore_exceptions = MagicMock()

    fake_boto3.session.Session.return_value.client.return_value = fake_client
    fake_botocore_exceptions.ClientError = _FakeClientError

    settings = _make_settings(bucket=bucket, prefix=prefix)

    with patch.dict(
        "sys.modules",
        {
            "boto3": fake_boto3,
            "botocore": MagicMock(),
            "botocore.config": fake_botocore_config,
            "botocore.exceptions": fake_botocore_exceptions,
        },
    ):
        client = S3StorageClient(settings)

    client._client_error_cls = _FakeClientError
    client._client = fake_client

    return client, fake_client


# --------------------------------------------------------------------------- #
# Init
# --------------------------------------------------------------------------- #


def test_requires_bucket() -> None:
    fake_boto3 = MagicMock()
    fake_botocore_config = MagicMock()
    fake_botocore_exceptions = MagicMock()
    fake_botocore_exceptions.ClientError = _FakeClientError

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
        S3StorageClient(_make_settings(bucket="   "))


# --------------------------------------------------------------------------- #
# upload_file
# --------------------------------------------------------------------------- #


def test_upload_returns_metadata() -> None:
    client, s3 = _make_client()
    meta = client.upload_file(
        b"hello",
        "documents/v1/doc.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    s3.put_object.assert_called_once()
    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["Key"] == "documents/v1/doc.docx"
    assert call_kwargs["Body"] == b"hello"

    assert isinstance(meta, FileMetadata)
    assert meta.path == "documents/v1/doc.docx"
    assert meta.size_bytes == 5


def test_upload_with_prefix() -> None:
    client, s3 = _make_client(prefix="templates")
    client.upload_file(b"data", "v1/doc.docx")

    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Key"] == "templates/v1/doc.docx"


def test_upload_with_metadata() -> None:
    client, s3 = _make_client()
    client.upload_file(b"data", "file.txt", metadata={"author": "test"})

    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Metadata"] == {"author": "test"}


def test_upload_raises_on_failure() -> None:
    client, s3 = _make_client()
    s3.put_object.side_effect = RuntimeError("network error")

    with pytest.raises(StorageError, match="konnte nicht nach S3 hochgeladen werden"):
        client.upload_file(b"data", "key.txt")


# --------------------------------------------------------------------------- #
# download_file
# --------------------------------------------------------------------------- #


def test_download_returns_bytes() -> None:
    client, s3 = _make_client()
    mock_body = MagicMock()
    mock_body.read.return_value = b"file content"
    s3.get_object.return_value = {"Body": mock_body}

    result = client.download_file("documents/v1/doc.docx")

    s3.get_object.assert_called_once_with(Bucket="test-bucket", Key="documents/v1/doc.docx")
    assert result == b"file content"


def test_download_raises_not_found() -> None:
    client, s3 = _make_client()
    s3.get_object.side_effect = _FakeClientError("NoSuchKey")

    with pytest.raises(StorageFileNotFoundError, match="not found"):
        client.download_file("missing.docx")


def test_download_raises_on_other_failure() -> None:
    client, s3 = _make_client()
    s3.get_object.side_effect = RuntimeError("S3 down")

    with pytest.raises(StorageError, match="konnte nicht aus S3 heruntergeladen werden"):
        client.download_file("doc.docx")


# --------------------------------------------------------------------------- #
# file_exists
# --------------------------------------------------------------------------- #


def test_exists_returns_true() -> None:
    client, s3 = _make_client()
    s3.head_object.return_value = {}
    assert client.file_exists("doc.docx") is True


def test_exists_returns_false_on_404() -> None:
    client, s3 = _make_client()
    s3.head_object.side_effect = _FakeClientError("404")
    assert client.file_exists("doc.docx") is False


def test_exists_raises_on_other_error() -> None:
    client, s3 = _make_client()
    s3.head_object.side_effect = RuntimeError("network error")

    with pytest.raises(StorageError, match="Existenz von"):
        client.file_exists("doc.docx")


# --------------------------------------------------------------------------- #
# delete_file
# --------------------------------------------------------------------------- #


def test_delete_calls_s3() -> None:
    client, s3 = _make_client()
    client.delete_file("doc.docx")
    s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="doc.docx")


def test_delete_raises_on_failure() -> None:
    client, s3 = _make_client()
    s3.delete_object.side_effect = RuntimeError("fail")

    with pytest.raises(StorageError, match="konnte nicht aus S3 gelöscht werden"):
        client.delete_file("doc.docx")


# --------------------------------------------------------------------------- #
# file_size
# --------------------------------------------------------------------------- #


def test_file_size_returns_content_length() -> None:
    client, s3 = _make_client()
    s3.head_object.return_value = {"ContentLength": 1234}
    assert client.file_size("doc.docx") == 1234


def test_file_size_raises_not_found() -> None:
    client, s3 = _make_client()
    s3.head_object.side_effect = _FakeClientError("NoSuchKey")

    with pytest.raises(StorageFileNotFoundError):
        client.file_size("doc.docx")


# --------------------------------------------------------------------------- #
# list_files
# --------------------------------------------------------------------------- #


def test_list_files_returns_sorted_keys() -> None:
    client, s3 = _make_client()

    paginator_mock = MagicMock()
    s3.get_paginator.return_value = paginator_mock
    paginator_mock.paginate.return_value = [
        {"Contents": [{"Key": "b.txt"}, {"Key": "a.txt"}]},
    ]

    result = client.list_files()
    assert result == ["a.txt", "b.txt"]


def test_list_files_with_prefix_strips_prefix() -> None:
    client, s3 = _make_client(prefix="templates")

    paginator_mock = MagicMock()
    s3.get_paginator.return_value = paginator_mock
    paginator_mock.paginate.return_value = [
        {"Contents": [{"Key": "templates/a.txt"}, {"Key": "templates/b.txt"}]},
    ]

    result = client.list_files()
    assert result == ["a.txt", "b.txt"]


def test_list_files_raises_on_failure() -> None:
    client, s3 = _make_client()

    paginator_mock = MagicMock()
    s3.get_paginator.return_value = paginator_mock
    paginator_mock.paginate.side_effect = RuntimeError("fail")

    with pytest.raises(StorageError, match="S3-Objekte konnten nicht aufgelistet werden"):
        client.list_files()


# --------------------------------------------------------------------------- #
# generate_presigned_url
# --------------------------------------------------------------------------- #


def test_presigned_url_returns_url() -> None:
    client, s3 = _make_client()
    s3.generate_presigned_url.return_value = "https://minio:9000/test-bucket/doc.docx?sig=abc"

    url = client.generate_presigned_url("doc.docx", expires_in=600)
    assert "doc.docx" in url

    s3.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "test-bucket", "Key": "doc.docx"},
        ExpiresIn=600,
    )


def test_presigned_url_raises_on_failure() -> None:
    client, s3 = _make_client()
    s3.generate_presigned_url.side_effect = RuntimeError("fail")

    with pytest.raises(StorageError, match="Presigned URL für"):
        client.generate_presigned_url("doc.docx")

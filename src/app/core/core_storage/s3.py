"""S3-compatible storage backend (AWS S3 / MinIO)."""

import logging

from app.core.core_messages import MessageKeys, msg
from app.core.core_storage.base import FileMetadata, StorageClient, normalize_storage_path
from app.core.core_storage.exceptions import StorageConfigError, StorageError, StorageFileNotFoundError
from app.core.core_storage.settings import StorageSettings

logger = logging.getLogger("app_logger")


class S3StorageClient(StorageClient):
    """Store files in an S3-compatible object store.

    A single physical bucket is used.  An optional *prefix* provides
    logical isolation within that bucket (all object keys are prefixed).
    """

    _client_error_cls: type[Exception]

    def __init__(self, settings: StorageSettings) -> None:
        bucket = settings.S3_BUCKET.strip()
        if not bucket:
            raise StorageConfigError(msg.get(MessageKeys.STORAGE_S3_BUCKET_REQUIRED))

        try:
            import boto3  # type: ignore[import-untyped]
            from botocore.config import Config  # type: ignore[import-untyped]
            from botocore.exceptions import ClientError  # type: ignore[import-untyped]
        except ImportError as exc:
            raise StorageConfigError(msg.get(MessageKeys.STORAGE_S3_BOTO3_REQUIRED)) from exc

        endpoint_url = settings.S3_ENDPOINT or None
        if endpoint_url and not settings.S3_SECURE:
            # Allow plain HTTP endpoints (common with local MinIO).
            if endpoint_url.startswith("https://"):
                endpoint_url = endpoint_url.replace("https://", "http://", 1)

        # Trim any accidental whitespace from secrets/keys coming from env files
        access_key = settings.S3_ACCESS_KEY_ID.get_secret_value().strip() if settings.S3_ACCESS_KEY_ID else None
        secret_key = settings.S3_SECRET_ACCESS_KEY.get_secret_value().strip() if settings.S3_SECRET_ACCESS_KEY else None

        session = boto3.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=settings.S3_REGION or None,
        )

        # Determine addressing style. For custom endpoints (MinIO with explicit
        # host/port) virtual-host (subdomain) addressing often breaks signing.
        addressing_style = settings.S3_ADDRESSING_STYLE or "auto"
        if endpoint_url:
            # If user explicitly set addressing style, respect it. Otherwise
            # prefer `path` style for custom endpoints to avoid SignatureDoesNotMatch.
            if addressing_style == "auto":
                addressing_style = "path"

        # Ensure modern signature version for S3-compatible servers
        config = Config(signature_version="s3v4", s3={"addressing_style": addressing_style})

        self._client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            config=config,
        )
        self._bucket = bucket
        self._prefix = settings.S3_PREFIX.strip("/")
        self._client_error_cls = ClientError

        logger.info(
            "S3StorageClient initialised — bucket '%s', prefix '%s', endpoint %s",
            self._bucket,
            self._prefix or "(none)",
            endpoint_url or "AWS",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _object_key(self, path: str) -> str:
        """Prepend the configured prefix to *path*."""
        if not self._prefix:
            return path
        return f"{self._prefix}/{path}"

    def _to_public_key(self, object_key: str) -> str:
        """Strip the configured prefix from *object_key*."""
        if not self._prefix:
            return object_key
        prefix_with_sep = f"{self._prefix}/"
        if object_key.startswith(prefix_with_sep):
            return object_key[len(prefix_with_sep) :]
        return object_key

    def _is_not_found(self, exc: Exception) -> bool:
        if not isinstance(exc, self._client_error_cls):
            return False
        response = getattr(exc, "response", None)
        if not isinstance(response, dict):
            return False
        error_obj = response.get("Error") or {}
        if not isinstance(error_obj, dict):
            return False
        code = error_obj.get("Code")
        return str(code) in {"404", "NoSuchKey", "NotFound"}

    # ------------------------------------------------------------------
    # Interface implementation
    # ------------------------------------------------------------------

    def upload_file(
        self,
        file_bytes: bytes,
        path: str,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> FileMetadata:
        normalized = normalize_storage_path(path)
        object_key = self._object_key(normalized)

        put_kwargs: dict[str, object] = {
            "Bucket": self._bucket,
            "Key": object_key,
            "Body": file_bytes,
            "ContentType": content_type,
        }
        if metadata:
            put_kwargs["Metadata"] = metadata

        try:
            self._client.put_object(**put_kwargs)
        except Exception as exc:
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_UPLOAD_FAILED, path=object_key, error=exc)) from exc

        return FileMetadata(
            path=normalized,
            size_bytes=len(file_bytes),
            content_type=content_type,
        )

    def download_file(self, path: str) -> bytes:
        normalized = normalize_storage_path(path)
        object_key = self._object_key(normalized)

        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=object_key)
            return obj["Body"].read()  # type: ignore[no-any-return]
        except Exception as exc:
            if self._is_not_found(exc):
                raise StorageFileNotFoundError(f"File not found: '{normalized}'") from exc
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_DOWNLOAD_FAILED, path=object_key, error=exc)) from exc

    def file_exists(self, path: str) -> bool:
        normalized = normalize_storage_path(path)
        object_key = self._object_key(normalized)

        try:
            self._client.head_object(Bucket=self._bucket, Key=object_key)
            return True
        except Exception as exc:
            if self._is_not_found(exc):
                return False
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_EXISTS_FAILED, path=object_key, error=exc)) from exc

    def delete_file(self, path: str) -> None:
        normalized = normalize_storage_path(path)
        object_key = self._object_key(normalized)

        try:
            self._client.delete_object(Bucket=self._bucket, Key=object_key)
        except Exception as exc:
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_DELETE_FAILED, path=object_key, error=exc)) from exc

    def file_size(self, path: str) -> int:
        normalized = normalize_storage_path(path)
        object_key = self._object_key(normalized)

        try:
            meta = self._client.head_object(Bucket=self._bucket, Key=object_key)
        except Exception as exc:
            if self._is_not_found(exc):
                raise StorageFileNotFoundError(f"File not found: '{normalized}'") from exc
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_METADATA_FAILED, path=object_key, error=exc)) from exc

        return int(meta.get("ContentLength") or 0)

    def list_files(self, prefix: str = "") -> list[str]:
        if prefix:
            normalized_prefix = normalize_storage_path(prefix)
            object_prefix = self._object_key(normalized_prefix)
        elif self._prefix:
            object_prefix = self._prefix
        else:
            object_prefix = ""

        if object_prefix and not object_prefix.endswith("/"):
            object_prefix = f"{object_prefix}/"

        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self._bucket, Prefix=object_prefix):
                for item in page.get("Contents", []):
                    object_key = str(item.get("Key") or "")
                    if not object_key:
                        continue
                    keys.append(self._to_public_key(object_key))
        except Exception as exc:
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_LIST_FAILED, error=exc)) from exc

        return sorted(keys)

    def generate_presigned_url(self, path: str, *, expires_in: int = 3600) -> str:
        normalized = normalize_storage_path(path)
        object_key = self._object_key(normalized)

        try:
            url: str = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            raise StorageError(msg.get(MessageKeys.STORAGE_S3_PRESIGNED_FAILED, path=object_key, error=exc)) from exc

        return url

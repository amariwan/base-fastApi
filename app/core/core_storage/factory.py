"""Singleton factory for the configured storage backend."""

import functools

from app.core.core_messages import MessageKeys, msg
from app.core.core_storage.base import StorageClient
from app.core.core_storage.exceptions import StorageConfigError
from app.core.core_storage.settings import StorageBackend, get_storage_settings


@functools.cache
def get_storage_client() -> StorageClient:
    """Return a singleton ``StorageClient`` for the configured backend.

    The concrete implementation is selected via ``STORAGE_BACKEND``.
    Lazy-imports backend modules so that e.g. *boto3* is only required
    when the S3 backend is actually in use.
    """
    settings = get_storage_settings()

    if settings.STORAGE_BACKEND == StorageBackend.S3:
        from app.core.core_storage.s3 import S3StorageClient

        return S3StorageClient(settings)

    if settings.STORAGE_BACKEND == StorageBackend.FILESYSTEM:
        from app.core.core_storage.filesystem import FilesystemStorageClient

        return FilesystemStorageClient(settings)

    raise StorageConfigError(msg.get(MessageKeys.STORAGE_UNSUPPORTED_BACKEND, backend=settings.STORAGE_BACKEND))

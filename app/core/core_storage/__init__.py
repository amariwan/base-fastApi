"""Reusable S3-compatible storage module.

Quick start::

    from app.core.core_storage import StorageDep

    @router.post("/upload")
    def upload(storage: StorageDep, ...):
        meta = storage.upload_file(data, "some/path.docx", content_type="application/octet-stream")
"""

from app.core.core_storage.base import FileMetadata, StorageClient, normalize_storage_path
from app.core.core_storage.dependency import StorageDep
from app.core.core_storage.exceptions import StorageConfigError, StorageError, StorageFileNotFoundError
from app.core.core_storage.factory import get_storage_client
from app.core.core_storage.settings import StorageBackend, StorageSettings, get_storage_settings

__all__ = [
    "FileMetadata",
    "StorageBackend",
    "StorageClient",
    "StorageConfigError",
    "StorageDep",
    "StorageError",
    "StorageFileNotFoundError",
    "StorageSettings",
    "get_storage_client",
    "get_storage_settings",
    "normalize_storage_path",
]

"""Filesystem storage backend for local development and testing."""

import logging
import os
from pathlib import Path

from app.core.core_messages import MessageKeys, msg
from app.core.core_storage.base import FileMetadata, StorageClient, normalize_storage_path
from app.core.core_storage.exceptions import StorageConfigError, StorageError, StorageFileNotFoundError
from app.core.core_storage.settings import StorageSettings

logger = logging.getLogger("app_logger")


class FilesystemStorageClient(StorageClient):
    """Store files on the local filesystem.

    Layout::

        {root}/{path}

    Where *root* comes from ``StorageSettings.FILESYSTEM_ROOT``.
    """

    def __init__(self, settings: StorageSettings) -> None:
        root = settings.FILESYSTEM_ROOT.strip()
        if not root:
            raise StorageConfigError(msg.get(MessageKeys.STORAGE_FILESYSTEM_ROOT_EMPTY))

        self._root = Path(root)

        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as err:
            raise StorageConfigError(
                msg.get(MessageKeys.STORAGE_FILESYSTEM_CREATE_DIR_FAILED, root=root, error=err)
            ) from err

        if not os.access(self._root, os.W_OK):
            raise StorageConfigError(msg.get(MessageKeys.STORAGE_FILESYSTEM_NOT_WRITABLE, root=root))

        logger.info("FilesystemStorageClient initialised — root '%s'", self._root)

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
        file_path = self._root / normalized
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_path.write_bytes(file_bytes)
        except (OSError, PermissionError) as err:
            raise StorageError(msg.get(MessageKeys.STORAGE_FILESYSTEM_WRITE_FAILED, path=file_path, error=err)) from err

        return FileMetadata(
            path=normalized,
            size_bytes=len(file_bytes),
            content_type=content_type,
        )

    def download_file(self, path: str) -> bytes:
        normalized = normalize_storage_path(path)
        file_path = self._root / normalized

        if not file_path.exists():
            raise StorageFileNotFoundError(f"File not found: '{normalized}'")

        try:
            return file_path.read_bytes()
        except (OSError, PermissionError) as err:
            raise StorageError(msg.get(MessageKeys.STORAGE_FILESYSTEM_READ_FAILED, path=file_path, error=err)) from err

    def file_exists(self, path: str) -> bool:
        normalized = normalize_storage_path(path)
        file_path = self._root / normalized
        return file_path.exists() and file_path.is_file()

    def delete_file(self, path: str) -> None:
        normalized = normalize_storage_path(path)
        file_path = self._root / normalized

        if not file_path.exists():
            return  # idempotent

        try:
            file_path.unlink()
        except (OSError, PermissionError) as err:
            raise StorageError(
                msg.get(MessageKeys.STORAGE_FILESYSTEM_DELETE_FAILED, path=file_path, error=err)
            ) from err

    def file_size(self, path: str) -> int:
        normalized = normalize_storage_path(path)
        file_path = self._root / normalized

        if not file_path.exists():
            raise StorageFileNotFoundError(f"File not found: '{normalized}'")

        return file_path.stat().st_size

    def list_files(self, prefix: str = "") -> list[str]:
        if prefix:
            normalized = normalize_storage_path(prefix)
            search_root = self._root / normalized
        else:
            search_root = self._root

        if not search_root.exists():
            return []

        keys: list[str] = []
        for file_path in search_root.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(self._root)
                keys.append(str(relative))

        return sorted(keys)

    def generate_presigned_url(self, path: str, *, expires_in: int = 3600) -> str:
        raise StorageError(msg.get(MessageKeys.STORAGE_FILESYSTEM_PRESIGNED_UNSUPPORTED))

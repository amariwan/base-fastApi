"""Storage abstraction: interface, metadata, and path helpers."""

import dataclasses
from abc import ABC, abstractmethod
from pathlib import PurePosixPath

from app.core.core_messages import MessageKeys, msg
from app.core.core_storage.exceptions import StorageError


@dataclasses.dataclass(frozen=True, slots=True)
class FileMetadata:
    """Metadata returned after a successful upload."""

    path: str
    size_bytes: int
    content_type: str


def normalize_storage_path(path: str) -> str:
    """Normalize and validate a storage path.

    Returns a cleaned POSIX path string.  Rejects empty, absolute, and
    directory-traversal paths.

    Raises
    ------
    StorageError
        If *path* is empty, absolute, or contains ``..`` segments.
    """
    stripped = path.strip()
    if not stripped:
        raise StorageError(msg.get(MessageKeys.STORAGE_PATH_EMPTY))

    normalized = str(PurePosixPath(stripped))
    if not normalized or normalized in {".", "/"}:
        raise StorageError(msg.get(MessageKeys.STORAGE_PATH_EMPTY))

    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        raise StorageError(msg.get(MessageKeys.STORAGE_INVALID_PATH))

    return normalized


class StorageClient(ABC):
    """Backend-agnostic byte-storage interface.

    Implementations receive bucket / prefix / root configuration at
    construction time.  Callers only pass relative *path* keys.
    """

    @abstractmethod
    def upload_file(
        self,
        file_bytes: bytes,
        path: str,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> FileMetadata:
        """Store *file_bytes* at *path* and return metadata."""

    @abstractmethod
    def download_file(self, path: str) -> bytes:
        """Load bytes by *path*."""

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Return whether a file at *path* exists."""

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete the file at *path*.  No-op if already absent."""

    @abstractmethod
    def file_size(self, path: str) -> int:
        """Return file size in bytes."""

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """List file paths under *prefix*."""

    @abstractmethod
    def generate_presigned_url(self, path: str, *, expires_in: int = 3600) -> str:
        """Return a time-limited download URL for *path*.

        Filesystem implementations raise ``StorageError``.
        """

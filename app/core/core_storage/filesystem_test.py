"""Tests for FilesystemStorageClient."""

from pathlib import Path

import pytest
from app.core.core_storage.exceptions import StorageConfigError, StorageError, StorageFileNotFoundError
from app.core.core_storage.filesystem import FilesystemStorageClient
from app.core.core_storage.settings import StorageBackend, StorageSettings


def _make_settings(root: str) -> StorageSettings:
    """Create StorageSettings pointing at a filesystem root."""
    return StorageSettings(
        STORAGE_BACKEND=StorageBackend.FILESYSTEM,
        FILESYSTEM_ROOT=root,
    )


# --------------------------------------------------------------------------- #
# Init
# --------------------------------------------------------------------------- #


def test_init_creates_root_directory(tmp_path: Path) -> None:
    root = tmp_path / "new_dir"
    assert not root.exists()
    _client = FilesystemStorageClient(_make_settings(str(root)))
    assert root.is_dir()


def test_init_raises_on_empty_root() -> None:
    with pytest.raises(StorageConfigError, match="FILESYSTEM_ROOT darf nicht leer sein"):
        FilesystemStorageClient(_make_settings(""))


# --------------------------------------------------------------------------- #
# upload + download round-trip
# --------------------------------------------------------------------------- #


def test_upload_and_download(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    data = b"word document bytes"

    meta = client.upload_file(data, "templates/v1/doc.docx", content_type="application/octet-stream")
    assert meta.size_bytes == len(data)
    assert meta.path == "templates/v1/doc.docx"
    assert meta.content_type == "application/octet-stream"

    result = client.download_file("templates/v1/doc.docx")
    assert result == data


# --------------------------------------------------------------------------- #
# file_exists
# --------------------------------------------------------------------------- #


def test_file_exists_false(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    assert client.file_exists("missing.txt") is False


def test_file_exists_true(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    client.upload_file(b"x", "key.txt")
    assert client.file_exists("key.txt") is True


# --------------------------------------------------------------------------- #
# download missing
# --------------------------------------------------------------------------- #


def test_download_raises_when_missing(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    with pytest.raises(StorageFileNotFoundError, match="not found"):
        client.download_file("missing.docx")


# --------------------------------------------------------------------------- #
# delete
# --------------------------------------------------------------------------- #


def test_delete_removes_file(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    client.upload_file(b"data", "del.txt")
    assert client.file_exists("del.txt") is True

    client.delete_file("del.txt")
    assert client.file_exists("del.txt") is False


def test_delete_idempotent_on_missing(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    client.delete_file("nonexistent.txt")  # should not raise


# --------------------------------------------------------------------------- #
# file_size
# --------------------------------------------------------------------------- #


def test_file_size(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    client.upload_file(b"12345", "sized.txt")
    assert client.file_size("sized.txt") == 5


def test_file_size_raises_when_missing(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    with pytest.raises(StorageFileNotFoundError):
        client.file_size("missing.txt")


# --------------------------------------------------------------------------- #
# list_files
# --------------------------------------------------------------------------- #


def test_list_files(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    client.upload_file(b"a", "dir/a.txt")
    client.upload_file(b"b", "dir/b.txt")
    client.upload_file(b"c", "other/c.txt")

    all_files = client.list_files()
    assert all_files == ["dir/a.txt", "dir/b.txt", "other/c.txt"]

    dir_files = client.list_files("dir")
    assert dir_files == ["dir/a.txt", "dir/b.txt"]


def test_list_files_empty_prefix(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    assert client.list_files() == []


# --------------------------------------------------------------------------- #
# generate_presigned_url
# --------------------------------------------------------------------------- #


def test_presigned_url_raises(tmp_path: Path) -> None:
    client = FilesystemStorageClient(_make_settings(str(tmp_path)))
    with pytest.raises(StorageError, match="Presigned URLs werden vom Filesystem-Storage nicht unterstützt"):
        client.generate_presigned_url("file.txt")

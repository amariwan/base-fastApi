"""Tests for normalize_storage_path and FileMetadata."""

import pytest
from app.core.core_storage.base import FileMetadata, normalize_storage_path
from app.core.core_storage.exceptions import StorageError

# --------------------------------------------------------------------------- #
# normalize_storage_path
# --------------------------------------------------------------------------- #


def test_simple_key() -> None:
    assert normalize_storage_path("hello.txt") == "hello.txt"


def test_nested_key() -> None:
    assert normalize_storage_path("a/b/c.txt") == "a/b/c.txt"


def test_strips_whitespace() -> None:
    assert normalize_storage_path("  a/b.txt  ") == "a/b.txt"


def test_normalizes_redundant_slashes() -> None:
    assert normalize_storage_path("a//b///c.txt") == "a/b/c.txt"


def test_empty_string_raises() -> None:
    with pytest.raises(StorageError, match="Storage-Pfad darf nicht leer sein"):
        normalize_storage_path("")


def test_whitespace_only_raises() -> None:
    with pytest.raises(StorageError, match="Storage-Pfad darf nicht leer sein"):
        normalize_storage_path("   ")


def test_dot_only_raises() -> None:
    with pytest.raises(StorageError, match="Storage-Pfad darf nicht leer sein"):
        normalize_storage_path(".")


def test_absolute_path_raises() -> None:
    with pytest.raises(StorageError, match="Ungültiger Storage-Pfad"):
        normalize_storage_path("/etc/passwd")


def test_traversal_raises() -> None:
    with pytest.raises(StorageError, match="Ungültiger Storage-Pfad"):
        normalize_storage_path("a/../../etc/passwd")


def test_single_dotdot_raises() -> None:
    with pytest.raises(StorageError, match="Ungültiger Storage-Pfad"):
        normalize_storage_path("..")


# --------------------------------------------------------------------------- #
# FileMetadata
# --------------------------------------------------------------------------- #


def test_file_metadata_is_frozen() -> None:
    meta = FileMetadata(path="a/b.txt", size_bytes=42, content_type="text/plain")
    assert meta.path == "a/b.txt"
    assert meta.size_bytes == 42
    assert meta.content_type == "text/plain"

    with pytest.raises(AttributeError):
        meta.path = "changed"  # type: ignore[misc]

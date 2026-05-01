"""Tests for the error code registry."""

import pytest

from app.shared.errors.registry import (
    ErrorEntry,
    get_error,
    get_error_or_default,
)


class TestGetError:
    def test_known_code_returns_entry(self) -> None:
        entry = get_error("SERVER_ERROR")
        assert entry is not None
        assert entry.code == "SERVER_ERROR"
        assert entry.http_status == 500
        assert entry.type == "error"

    def test_unknown_code_returns_none(self) -> None:
        assert get_error("DOES_NOT_EXIST") is None

    def test_validation_codes_are_warnings(self) -> None:
        entry = get_error("VALIDATION_FAILED")
        assert entry is not None
        assert entry.type == "warning"

    def test_auth_codes_have_correct_status(self) -> None:
        entry = get_error("AUTH_REQUIRED")
        assert entry is not None
        assert entry.http_status == 401


class TestGetErrorOrDefault:
    def test_known_code(self) -> None:
        entry = get_error_or_default("TEMPLATE_NOT_FOUND")
        assert entry.code == "TEMPLATE_NOT_FOUND"
        assert entry.http_status == 404

    def test_unknown_code_returns_default(self) -> None:
        entry = get_error_or_default("DOES_NOT_EXIST")
        assert entry.code == "UNKNOWN_ERROR"
        assert entry.http_status == 500

    def test_all_entries_have_german_message(self) -> None:
        """Every registered entry must have a non-empty message."""
        from app.shared.errors.registry import _REGISTRY

        for code, entry in _REGISTRY.items():
            assert entry.message, f"Entry {code} has empty message"
            assert entry.code == code


class TestErrorEntry:
    def test_frozen(self) -> None:
        entry = ErrorEntry(code="TEST", message="Test")
        with pytest.raises(AttributeError):
            entry.code = "CHANGED"  # type: ignore[misc]

    def test_defaults(self) -> None:
        entry = ErrorEntry(code="TEST", message="msg")
        assert entry.type == "error"
        assert entry.http_status == 400
        assert entry.loesung is None

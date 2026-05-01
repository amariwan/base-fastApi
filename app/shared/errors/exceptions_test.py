"""Tests for UnifiedApiError exception."""

from app.shared.errors.exceptions import UnifiedApiError


class TestUnifiedApiError:
    def test_resolves_from_registry(self) -> None:
        exc = UnifiedApiError("SERVER_ERROR")
        assert exc.code == "SERVER_ERROR"
        assert exc.http_status == 500
        assert exc.error_type == "error"
        assert exc.message  # non-empty from registry

    def test_overrides(self) -> None:
        exc = UnifiedApiError(
            "SERVER_ERROR",
            message="Custom",
            type="warning",
            http_status=503,
        )
        assert exc.message == "Custom"
        assert exc.error_type == "warning"
        assert exc.http_status == 503

    def test_details_and_dev(self) -> None:
        details = [{"field": "x", "reason": "bad"}]
        dev = {"loesung": "fix x"}
        exc = UnifiedApiError("VALIDATION_FAILED", details=details, dev=dev)
        assert exc.details == details
        assert exc.dev == dev

    def test_unknown_code_uses_defaults(self) -> None:
        exc = UnifiedApiError("NONEXISTENT")
        assert exc.http_status == 500  # from default entry
        assert exc.message  # non-empty from default

    def test_is_exception(self) -> None:
        exc = UnifiedApiError("SERVER_ERROR")
        assert isinstance(exc, Exception)
        assert str(exc) == exc.message

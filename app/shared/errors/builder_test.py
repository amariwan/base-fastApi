"""Tests for the unified error response builder."""

from app.shared.errors.builder import build_error_response


class TestBuildErrorResponse:
    def test_basic_envelope_structure(self) -> None:
        result = build_error_response("SERVER_ERROR")
        assert "error" in result

        error = result["error"]
        assert error["code"] == "SERVER_ERROR"
        assert error["type"] == "error"
        assert "traceId" in error
        assert "timestamp" in error
        assert error["message"]  # non-empty

    def test_message_from_registry(self) -> None:
        result = build_error_response("TEMPLATE_NOT_FOUND")
        assert "nicht gefunden" in result["error"]["message"]

    def test_message_override(self) -> None:
        result = build_error_response("SERVER_ERROR", message="Custom msg")
        assert result["error"]["message"] == "Custom msg"

    def test_type_override(self) -> None:
        result = build_error_response("SERVER_ERROR", type="warning")
        assert result["error"]["type"] == "warning"

    def test_details_included_when_present(self) -> None:
        details = [{"field": "name", "reason": "required"}]
        result = build_error_response("VALIDATION_FAILED", details=details)
        assert result["error"]["details"] == details

    def test_details_omitted_when_none(self) -> None:
        result = build_error_response("SERVER_ERROR")
        assert "details" not in result["error"]

    def test_dev_included_when_present(self) -> None:
        result = build_error_response("SERVER_ERROR", dev={"loesung": "Fix it"})
        assert result["error"]["dev"] == {"loesung": "Fix it"}

    def test_dev_omitted_when_none(self) -> None:
        result = build_error_response("SERVER_ERROR")
        assert "dev" not in result["error"]

    def test_unknown_code_uses_default(self) -> None:
        result = build_error_response("NONEXISTENT_CODE")
        assert result["error"]["code"] == "NONEXISTENT_CODE"
        assert result["error"]["message"]  # default message from fallback

    def test_trace_id_is_hex(self) -> None:
        result = build_error_response("SERVER_ERROR")
        trace_id = result["error"]["traceId"]
        assert len(trace_id) == 32
        int(trace_id, 16)  # should not raise

    def test_timestamp_iso_format(self) -> None:
        result = build_error_response("SERVER_ERROR")
        ts = result["error"]["timestamp"]
        assert ts.endswith("Z")

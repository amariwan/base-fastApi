from __future__ import annotations

import logging

import pytest

from shared.logging.AppLogger import OperationLogger, setup_logging
from shared.logging.LogTypeAdapter import LogTypeAdapter
from shared.logging.MyLogger import MyJSONFormatter
from shared.logging.request_context import get_request_id, reset_request_id, set_request_id


def test_request_context_roundtrip() -> None:
    token = set_request_id("abc")
    assert get_request_id() == "abc"
    reset_request_id(token)
    assert get_request_id() is None


def test_log_type_adapter_injects_request_id(caplog: pytest.LogCaptureFixture) -> None:
    setup_logging(force=True)
    caplog.set_level(logging.INFO)
    adapter = LogTypeAdapter(logging.getLogger("test"), {"log_type": "TEST"})
    token = set_request_id("rid-1")
    adapter.info("message", extra={"foo": "bar"})
    reset_request_id(token)
    record = caplog.records[-1]
    assert record.log_type == "TEST"
    assert record.request_id == "rid-1"


def test_operation_logger_records_duration(caplog: pytest.LogCaptureFixture) -> None:
    setup_logging(force=True)
    caplog.set_level(logging.INFO)
    adapter = LogTypeAdapter(logging.getLogger("ops"), {"log_type": "OPS"})
    with OperationLogger(adapter, "op", entity="news"):
        pass
    assert any("completed op" in message for message in caplog.messages)


def test_json_formatter_outputs_fields() -> None:
    formatter = MyJSONFormatter(fmt_keys={"logger": "name"})
    record = logging.LogRecord("logger", logging.INFO, __file__, 10, "msg", (), None)
    record.log_type = "TEST"
    output = formatter.format(record)
    assert '"log_type": "TEST"' in output

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.sql import column

from core.error_handling import AppError
from shared.logging.app_logger import journey_logger
from shared.logging.JourneyLogger import JourneyTracker
from shared.utils.string_utils import to_camel
from utils.datetime_utils import get_current_iso_timestamp, greater, less, now_utc
from utils.env_helpers import first_env, read_env_bool, read_env_csv
from utils.idempotency import find_by_idempotency
from utils.model_utils import to_read_model_fallback
from utils.sort.resolve_sort import add_sortable_column, resolve_sort
from utils.time.time_utils import _is_published_at_reached, _is_visible_until_reached


def test_env_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLAG", "true")
    monkeypatch.setenv("CSV_VALUES", "a;b,c")
    assert read_env_bool("FLAG") is True
    assert read_env_csv("CSV_VALUES") == ["a", "b", "c"]
    monkeypatch.delenv("MISSING", raising=False)
    assert first_env("MISSING", default="fallback") == "fallback"


def test_datetime_helpers() -> None:
    now = now_utc()
    assert isinstance(now, datetime)
    assert less(now, now + timedelta(seconds=1))
    assert greater(now + timedelta(seconds=1), now)
    assert get_current_iso_timestamp().endswith("+00:00")


@pytest.mark.asyncio
async def test_find_by_idempotency() -> None:
    class FakeModel:
        idempotency_key = column("idempotency_key")

    class FakeResult:
        def __init__(self, obj):
            self._obj = obj

        def scalars(self):
            return self

        def first(self):
            return self._obj

    class FakeSession:
        async def execute(self, stmt):
            return FakeResult(SimpleNamespace(id=1))

    result = await find_by_idempotency(FakeSession(), FakeModel, "key")
    assert result.id == 1


def test_model_utils_fallback() -> None:
    class Obj:
        id = 1
        title = "hello"
        body_html = "<p>text</p>"
        author = "user"
        tags = ["a"]
        status = "draft"
        visible_until = None
        published_at = None
        priority = 1
        sticky_until = None
        created_at = None
        updated_at = None
        created_by = None
        updated_by = None
        meta = {}
        source = None
        slug = "slug"
        idempotency_key = "idem"

    dto = to_read_model_fallback(Obj())
    assert dto.title == "hello"
    assert dto.idempotencyKey == "idem"


def test_sort_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    add_sortable_column("createdAt", column("created_at"))
    expr, raw = resolve_sort("-createdAt")
    assert raw == "-createdAt"
    with pytest.raises(AppError):
        resolve_sort("unknown")


def test_time_utils() -> None:
    now = datetime.now(UTC)
    assert _is_published_at_reached(now - timedelta(seconds=1), reference_time=now)
    assert not _is_visible_until_reached(now + timedelta(seconds=1), reference_time=now)


def test_journey_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_log(message: str, extra: dict) -> None:
        calls.append((message, extra))

    monkeypatch.setattr(journey_logger, "info", fake_log)
    tracker = JourneyTracker("req")
    tracker.add_step("start", {"foo": "bar"})
    tracker.set_failure()
    tracker.log_journey()
    assert calls and calls[0][1]["request_id"] == "req"


def test_to_camel() -> None:
    assert to_camel("created_at") == "createdAt"

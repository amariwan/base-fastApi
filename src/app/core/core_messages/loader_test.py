from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.core.core_messages.loader import (
    ImproperlyConfiguredError,
    MessageService,
    reset_request_message_language,
    set_request_message_language,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_message_service_merges_multiple_sources(tmp_path: Path) -> None:
    core_file = tmp_path / "core" / "messages.de.json"
    service_file = tmp_path / "service" / "messages.de.json"
    _write_json(core_file, {"auth": {"invalid_token": "Ungültiges Token"}})
    _write_json(service_file, {"batch": {"not_found": "Batch nicht gefunden"}})

    service = MessageService(language="de", message_files=[core_file, service_file])

    assert service.get("auth.invalid_token") == "Ungültiges Token"
    assert service.get("batch.not_found") == "Batch nicht gefunden"
    assert service.get(service.keys.AUTH_INVALID_TOKEN) == "Ungültiges Token"


def test_message_service_returns_key_and_logs_warning_for_missing_key(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    core_file = tmp_path / "core" / "messages.de.json"
    _write_json(core_file, {"auth": {"invalid_token": "Ungültiges Token"}})

    service = MessageService(language="de", message_files=[core_file])

    with caplog.at_level("WARNING", logger="app_logger"):
        result = service.get("missing.key")

    assert result == "missing.key"
    assert "Missing message key: missing.key" in caplog.text


def test_message_service_raises_for_duplicate_key(tmp_path: Path) -> None:
    core_file = tmp_path / "core" / "messages.de.json"
    service_file = tmp_path / "service" / "messages.de.json"
    _write_json(core_file, {"auth": {"invalid_token": "Ungültiges Token"}})
    _write_json(service_file, {"auth": {"invalid_token": "Anderes Token"}})

    with pytest.raises(ImproperlyConfiguredError, match="Duplicate message key 'auth.invalid_token'"):
        MessageService(language="de", message_files=[core_file, service_file])


def test_message_service_interpolates_values(tmp_path: Path) -> None:
    core_file = tmp_path / "core" / "messages.de.json"
    _write_json(core_file, {"user": {"welcome": "Willkommen {name}"}})

    service = MessageService(language="de", message_files=[core_file])

    assert service.get("user.welcome", name="Tasio") == "Willkommen Tasio"


def test_message_service_defaults_to_de_and_supports_explicit_language(tmp_path: Path) -> None:
    de_core = tmp_path / "core" / "messages.de.json"
    en_core = tmp_path / "core" / "messages.en.json"
    _write_json(de_core, {"user": {"welcome": "Willkommen {name}"}})
    _write_json(en_core, {"user": {"welcome": "Welcome {name}"}})

    service = MessageService(language="de")
    service._messages_by_language = {
        "de": service._load_messages([de_core]),
        "en": service._load_messages([en_core]),
    }

    assert service.get("user.welcome", name="Tasio") == "Willkommen Tasio"
    assert service.get("user.welcome", lang="en", name="Tasio") == "Welcome Tasio"


def test_message_service_uses_request_language_context(tmp_path: Path) -> None:
    de_core = tmp_path / "core" / "messages.de.json"
    en_core = tmp_path / "core" / "messages.en.json"
    _write_json(de_core, {"errors": {"unexpected": "Unerwartet"}})
    _write_json(en_core, {"errors": {"unexpected": "Unexpected"}})

    service = MessageService(language="de")
    service._messages_by_language = {
        "de": service._load_messages([de_core]),
        "en": service._load_messages([en_core]),
    }

    token = set_request_message_language("en-US")
    try:
        assert service.get("errors.unexpected") == "Unexpected"
    finally:
        reset_request_message_language(token)

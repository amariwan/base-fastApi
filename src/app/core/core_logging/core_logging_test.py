import importlib
from types import SimpleNamespace
from typing import cast

import pytest


def test_importing_logging_module_does_not_configure_process_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("app.core.core_logging.AppLogger")
    configure_calls: list[object] = []

    monkeypatch.setattr(module.logging.config, "dictConfig", configure_calls.append)
    importlib.reload(module)

    assert configure_calls == []


def test_setup_logging_configures_root_and_application_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("app.core.core_logging.AppLogger")
    captured_config: list[dict[str, object]] = []

    monkeypatch.setattr(module, "get_app_settings", lambda: SimpleNamespace(LOG_LEVEL=SimpleNamespace(value="DEBUG")))
    monkeypatch.setattr(module.logging.config, "dictConfig", captured_config.append)

    module.setup_logging()

    config = captured_config[0]
    root_config = cast(dict[str, object], config["root"])
    app_logger_config = cast(dict[str, object], cast(dict[str, object], config["loggers"])["app_logger"])
    assert root_config["level"] == "DEBUG"
    assert app_logger_config["handlers"] == ["system_stdout"]
    assert app_logger_config["propagate"] is False

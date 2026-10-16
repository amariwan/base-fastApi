from __future__ import annotations

import json
import logging
import logging.config
import pathlib
from logging import getLogger

from app.config import get_app_settings
from app.core.core_logging.LogTypeAdapter import LogTypeAdapter

fastapi_logger = logging.getLogger("app_logger")

system_logger = LogTypeAdapter(getLogger("system"), {"log_type": "SYSTEM"})
single_logger = LogTypeAdapter(getLogger("single"), {"log_type": "SINGLE"})
journey_logger = LogTypeAdapter(getLogger("journey"), {"log_type": "JOURNEY"})


def setup_logging() -> None:
    """Configure application logging from the checked-in JSON config.

    Configuration is intentionally explicit: importing a logger module must
    not mutate the process-wide logging configuration. The application factory
    invokes this function during app construction.
    """
    app_settings = get_app_settings()
    fastapi_logger.debug("Setting up logging with level: %s", app_settings.LOG_LEVEL.value)
    config_file = pathlib.Path(__file__).parent / "logger_config_files/stdout_config.json"
    with config_file.open() as f_in:
        logger_config = json.load(f_in)

    # Update root level. ``root`` is a top-level logging configuration key,
    # not an entry in the named ``loggers`` mapping.
    if "root" in logger_config:
        logger_config["root"]["level"] = app_settings.LOG_LEVEL.value

    # Update any explicitly defined loggers
    for logger_name in ["app_logger", "system", "single", "journey"]:
        if logger_name in logger_config.get("loggers", {}):
            logger_config["loggers"][logger_name]["level"] = app_settings.LOG_LEVEL.value

    logging.config.dictConfig(logger_config)

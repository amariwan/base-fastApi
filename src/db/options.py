from __future__ import annotations

from types import SimpleNamespace
from typing import Final, cast

from config import get_app_settings, get_db_settings

try:
    _db = get_db_settings()
except SystemExit:
    _db = cast(
        SimpleNamespace,
        SimpleNamespace(
            DB_POOL_SIZE=5,
            DB_MAX_OVERFLOW=5,
            DB_POOL_RECYCLE_SECS=300,
            DB_POOL_TIMEOUT=30.0,
            DB_CONNECT_TIMEOUT=10.0,
            DB_COMMAND_TIMEOUT=60.0,
            DB_STARTUP_MAX_RETRIES=10,
            DB_STARTUP_BASE_DELAY=0.5,
            DB_STARTUP_MAX_DELAY=10.0,
            DB_STARTUP_OVERALL_TIMEOUT=60.0,
            DB_SSL=False,
            DB_SSL_NO_VERIFY=False,
            PG_STATEMENT_TIMEOUT_MS=60000,
            PG_IDLE_IN_XACT_TIMEOUT_MS=300000,
            DB_SKIP_STARTUP_WAIT=None,
        ),
    )

_app = get_app_settings()

POOL_SIZE: Final[int] = int(_db.DB_POOL_SIZE)
MAX_OVERFLOW: Final[int] = int(_db.DB_MAX_OVERFLOW)
POOL_RECYCLE_SECS: Final[int] = int(_db.DB_POOL_RECYCLE_SECS)
POOL_TIMEOUT: Final[float] = float(getattr(_db, "DB_POOL_TIMEOUT", 30.0))

CONNECT_TIMEOUT: Final[float] = float(_db.DB_CONNECT_TIMEOUT)
COMMAND_TIMEOUT: Final[float] = float(_db.DB_COMMAND_TIMEOUT)

STARTUP_MAX_RETRIES: Final[int] = int(_db.DB_STARTUP_MAX_RETRIES)
STARTUP_BASE_DELAY: Final[float] = float(_db.DB_STARTUP_BASE_DELAY)
STARTUP_MAX_DELAY: Final[float] = float(_db.DB_STARTUP_MAX_DELAY)
STARTUP_OVERALL_TIMEOUT: Final[float] = float(_db.DB_STARTUP_OVERALL_TIMEOUT)

DB_REQUIRE_SSL: Final[bool] = bool(_db.DB_SSL)
DB_SSL_NO_VERIFY: Final[bool] = bool(_db.DB_SSL_NO_VERIFY)

APP_NAME: Final[str] = str(getattr(_app, "APP_NAME", "app"))
APP_ENV: Final[str] = str(getattr(_app, "APP_ENV", "dev")).lower()

PG_STATEMENT_TIMEOUT_MS: Final[int] = int(_db.PG_STATEMENT_TIMEOUT_MS)
PG_IDLE_IN_XACT_TIMEOUT_MS: Final[int] = int(_db.PG_IDLE_IN_XACT_TIMEOUT_MS)

_raw_skip_wait = getattr(_db, "DB_SKIP_STARTUP_WAIT", None)
SKIP_STARTUP_WAIT: Final[bool] = (
    bool(_raw_skip_wait)
    if _raw_skip_wait is not None
    else APP_ENV in {"dev", "local", "test"}
)

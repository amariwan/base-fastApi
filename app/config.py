from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# All allowed values for ENV LOG_LEVEL
class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Overall Settings
class AppSettings(BaseSettings):
    API_PREFIX: str = "/api"
    LOG_LEVEL: LogLevel = LogLevel.INFO
    TEST_MODE: bool = False
    PYTHONPATH: str = "app"
    PROFILING_ENABLED: bool = False
    RUN_MIGRATIONS_ON_STARTUP: bool = True
    MIGRATIONS_ON_STARTUP_MODE: Literal["auto", "always", "never"] = "auto"

    AUTH_MODE: Literal["jwks", "hs"] = "jwks"
    AUTH_ROLE_PREFIX: str = "GRPS_"
    ROLES_ACTIVE: bool = True
    ROLES_READ: str = "read"
    ROLES_WRITE: str = "write"
    ROLES_DELETE: str = "delete"
    ROLES_ADMIN: str = "admin"
    ROLES_HIERARCHY: str = "admin>delete>write>read"
    AUTH_MANDANT_CLAIM: str = "organisation"
    AUTH_JWKS_URL: str | None = None

    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:3300,http://127.0.0.1:3300,http://localhost:3000,http://127.0.0.1:3000"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    AUTH_ISSUER: str | None = None
    AUTH_AUDIENCE: str | None = None
    AUTH_ALGORITHMS: str = "RS256"
    AUTH_VALIDATE_SIGNATURE: bool = False
    AUTH_HS_SECRET: str | None = None
    AUTH_VERIFY_SIGNATURE: bool = True
    AUTH_VERIFY_EXP: bool = True
    AUTH_VERIFY_ISS: bool = True
    AUTH_VERIFY_AUD: bool = True
    AUTH_CLOCK_SKEW_SECS: int = 60

    MAX_REQUEST_SIZE_BYTES: int = 10 * 1024 * 1024
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024

    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Startup health check timeouts and migration control
    DB_PROBE_TIMEOUT_SECONDS: int = 5
    S3_PROBE_TIMEOUT_SECONDS: int = 5
    MIGRATION_TIMEOUT_SECONDS: int = 300
    STARTUP_FAIL_ON_ERROR: bool = False
    MIGRATIONS_ADVISORY_LOCK_USE: bool = True
    MIGRATIONS_ADVISORY_LOCK_KEY: int = 123456789

    SECURITY_HEADERS_ENABLED: bool = True
    SECURITY_HEADERS_HSTS_ENABLED: bool = False
    SECURITY_HEADERS_HSTS_MAX_AGE: int = 31536000
    SECURITY_HEADERS_CSP_ENABLED: bool = False
    SECURITY_HEADERS_CSP_DIRECTIVES: str = ""
    SECURITY_HEADERS_X_FRAME_OPTIONS: str | None = None

    HTTP_LOGGING_ENABLED: bool = True
    HTTP_REQUEST_LOGGING_ENABLED: bool = False
    HTTP_RESPONSE_LOGGING_ENABLED: bool = False
    HTTP_FAULT_LOGGING_ENABLED: bool = True

    MSYS2_ENV_CONV_EXCL: str | None = None

    model_config = SettingsConfigDict(env_file=(".env", ".env.dev"), case_sensitive=False, extra="ignore")

    def csv(self, raw: str) -> list[str]:
        raw = raw.strip()
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def cors_allowed_origins(self) -> list[str]:
        return self.csv(self.CORS_ALLOWED_ORIGINS)

    @property
    def cors_allow_methods(self) -> list[str]:
        methods = self.CORS_ALLOW_METHODS.strip()
        if methods == "*":
            return ["*"]
        return [m.strip() for m in methods.split(",") if m.strip()]

    @property
    def cors_allow_headers(self) -> list[str]:
        headers = self.CORS_ALLOW_HEADERS.strip()
        if headers == "*":
            return ["*"]
        return [h.strip() for h in headers.split(",") if h.strip()]

    @property
    def auth_algorithms(self) -> list[str]:
        return self.csv(self.AUTH_ALGORITHMS)


# DB Specific Settings
class DbSettings(BaseSettings):
    # When DB_ENABLED is False, DB fields may be omitted to run without a DB
    # Defaulting to False makes the application easier to run in environments
    # that don't provide a database (local/dev/test). Enable via env var when needed.
    DB_ENABLED: bool = False
    DB_PORT: int | None = None
    DB_USERNAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_DATABASE: str | None = None
    DB_IP: str = "localhost"
    DB_ENGINE_ECHO: bool = False  # sets echo=False

    # Connection pool — tune per deployment size
    DB_POOL_SIZE: int = 10  # persistent connections per process
    DB_MAX_OVERFLOW: int = 20  # extra connections allowed during traffic spikes
    DB_POOL_RECYCLE: int = 3600  # seconds before recycling idle connections
    DB_POOL_PRE_PING: bool = True  # test connections before use (prevents stale-connection errors)
    DB_AUTO_CREATE_TABLES: bool = True

    model_config = SettingsConfigDict(env_file=(".env", ".env.dev"), case_sensitive=False, extra="ignore")


def _crash_invalid_settings(scope: str, error: Exception) -> None:
    raise SystemExit(f"CRITICAL ERROR: Invalid {scope} environment variables!\n{error}") from error


@lru_cache(maxsize=1)
def get_db_settings() -> DbSettings:
    """
    Return a singleton instance of DbSettings.
    Initializes on first access. Exits if environment variables are invalid unless DB_ENABLED is False.
    """
    try:
        db_settings = DbSettings()
        # Validate required DB values only when DB is enabled
        if db_settings.DB_ENABLED:
            missing = [
                name
                for name in ("DB_PORT", "DB_USERNAME", "DB_PASSWORD", "DB_DATABASE")
                if getattr(db_settings, name) in (None, "")
            ]
            if missing:
                raise SystemExit("CRITICAL ERROR: DB is enabled but missing variables: " + ", ".join(missing))
    except Exception as e:
        _crash_invalid_settings("DB", e)
    return db_settings


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """
    Return a singleton instance of AppSettings.
    Initializes on first access. Exits if environment variables are invalid.
    """
    try:
        app_settings = AppSettings()
        if not app_settings.API_PREFIX.startswith("/"):
            app_settings.API_PREFIX = f"/{app_settings.API_PREFIX}"
    except Exception as e:
        _crash_invalid_settings("App", e)
    return app_settings


@lru_cache(maxsize=1)
def get_api_roles() -> dict[str, str]:
    settings = get_app_settings()
    return {
        "read": settings.ROLES_READ,
        "write": settings.ROLES_WRITE,
        "delete": settings.ROLES_DELETE,
        "admin": settings.ROLES_ADMIN,
    }

from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Enum for the supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class BaseConfig:
    """Base class for all configurations with centralized `model_config`."""

    model_config = SettingsConfigDict(
        env_file=(".env.dev", ".env"),
        case_sensitive=False,
        extra="ignore",
    )


class AuthSettings(BaseSettings, BaseConfig):
    """Authentication and Authorization settings"""

    AUTH_METADATA_URL: str = Field(default="", description="OIDC metadata URL")
    AUTH_CLIENT_ID: str = Field(default="", description="OAuth2 Client ID")
    AUTH_AUDIENCE: str = Field(default="", description="JWT Audience")
    AUTH_CLIENT_SECRET: str = Field(default="", description="OAuth2 Client Secret")
    AUTH_OIDC_URL: str = Field(default="", description="OIDC provider base URL")
    AUTH_OIDC_LOGIN_PATH: str = Field(
        default="/protocol/openid-connect/token",
        description="OIDC provider login endpoint path",
    )
    AUTH_ROLE_PREFIX: str = Field(
        default="GRPS_ExampleApp_", description="Prefix for role extraction from JWT"
    )
    AUTH_ORGANISATION_PREFIX: str = Field(
        default="GRPS_ExampleApp_Org", description="Prefix for organisation extraction"
    )
    AUTH_ORGANISATION_CLAIM_TYPE: str = Field(
        default="organisation", description="JWT claim name for organisation"
    )
    AUTH_MANDANT_CLAIM: str = Field(
        default="mandant_id", description="JWT claim name for mandant or group id"
    )

    AUTH_VERIFY_SIGNATURE: bool = Field(
        default=True, description="Verify JWT signature"
    )
    AUTH_VERIFY_EXPIRY: bool = Field(default=True, description="Verify JWT expiry")


class RoleSettings(BaseSettings, BaseConfig):
    """Role-based access control settings"""

    ROLES_ACTIVE: bool = Field(default=True, description="Enable role-based access")
    ROLES_READ: str = Field(
        default="", description="Comma-separated list of read roles"
    )
    ROLES_WRITE: str = Field(
        default="", description="Comma-separated list of write roles"
    )
    ROLES_ADMIN: str = Field(
        default="", description="Comma-separated list of admin roles"
    )
    ROLES_DELETE: str = Field(
        default="", description="Comma-separated list of delete roles"
    )

    @property
    def read_roles(self) -> list[str]:
        return [r.strip() for r in self.ROLES_READ.split(",") if r.strip()]

    @property
    def write_roles(self) -> list[str]:
        return [r.strip() for r in self.ROLES_WRITE.split(",") if r.strip()]

    @property
    def admin_roles(self) -> list[str]:
        return [r.strip() for r in self.ROLES_ADMIN.split(",") if r.strip()]

    @property
    def delete_roles(self) -> list[str]:
        return [r.strip() for r in self.ROLES_DELETE.split(",") if r.strip()]


class HttpLoggingSettings(BaseSettings, BaseConfig):
    """HTTP request/response logging configuration"""

    HTTP_LOGGING_ENABLED: bool = Field(default=True, description="Enable HTTP logging")
    HTTP_REQUEST_LOGGING_ENABLED: bool = Field(
        default=False, description="Enable request body logging"
    )
    HTTP_RESPONSE_LOGGING_ENABLED: bool = Field(
        default=False, description="Enable response body logging"
    )
    HTTP_FAULT_LOGGING_ENABLED: bool = Field(
        default=True, description="Enable fault/error logging"
    )


class SecuritySettings(BaseSettings, BaseConfig):
    """Security-related configuration"""

    CORS_ENABLED: bool = Field(default=True, description="Enable CORS middleware")
    CORS_ALLOWED_ORIGINS: str = Field(
        default="", description="Comma-separated list of allowed origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials")
    CORS_ALLOWED_METHODS: str = Field(default="*", description="Allowed HTTP methods")
    CORS_ALLOWED_HEADERS: str = Field(default="*", description="Allowed headers")

    RATE_LIMIT_ENABLED: bool = Field(default=False, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(
        default=100, description="Max requests per time window"
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Time window in seconds"
    )

    MAX_REQUEST_SIZE_BYTES: int = Field(
        default=10_485_760, description="Max request size (10MB)"
    )
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=52_428_800, description="Max upload size (50MB)"
    )

    SECURITY_HEADERS_ENABLED: bool = Field(
        default=True, description="Enable security headers"
    )
    HSTS_ENABLED: bool = Field(default=True, description="Enable HSTS header")
    HSTS_MAX_AGE: int = Field(default=31536000, description="HSTS max age in seconds")
    CSP_ENABLED: bool = Field(
        default=False, description="Enable Content Security Policy"
    )
    CSP_DIRECTIVES: str = Field(
        default="default-src 'self'", description="CSP directives"
    )

    REQUIRE_API_KEY: bool = Field(
        default=False, description="Require API key for requests"
    )
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")


class AppSettings(BaseSettings, BaseConfig):
    """App general settings"""

    LOG_LEVEL: LogLevel = LogLevel.INFO
    TEST_MODE: bool = False
    APP_NAME: str = "service"
    APP_ENV: str = "local"
    API_PREFIX: str = "/api"
    API_VERSION: str = Field(default="v1", description="API version")
    ALLOWED_HOSTS: str = Field(default="*", description="Comma-separated allowed hosts")
    ENABLE_DOCS: bool = Field(default=True, description="Enable OpenAPI documentation")
    ENABLE_METRICS: bool = Field(default=False, description="Enable metrics endpoint")
    ENABLE_HEALTH_CHECK: bool = Field(
        default=True, description="Enable health check endpoint"
    )

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]


class DbSettings(BaseSettings, BaseConfig):
    """Database settings"""

    DB_PORT: int
    DB_HOST: str
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_DATABASE: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE_SECS: int = 300
    DB_POOL_TIMEOUT: float = 30.0
    DB_CONNECT_TIMEOUT: float = 10.0
    DB_COMMAND_TIMEOUT: float = 60.0
    DB_STARTUP_MAX_RETRIES: int = 10
    DB_STARTUP_BASE_DELAY: float = 0.5
    DB_STARTUP_MAX_DELAY: float = 10.0
    DB_STARTUP_OVERALL_TIMEOUT: float = 60.0
    DB_SSL: bool = False
    DB_SSL_NO_VERIFY: bool = False
    PG_STATEMENT_TIMEOUT_MS: int = 60000
    PG_IDLE_IN_XACT_TIMEOUT_MS: int = 300000
    DATABASE_URL: str | None = None


# Singleton pattern for config initialization
_instances: dict[str, BaseSettings | None] = {
    "app": None,
    "db": None,
    "auth": None,
    "roles": None,
    "http_logging": None,
    "security": None,
}


def get_db_settings() -> DbSettings:
    """Singleton for DB settings"""
    if _instances["db"] is None:
        _instances["db"] = DbSettings()
    return _instances["db"]


def get_app_settings() -> AppSettings:
    """Singleton for App settings"""
    if _instances["app"] is None:
        _instances["app"] = AppSettings()
    return _instances["app"]


def get_auth_settings() -> AuthSettings:
    """Singleton for Auth settings"""
    if _instances["auth"] is None:
        _instances["auth"] = AuthSettings()
    return _instances["auth"]


def get_role_settings() -> RoleSettings:
    """Singleton for Role settings"""
    if _instances["roles"] is None:
        _instances["roles"] = RoleSettings()
    return _instances["roles"]


def get_http_logging_settings() -> HttpLoggingSettings:
    """Singleton for HTTP logging settings"""
    if _instances["http_logging"] is None:
        _instances["http_logging"] = HttpLoggingSettings()
    return _instances["http_logging"]


def get_security_settings() -> SecuritySettings:
    """Singleton for Security settings"""
    if _instances["security"] is None:
        _instances["security"] = SecuritySettings()
    return _instances["security"]


def reset_settings_cache(*names: str) -> None:
    """Reset cached settings instances (useful in tests)."""
    if not names:
        names = tuple(_instances.keys())
    for name in names:
        if name in _instances:
            _instances[name] = None

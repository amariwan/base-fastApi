"""Validated environment configuration for optional AI capabilities."""

from collections.abc import Iterable
from functools import lru_cache

from app.core.core_ai.contracts import Capability
from app.core.core_ai.security.policies import validate_http_endpoint
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item.strip().lower() for item in value.replace(";", ",").split(",") if item.strip())
    if isinstance(value, Iterable):
        return tuple(str(item).strip().lower() for item in value if str(item).strip())
    raise TypeError("value must be a comma-separated string or iterable")


class AISettings(BaseSettings):
    """Core AI settings. No provider is initialized while ``ENABLED`` is false."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.dev"),
        env_prefix="AI_",
        case_sensitive=False,
        extra="ignore",
    )

    ENABLED: bool = False
    DEFAULT_PROVIDER: str = "ollama"
    DEFAULT_MODEL: str | None = None
    DEFAULT_MODEL_CAPABILITIES: tuple[Capability, ...] = ()
    MODELS: dict[str, list[str]] = Field(default_factory=dict)

    ALLOWED_PROVIDERS: tuple[str, ...] = ("ollama",)
    ALLOWED_ENDPOINT_HOSTS: tuple[str, ...] = ()
    CLOUD_DATA_ALLOWED: bool = False
    CLOUD_FALLBACK_ENABLED: bool = False

    REQUEST_TIMEOUT_SECONDS: float = Field(default=60, gt=0, le=600)
    MAX_CONCURRENT_REQUESTS: int = Field(default=4, ge=1, le=128)
    MAX_INPUT_CHARS: int = Field(default=200_000, ge=1)
    MAX_OUTPUT_TOKENS: int = Field(default=4096, ge=1)
    MAX_TOOL_CALLS: int = Field(default=8, ge=0, le=100)
    MAX_MODEL_REQUESTS: int = Field(default=3, ge=1, le=20)

    STORE_PROMPTS: bool = False
    STORE_RESPONSES: bool = False
    TRACING_ENABLED: bool = False

    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OPENAI_COMPATIBLE_BASE_URL: str | None = None
    OPENAI_COMPATIBLE_API_KEY: SecretStr | None = None
    OPENAI_COMPATIBLE_IS_CLOUD: bool = False
    OPENAI_API_KEY: SecretStr | None = None
    ANTHROPIC_API_KEY: SecretStr | None = None
    GOOGLE_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None

    @field_validator("ALLOWED_PROVIDERS", "ALLOWED_ENDPOINT_HOSTS", mode="before")
    @classmethod
    def _parse_csv_fields(cls, value: object) -> tuple[str, ...]:
        return _split_csv(value)

    @field_validator("DEFAULT_MODEL_CAPABILITIES", mode="before")
    @classmethod
    def _parse_capabilities(cls, value: object) -> tuple[str, ...] | object:
        if isinstance(value, str):
            return _split_csv(value)
        return value

    @model_validator(mode="after")
    def _validate_enabled_provider(self) -> "AISettings":
        self.DEFAULT_PROVIDER = self.DEFAULT_PROVIDER.strip().lower()
        if self.ENABLED and not (self.DEFAULT_MODEL and self.DEFAULT_MODEL.strip()):
            raise ValueError("AI_DEFAULT_MODEL is required when AI_ENABLED=true")
        if self.ENABLED and self.DEFAULT_PROVIDER not in self.ALLOWED_PROVIDERS:
            raise ValueError("AI_DEFAULT_PROVIDER must be included in AI_ALLOWED_PROVIDERS")

        cloud_providers = {"openai", "anthropic", "google", "openrouter"}
        if self.ENABLED and self.DEFAULT_PROVIDER in cloud_providers and not self.CLOUD_DATA_ALLOWED:
            raise ValueError("AI_CLOUD_DATA_ALLOWED must be true for a cloud default provider")
        if (
            self.ENABLED
            and self.DEFAULT_PROVIDER == "openai_compatible"
            and self.OPENAI_COMPATIBLE_IS_CLOUD
            and not self.CLOUD_DATA_ALLOWED
        ):
            raise ValueError("AI_CLOUD_DATA_ALLOWED must be true for a cloud OpenAI-compatible default provider")

        provider_credentials = {
            "openai": self.OPENAI_API_KEY,
            "anthropic": self.ANTHROPIC_API_KEY,
            "google": self.GOOGLE_API_KEY,
            "openrouter": self.OPENROUTER_API_KEY,
        }
        if self.ENABLED and self.DEFAULT_PROVIDER in provider_credentials:
            credential = provider_credentials[self.DEFAULT_PROVIDER]
            if credential is None or not credential.get_secret_value().strip():
                raise ValueError(f"AI_{self.DEFAULT_PROVIDER.upper()}_API_KEY is required for the default provider")
        if self.ENABLED and self.DEFAULT_PROVIDER == "openai_compatible":
            compatible_key = self.OPENAI_COMPATIBLE_API_KEY
            if self.OPENAI_COMPATIBLE_BASE_URL is None or compatible_key is None:
                raise ValueError(
                    "AI_OPENAI_COMPATIBLE_BASE_URL and AI_OPENAI_COMPATIBLE_API_KEY are required for the default provider"
                )

        self._validate_endpoint("OLLAMA_BASE_URL", self.OLLAMA_BASE_URL)
        if self.OPENAI_COMPATIBLE_BASE_URL:
            self._validate_endpoint("OPENAI_COMPATIBLE_BASE_URL", self.OPENAI_COMPATIBLE_BASE_URL)
        return self

    def _validate_endpoint(self, field_name: str, raw_url: str) -> None:
        validate_http_endpoint(
            raw_url,
            field_name=field_name,
            allowed_hosts=frozenset(self.ALLOWED_ENDPOINT_HOSTS),
        )


@lru_cache(maxsize=1)
def get_ai_settings() -> AISettings:
    return AISettings()


def reload_ai_settings() -> AISettings:
    get_ai_settings.cache_clear()
    return get_ai_settings()

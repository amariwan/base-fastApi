"""Cache backend settings."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheBackend(StrEnum):
    MEMORY = "memory"
    REDIS = "redis"


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.dev"), case_sensitive=False, extra="ignore")

    CACHE_BACKEND: CacheBackend = CacheBackend.MEMORY
    CACHE_DEFAULT_TTL_SECONDS: int = Field(default=300, ge=1)
    CACHE_MAX_ENTRIES: int = Field(default=1024, ge=1)
    CACHE_KEY_PREFIX: str = "app"
    CACHE_REDIS_URL: str | None = None

    @model_validator(mode="after")
    def validate_redis(self) -> CacheSettings:
        if self.CACHE_BACKEND is CacheBackend.REDIS and not self.CACHE_REDIS_URL:
            raise ValueError("CACHE_REDIS_URL is required for the Redis cache backend")
        return self


@lru_cache(maxsize=1)
def get_cache_settings() -> CacheSettings:
    return CacheSettings()


__all__ = ["CacheBackend", "CacheSettings", "get_cache_settings"]

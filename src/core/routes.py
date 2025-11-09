from __future__ import annotations

"""API router registration helpers."""

import os
from typing import Final

from fastapi import APIRouter, FastAPI

from core.constants import (
    API_PREFIX_ENV,
    API_VERSION_ENV,
    DEFAULT_API_PREFIX,
    DEFAULT_API_VERSION,
)


def _build_api_root() -> str:
    prefix = (os.getenv(API_PREFIX_ENV) or DEFAULT_API_PREFIX).strip("/")
    version = (os.getenv(API_VERSION_ENV) or DEFAULT_API_VERSION).strip("/")
    root = f"/{prefix}"
    return f"{root}/{version}" if version else root


API_ROOT: Final[str] = _build_api_root()
TAGS_HEALTH: Final[tuple[str, ...]] = ("health",)


def build_api_router() -> APIRouter:
    """Create the top-level API router with all sub-routers attached."""
    api = APIRouter(prefix=API_ROOT)
    from core.healthcheck.routes import router as health_router

    api.include_router(health_router, tags=TAGS_HEALTH)
    return api


def register_routers(app: FastAPI) -> None:
    """Register routers exactly once for the FastAPI application."""
    if getattr(app.state, "_routers_registered", False):
        return
    app.include_router(build_api_router())
    app.state._routers_registered = True

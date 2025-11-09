from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from typing import Final, Protocol

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .error_handling import register_exception_handlers
from .lifespan import lifespan
from .middleware import register_middleware
from .openapi import simplify_operation_ids
from .routes import register_routers


class AppConfigurator(Protocol):
    def middleware(self, app: FastAPI) -> None: ...
    def exceptions(self, app: FastAPI) -> None: ...
    def routers(self, app: FastAPI) -> None: ...
    def openapi(self, app: FastAPI) -> None: ...


class _DefaultConfigurator:
    def middleware(self, app: FastAPI) -> None:
        register_middleware(app)

    def exceptions(self, app: FastAPI) -> None:
        register_exception_handlers(app)

    def routers(self, app: FastAPI) -> None:
        register_routers(app)

    def openapi(self, app: FastAPI) -> None:
        simplify_operation_ids(app)


def _pkg_version(pkg_name: str) -> str:
    try:
        return pkg_version(pkg_name)
    except PackageNotFoundError:
        return os.getenv("APP_VERSION", "0.0.0+local")


APP_TITLE: Final[str] = os.getenv("APP_TITLE", "service")
APP_VERSION: Final[str] = _pkg_version(APP_TITLE)


def create_app(*, configurator: AppConfigurator | None = None) -> FastAPI:
    """Instantiate the FastAPI application with the default configurator."""
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    cfg = configurator or _DefaultConfigurator()
    cfg.middleware(app)
    cfg.exceptions(app)
    cfg.routers(app)
    cfg.openapi(app)
    return app

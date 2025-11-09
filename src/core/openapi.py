from __future__ import annotations

"""OpenAPI customization helpers."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute


def simplify_operation_ids(app: FastAPI) -> None:
    """Set `operationId` to the route name for deterministic client generation."""
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


def add_bearer_security(app: FastAPI) -> None:
    """Attach a reusable HTTP Bearer security scheme to the OpenAPI document."""

    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        comps = schema.setdefault("components", {})
        security_schemes = comps.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


__all__ = ["simplify_operation_ids", "add_bearer_security"]


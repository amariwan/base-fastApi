from __future__ import annotations

from http import HTTPStatus

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.error_handling.handlers.database_handlers import (
    handle_integrity_error,
    handle_sqlalchemy_error,
)
from core.error_handling.handlers.domain_handlers import (
    handle_domain_conflict,
    handle_domain_not_found,
    handle_domain_validation,
)
from core.error_handling.handlers.http_handlers import (
    handle_http_exception,
    handle_request_validation_error,
)
from core.error_handling.handlers.system_handlers import handle_app_error, handle_unhandled
from core.error_handling.payload import build_problem, json_error
from core.error_handling.types import AppError
from core.errors import ConflictError, NotFoundError, ValidationError
from shared.logging.request_context import set_request_id


def make_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/resource",
        "headers": [],
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


def test_build_problem_and_json_error() -> None:
    problem = build_problem(status=HTTPStatus.BAD_REQUEST, title="Bad", errors={"field": ["error"]}, trace_id="abc")
    assert problem["status"] == 400
    response = json_error(
        status=HTTPStatus.BAD_REQUEST,
        kind="validation_error",
        message="Bad",
        details=[{"loc": ["body", "name"], "msg": "invalid"}],
        request_id="abc",
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_http_handlers() -> None:
    request = make_request()
    exc = HTTPException(status_code=401, detail="nope")
    response = await handle_http_exception(request, exc)
    assert response.status_code == 401

    validation_exc = RequestValidationError([{"loc": ("body", "field"), "msg": "bad"}])
    validation_response = await handle_request_validation_error(request, validation_exc)
    assert validation_response.status_code == 422


@pytest.mark.asyncio
async def test_domain_and_system_handlers() -> None:
    request = make_request()
    set_request_id("req-1")
    response = await handle_domain_validation(request, ValidationError("bad data"))
    assert response.status_code == 400
    response = await handle_domain_conflict(request, ConflictError("conflict"))
    assert response.status_code == 409
    response = await handle_domain_not_found(request, NotFoundError("missing"))
    assert response.status_code == 404
    response = await handle_app_error(request, AppError(status_code=418, message="teapot", code="app_error"))
    assert response.status_code == 418
    response = await handle_unhandled(request, RuntimeError("boom"))
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_database_handlers() -> None:
    request = make_request()
    response = await handle_integrity_error(
        request, IntegrityError("stmt", {"id": 1}, RuntimeError("db"))
    )
    assert response.status_code == 409
    response = await handle_sqlalchemy_error(request, SQLAlchemyError())
    assert response.status_code == 500

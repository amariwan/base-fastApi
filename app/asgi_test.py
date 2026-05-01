"""Smoke tests for the ASGI entry-point module."""

from fastapi import FastAPI


def test_asgi_app_is_importable() -> None:
    """The asgi module must expose the FastAPI app object."""
    from app.asgi import app  # noqa: PLC0415

    assert isinstance(app, FastAPI)


def test_asgi_module_all_contains_app() -> None:
    """__all__ must list 'app' so ASGI servers like uvicorn can locate it."""
    import app.asgi as asgi_module  # noqa: PLC0415

    assert "app" in asgi_module.__all__

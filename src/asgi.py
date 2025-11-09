from core import create_app

# Create the FastAPI app here (ASGI entrypoint). This avoids creating the
# app during core package import and prevents circular import problems.
app = create_app()

__all__ = ["app"]

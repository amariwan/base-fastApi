from __future__ import annotations

from .factory import create_app

# Do NOT create the application instance at import time here. Creating the app
# triggers router registration which may import application modules and cause
# circular import issues. Call create_app() explicitly in the ASGI entrypoint.

__all__ = ["create_app"]

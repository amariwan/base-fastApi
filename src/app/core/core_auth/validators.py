from __future__ import annotations

"""JWT validation helpers."""

from app.shared.types import JSONValue

from .service import get_jwt_service

Claims = dict[str, JSONValue]


def validate_jwt(token: str) -> Claims:
    """Validate and decode a JWT using the configured mode.

    This function delegates to JWTAuthService which handles:
    - Full signature validation when AUTH_VALIDATE_SIGNATURE=true
    - Claims-only parsing when AUTH_VALIDATE_SIGNATURE=false

    Args:
        token: The JWT token string

    Returns:
        Decoded claims dictionary

    Raises:
        HTTPException: On validation errors
    """
    service = get_jwt_service()
    decoded = service.decode_token(token)
    return decoded["payload"]


__all__ = ["validate_jwt"]

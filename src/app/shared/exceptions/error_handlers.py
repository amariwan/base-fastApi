"""Utility functions for converting shared exceptions to HTTP responses."""

from fastapi import HTTPException

from .api_errors import ApiError


def as_http_exception(exc: ApiError) -> HTTPException:
    """Convert ApiError to FastAPI HTTPException.

    Args:
        exc: ApiError instance

    Returns:
        HTTPException with status code and detail
    """
    return HTTPException(
        status_code=exc.http_status,
        detail=exc.to_dict(),
    )


def http_error(
    code: str,
    message: str,
    loesung: str,
    status_code: int = 400,
) -> HTTPException:
    """Create HTTPException directly with error detail.

    Args:
        code: Machine-readable error code
        message: German-language message
        loesung: German-language solution
        status_code: HTTP status (default 400)

    Returns:
        HTTPException ready to raise
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "detail": {
                "code": code,
                "message": message,
                "loesung": loesung,
            }
        },
    )

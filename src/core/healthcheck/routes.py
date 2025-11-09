from __future__ import annotations

"""Health and diagnostics routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from config import get_app_settings
from core.auth import UserClaims, get_current_user, get_optional_user
from shared.logging.AppLogger import system_logger as syslog

from .schemas import HealthResponse, WhoAmIResponse
from .security import is_admin
from .services import build_safe_health_config

router = APIRouter(prefix="", tags=["system"])


def _can_view_config(user: UserClaims | None) -> bool:
    test_mode = bool(getattr(get_app_settings(), "TEST_MODE", False))
    return test_mode or is_admin(getattr(user, "roles", None))


@router.get("/health", response_model=HealthResponse)
async def healthcheck(
    with_config: bool = Query(False, alias="config", description="Return config snapshot"),
    user: Annotated[UserClaims | None, Depends(get_optional_user)] = None,
) -> HealthResponse:
    """Return readiness/liveness information."""
    if not with_config:
        return HealthResponse()

    if not _can_view_config(user):
        roles = list(getattr(user, "roles", []) or [])
        syslog.warning("health_config_denied", extra={"roles": roles})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    cfg = build_safe_health_config()
    syslog.debug(
        "health_with_config",
        extra={"config_keys": sorted(cfg.model_dump(by_alias=True).keys())},
    )
    return HealthResponse(config=cfg)


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(user: Annotated[UserClaims, Depends(get_current_user)]) -> WhoAmIResponse:
    """Return the normalized user claims."""
    payload = WhoAmIResponse(
        sub=user.sub,
        name=user.name,
        email=user.email,
        preferred_username=user.preferred_username,
        organization=user.organization,
        roles=list(user.roles),
    )
    syslog.debug("whoami", extra={"roles_count": len(payload.roles)})
    return payload

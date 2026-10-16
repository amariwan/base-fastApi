import logging

from fastapi import APIRouter

from app.core.core_api.schemas import WhoAmIResponse
from app.core.core_auth import CurrentUser

logger = logging.getLogger("app_logger")

router = APIRouter(tags=["auth"])
whoami_router = router


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(user: CurrentUser) -> WhoAmIResponse:
    """Return the normalized user claims."""
    payload = WhoAmIResponse(
        sub=user.sub,
        name=user.name,
        email=user.email,
        preferred_username=user.preferred_username,
        organisation=user.organisation,
        roles=list(user.roles),
    )
    logger.debug("whoami", extra={"roles_count": len(payload.roles)})
    return payload

"""FastAPI dependency aliases for internal AI-enabled adapters."""

from typing import Annotated

from app.core.core_ai.bootstrap import get_ai_client
from app.core.core_ai.inference import AIInferenceClient
from fastapi import Depends

AIClientDep = Annotated[AIInferenceClient, Depends(get_ai_client)]

__all__ = ["AIClientDep"]

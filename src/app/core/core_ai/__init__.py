"""Optional, reusable AI and agent infrastructure for business adapters."""

from app.core.core_ai.bootstrap import get_ai_client
from app.core.core_ai.config import AISettings, get_ai_settings
from app.core.core_ai.contracts import AIRequest, AIResult, Capability
from app.core.core_ai.inference import AIInferenceClient

__all__ = [
    "AIInferenceClient",
    "AIRequest",
    "AIResult",
    "AISettings",
    "Capability",
    "get_ai_client",
    "get_ai_settings",
]

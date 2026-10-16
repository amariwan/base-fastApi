"""Stable framework-light contracts exposed by Core AI."""

from app.core.core_ai.contracts.capabilities import (
    Capability,
    CapabilitySupport,
    PrivacyRequirement,
    ProviderLocation,
)
from app.core.core_ai.contracts.events import StreamEvent, StreamEventKind
from app.core.core_ai.contracts.exceptions import (
    AIConfigurationError,
    AIDisabledError,
    AIError,
    AIOutputValidationError,
    AIProviderError,
    AIRequestLimitError,
    AIRequestTimeoutError,
    ModelNotFoundError,
    ToolApprovalRequiredError,
    ToolPermissionDeniedError,
    WorkflowExecutionError,
)
from app.core.core_ai.contracts.models import (
    AIRequest,
    AIResult,
    ExecutionLimits,
    GenerationParameters,
    ModelDescriptor,
    ProviderDescriptor,
    Usage,
)

__all__ = [
    "AIConfigurationError",
    "AIDisabledError",
    "AIError",
    "AIOutputValidationError",
    "AIProviderError",
    "AIRequest",
    "AIRequestLimitError",
    "AIRequestTimeoutError",
    "AIResult",
    "Capability",
    "CapabilitySupport",
    "ExecutionLimits",
    "GenerationParameters",
    "ModelDescriptor",
    "ModelNotFoundError",
    "PrivacyRequirement",
    "ProviderDescriptor",
    "ProviderLocation",
    "StreamEvent",
    "StreamEventKind",
    "ToolApprovalRequiredError",
    "ToolPermissionDeniedError",
    "Usage",
    "WorkflowExecutionError",
]

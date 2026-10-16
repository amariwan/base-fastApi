"""Stable, secret-safe exceptions exposed by the Core AI platform."""


class AIError(Exception):
    """Base class for Core AI failures."""


class AIDisabledError(AIError):
    """Raised when AI functionality is requested while disabled."""


class AIConfigurationError(AIError):
    """Raised for invalid runtime registration or configuration."""


class AIProviderError(AIError):
    """Raised when a provider fails without exposing provider details."""


class AIRequestTimeoutError(AIProviderError):
    """Raised when an inference request exceeds its configured deadline."""


class AIRequestLimitError(AIError):
    """Raised before execution when a configured request limit is exceeded."""


class AIOutputValidationError(AIProviderError):
    """Raised when a provider cannot produce the requested typed output."""


class ModelNotFoundError(AIError):
    """Raised when routing cannot find a compatible model."""


class ToolPermissionDeniedError(AIError):
    """Raised before execution when a caller lacks a tool permission."""


class ToolApprovalRequiredError(AIError):
    """Raised before execution when trusted application approval is missing."""


class WorkflowExecutionError(AIError):
    """Raised when a workflow runner fails without exposing private details."""

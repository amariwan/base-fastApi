"""Capability and data-location vocabulary used across Core AI."""

from enum import StrEnum


class Capability(StrEnum):
    TEXT_GENERATION = "text_generation"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    AUDIO = "audio"


class CapabilitySupport(StrEnum):
    UNKNOWN = "unknown"
    CONFIGURED = "configured"
    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"

    @property
    def is_supported(self) -> bool:
        return self in {CapabilitySupport.CONFIGURED, CapabilitySupport.VERIFIED}


class ProviderLocation(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


class PrivacyRequirement(StrEnum):
    LOCAL_ONLY = "local_only"
    CLOUD_ALLOWED = "cloud_allowed"

"""Process-level limits enforced by the inference client."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AIClientLimits:
    timeout_seconds: float = 60
    max_concurrency: int = 4
    max_input_chars: int = 200_000
    max_output_tokens: int = 4096
    max_tool_calls: int = 8
    max_model_requests: int = 3
    cloud_data_allowed: bool = False
    cloud_fallback_enabled: bool = False

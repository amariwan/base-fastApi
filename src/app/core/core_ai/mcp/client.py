"""Lazy PydanticAI MCP client construction."""

from dataclasses import dataclass

from pydantic import SecretStr
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset, FilteredToolset


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    server_id: str
    url: str
    allowed_tools: frozenset[str]
    required_permissions: frozenset[str] = frozenset()
    bearer_token: SecretStr | None = None
    connect_timeout_seconds: float = 10
    read_timeout_seconds: float = 60


def build_mcp_toolset(config: MCPServerConfig) -> AbstractToolset[object]:
    auth = config.bearer_token.get_secret_value() if config.bearer_token else None
    toolset = MCPToolset(
        config.url,
        id=config.server_id,
        include_instructions=False,
        init_timeout=config.connect_timeout_seconds,
        read_timeout=config.read_timeout_seconds,
        auth=auth,
        sampling_model=None,
        elicitation_handler=None,
    )
    allowed = config.allowed_tools
    return FilteredToolset(toolset, lambda _ctx, definition: definition.name in allowed)

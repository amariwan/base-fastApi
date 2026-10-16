"""Secure, lazy MCP client toolset registration."""

from app.core.core_ai.contracts import AIConfigurationError, ToolPermissionDeniedError
from app.core.core_ai.mcp.client import MCPServerConfig, build_mcp_toolset
from app.core.core_ai.mcp.security import validate_mcp_url
from pydantic_ai.toolsets import AbstractToolset


class MCPServerRegistry:
    def __init__(self, *, allowed_endpoint_hosts: frozenset[str] = frozenset()) -> None:
        self._allowed_endpoint_hosts = frozenset(host.lower() for host in allowed_endpoint_hosts)
        self._servers: dict[str, MCPServerConfig] = {}

    def register(self, config: MCPServerConfig) -> None:
        if config.server_id in self._servers:
            raise AIConfigurationError(f"MCP server '{config.server_id}' is already registered")
        if not config.allowed_tools:
            raise AIConfigurationError("MCP servers require an explicit non-empty tool allowlist")
        validate_mcp_url(config.url, allowed_endpoint_hosts=self._allowed_endpoint_hosts)
        self._servers[config.server_id] = config

    def resolve(self, server_id: str, *, granted_permissions: frozenset[str]) -> AbstractToolset[object]:
        try:
            config = self._servers[server_id]
        except KeyError as exc:
            raise AIConfigurationError(f"MCP server '{server_id}' is not registered") from exc
        missing = config.required_permissions - granted_permissions
        if missing:
            raise ToolPermissionDeniedError(
                f"MCP server '{server_id}' requires permissions: {', '.join(sorted(missing))}"
            )
        return build_mcp_toolset(config)

    def resolve_many(
        self, server_ids: frozenset[str], *, granted_permissions: frozenset[str]
    ) -> tuple[AbstractToolset[object], ...]:
        return tuple(
            self.resolve(server_id, granted_permissions=granted_permissions) for server_id in sorted(server_ids)
        )

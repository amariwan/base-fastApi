"""Network policy for MCP endpoints."""

import ipaddress
from urllib.parse import urlparse

from app.core.core_ai.contracts import AIConfigurationError


def validate_mcp_url(raw_url: str, *, allowed_endpoint_hosts: frozenset[str]) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AIConfigurationError("MCP URL must be an absolute HTTP(S) URL")
    host = parsed.hostname.lower()
    private = _is_private_or_loopback(host)
    if not private and host not in allowed_endpoint_hosts:
        raise AIConfigurationError("MCP host must be local/private or explicitly allowed")
    if not private and parsed.scheme != "https":
        raise AIConfigurationError("MCP endpoints must use HTTPS outside local/private networks")


def _is_private_or_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback

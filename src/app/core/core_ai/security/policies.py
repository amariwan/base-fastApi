"""Shared endpoint policy for configurable model servers."""

import ipaddress
from urllib.parse import urlparse


def validate_http_endpoint(raw_url: str, *, field_name: str, allowed_hosts: frozenset[str]) -> None:
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"AI_{field_name} must be an absolute HTTP(S) URL")
    host = parsed.hostname.lower()
    private = _is_private_or_loopback(host)
    if not private and host not in allowed_hosts:
        raise ValueError(f"AI_{field_name} host must be local/private or explicitly allowed")
    if not private and parsed.scheme != "https":
        raise ValueError(f"AI_{field_name} must use HTTPS for non-local endpoints")


def _is_private_or_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback

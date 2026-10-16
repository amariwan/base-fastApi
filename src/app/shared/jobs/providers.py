"""ARQ pool provider for the shared jobs contract.

ARQ is an optional dependency. When it is not installed or configured, the
pool is unavailable and health checks report it as skipped.
"""


def get_arq_pool() -> object | None:
    """Return the shared ARQ connection pool, if ARQ is enabled.

    Returns ``None`` when ARQ is not installed or configured, which causes
    the health check to report the arq component as skipped.
    """
    try:
        import arq  # noqa: F401
    except ImportError:
        return None
    return None
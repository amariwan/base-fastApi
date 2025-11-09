from __future__ import annotations

import ssl

from sqlalchemy.engine import URL, make_url

from config import get_db_settings

from .options import DB_REQUIRE_SSL, DB_SSL_NO_VERIFY

_MASK = "****"

def build_url() -> URL:
    db = get_db_settings()
    if getattr(db, "DATABASE_URL", None):
        # akzeptiere beide Varianten: asyncpg/sync
        try:
            return make_url(db.DATABASE_URL)
        except Exception:
            pass  # fallback auf Komponenten

    host = db.DB_HOST or "127.0.0.1"
    return URL.create(
        drivername="postgresql+asyncpg",
        username=db.DB_USERNAME,
        password=db.DB_PASSWORD,
        host=host,
        port=int(db.DB_PORT),
        database=db.DB_DATABASE,
    )

def masked(url: URL | str) -> str:
    try:
        u = make_url(str(url))
        return str(u.set(username=_MASK, password=_MASK if u.password else None))
    except Exception:
        return str(url)

def ssl_context() -> ssl.SSLContext | None:
    if not DB_REQUIRE_SSL:
        return None
    ctx = ssl.create_default_context()
    if DB_SSL_NO_VERIFY:
        # Nur in DEV/TEST zulassen; PROD soll verifizieren
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

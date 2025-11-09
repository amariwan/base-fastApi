# DB

Asynchrone DB-Schicht mit SQLAlchemy.
Ziele: **sicher per Default**, **ENV-konfigurierbar**, **robust gegen Ausfälle**, **keine Secrets im Code/Repo**.

## Struktur

```
db
 ┣ migration/
 ┃ ┣ versions/             # Alembic-Revisions
 ┃ ┣ env.py                # nutzt Settings, erzwingt Sync-Driver
 ┃ ┗ script.py.mako        # Template (Black/Ruff optional)
 ┣ database.py             # Engine/Session, Init, Backoff, Helpers
 ┣ dsn.py                  # URL-Building, Masking, SSL-Kontext
 ┣ options.py              # Runtime-Parameter aus Settings
 ┗ __init__.py             # Dependency-Factories
```

## Sicherheitsprinzipien

* **Keine DSNs/Credentials im Repo** (auch nicht in `alembic.ini`).
* **SSL in PROD Pflicht**. `DB_SSL_NO_VERIFY` in PROD verboten.
* **Masking** in Logs (`postgresql://****:****@…`).
* **Keine Interna/Tracebacks** nach außen (Error-Handling übernimmt `core/error_handling`).

## ENV / Settings

Relevante Werte (Bezeichner können aus deinen `get_db_settings()` kommen):

```dotenv
# Verbindung
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=database
DB_USERNAME=postgres
DB_PASSWORD=postgres

# Pool/Timeouts
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE_SECS=300
DB_POOL_TIMEOUT=30.0
DB_CONNECT_TIMEOUT=10.0
DB_COMMAND_TIMEOUT=60.0

# Startup-Retry
DB_STARTUP_MAX_RETRIES=10
DB_STARTUP_BASE_DELAY=0.5
DB_STARTUP_MAX_DELAY=10.0
DB_STARTUP_OVERALL_TIMEOUT=60.0

# SSL
DB_SSL=true
DB_SSL_NO_VERIFY=false  # nur DEV/TEST

# App-Meta für server_settings
APP_NAME=service
APP_ENV=prod            # dev|local|test|prod
```

**Hinweis:** Wenn `DATABASE_URL` gesetzt ist, wird sie bevorzugt (async oder sync). Fehlt sie, wird aus Einzelwerten gebaut.

## Laufzeit-Verhalten

* **Engine**: lazy, async (`create_async_engine`), Pre-Ping, Pool-Recycle.
* **server_settings** (Postgres): `statement_timeout`, `idle_in_transaction_session_timeout`, `application_name`, `timezone=UTC`.
* **Backoff** beim Start: Exponential + Jitter, begrenzt durch `DB_STARTUP_*`.
* **Read-Only** Sessions: `SET TRANSACTION READ ONLY` (best effort, auf Sqlite no-op).
* **PROD-Guard**: ohne SSL oder mit `NO_VERIFY` → **Startfehler**.

## Nutzung

### Session als Dependency (FastAPI)

```python
from fastapi import Depends
from db import get_session_dependency, get_readonly_session

@router.get("/items")
async def list_items(session = Depends(get_readonly_session)):
    rows = await session.execute(...)
    return rows.scalars().all()

@router.post("/items")
async def create_item(session = Depends(get_session_dependency)):
    session.add(...)
    # Commit/Rollback handled by dependency
```

### Manuell (Kontextmanager)

```python
from db.database import db

async with db.session(read_only=True) as s:
    res = await s.execute(...)
```

### App-Lifecycle

`core/lifespan.py` ruft `db.init_models()` nur in produktionsähnlichen Umgebungen auf. In `dev/test/local` wird **nicht** an die echte DB verbunden.

## Alembic (Migrationen)

**Kein Hardcoding in `alembic.ini`.** URL kommt aus `migration/env.py` via Settings.

* Neue Revision:

  ```bash
  alembic -c db/migration/alembic.ini revision -m "add table xyz"
  ```
* Autogenerate:

  ```bash
  alembic -c db/migration/alembic.ini revision --autogenerate -m "xyz"
  ```
* Upgrade/Downgrade:

  ```bash
  alembic -c db/migration/alembic.ini upgrade head
  alembic -c db/migration/alembic.ini downgrade -1
  ```

`env.py` erzwingt **Sync-Driver** (`postgresql+psycopg`) und ersetzt ggf. `asyncpg`.
`target_metadata` zeigt auf `service.models.Base`.

## Logging

* Engine-Erstellung:

  ```
  DB engine created {"url": "postgresql://****:****@host:5432/db"}
  ```
* Backoff:

  ```
  DB not ready – retrying {"attempt": 3, "wait": 1.25}
  DB became available
  ```
* Dispose:

  ```
  DB engine disposed
  ```

**Keine Passwörter/DSNs im Klartext.**

## Tests (Empfehlungen)

* **SSL-Policy**: in `prod` ohne SSL → Exception.
* **Masking**: Log enthält keine Credentials.
* **Backoff-Grenzen**: bei Unreachable DB → Abbruch innerhalb `DB_STARTUP_OVERALL_TIMEOUT`.
* **Readonly**: `read_only=True` setzt Transaktion (auf PG).
* **Alembic URL-Mapping**: `asyncpg` → `psycopg` in `env.py`.

Beispiel (pytest, paraphrasiert):

```python
import os, pytest
from db.database import Database

def test_prod_requires_ssl(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("DB_SSL", "false")
    with pytest.raises(RuntimeError):
        Database().engine  # erzwingt SSL

def test_masking_does_not_leak_password(caplog):
    from db.dsn import masked
    assert "****" in masked("postgresql://user:pass@h/db")
```

## Do’s & Don’ts

* ✅ ENV nutzen, nicht committen.
* ✅ In PROD: SSL erzwingen, `NO_VERIFY=false`.
* ✅ Kein Wildwuchs: DB-Code nur in `db/`.
* ✅ Keine Session global cachen (nur factory/engine).
* ❌ Kein Secret/DSN in `alembic.ini`/Logs.
* ❌ Kein `autocommit`/silent-fail bei Fehlern.

## Wartung

* Pool-Parameter über ENV tunen, nicht im Code.
* Statement-Timeouts sauber setzen (DoS-Prävention).
* Regelmäßig Migrationskonsistenz prüfen (Autogenerate + Review).
* Read-only-Pfad für GET-Endpoints nutzen.

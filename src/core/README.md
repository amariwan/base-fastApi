# Core

Zentrale Infrastruktur-Schicht: App-Bootstrapping, Middleware, OpenAPI, Routing, Lifecycles, Scheduler, Auth, Fehlerbehandlung.

## Ziele

* **Sicher per Default:** strikte CORS, Security-Header, keine Interna in Responses.
* **Konfigurierbar über ENV:** kein Rebuild für Konfigwechsel.
* **Wartbar:** kleine, fokussierte Module; keine Zyklen.
* **Beobachtbar:** Request-ID, sauberes Logging.

---

## Struktur

```
core
 ┣ auth/            # JWT, RBAC, Dependencies
 ┣ error_handling/  # RFC 9110 ProblemDetails, Handler
 ┣ healthcheck/     # /health, /whoami (optional Diagnose)
 ┣ factory.py       # create_app()
 ┣ lifespan.py      # Startup/Shutdown, DB init, Scheduler
 ┣ middleware.py    # Request-ID, GZip, CORS, Security-Header
 ┣ openapi.py       # Security-Schemes, opId-Refactor
 ┣ routes.py        # API-Prefix/Version, Router-Registrierung
 ┣ scheduler.py     # Hintergrundjobs (opt-in)
 ┗ __init__.py
```

---

## ENV

**Alle Schalter sind opt-in/opt-out über ENV.** Nichts hart verdrahtet.

```dotenv
# App
APP_TITLE=service
APP_VERSION=0.0.0+local
API_PREFIX=/api
API_VERSION=v1
ENV=dev              # dev|local|test|prod
TEST_MODE=false

# OpenAPI
OPENAPI_ENABLE_BEARER=true

# CORS (leer = strikt; kommagetrennt konfigurieren)
CORS_ALLOW_ORIGINS=https://example.com,https://admin.example.com
CORS_ALLOW_HEADERS=Authorization,Content-Type
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=600

# Request-ID / Security-Header
TRUST_X_REQUEST_ID=false
SECURITY_HEADERS_ENABLE=true
HSTS_ENABLE=true
HSTS_MAX_AGE=63072000
REFERRER_POLICY=no-referrer
XFRAME_DENY=true

# Scheduler
SCHEDULER_ENABLED=true
AUTO_PUBLISH_INTERVAL_SECONDS=60
```

> **Prod-Hinweis:** `CORS_ALLOW_ORIGINS` **niemals** leer lassen und **kein `"*"`**.

---

## Bootstrapping

```python
# main.py
from core.factory import create_app
app = create_app()
```

`create_app()` macht:

1. Middleware registrieren (Request-ID, GZip, CORS, Security-Header)
2. Exception-Handler registrieren (RFC 9110, keine Interna)
3. Router registrieren (Prefix `API_PREFIX/API_VERSION`)
4. OpenAPI Security optional aktivieren (`OPENAPI_ENABLE_BEARER`)

Lifecycle (`lifespan.py`):

* Dev/Test: **keine** produktive DB-Init, kein Dispose (schneller, sicher).
* Prod: DB-Init + optionaler Scheduler (`SCHEDULER_ENABLED`).

---

## Sicherheit

* **CORS:** strikt per ENV. In Prod keine Wildcards.
* **Security-Header:** HSTS, XFO, Referrer-Policy, Permissions-Policy.
* **Request-ID:** generiert; nur Header vertrauen, wenn `TRUST_X_REQUEST_ID=true`.
* **Fehlerausgaben:** RFC 9110 ProblemDetails; **5xx immer generisch**, keine SQL/Stacktraces.
* **Auth:** JWT/JWKS + RBAC im Paket `core/auth` (siehe dortige README).

---

## Routing

* Basis: `/{API_PREFIX}/{API_VERSION}`, z. B. `/api/v1`.
* `core.routes.build_api_router()` bindet:

  * `core.healthcheck.routes` (z. B. `/health`, `/whoami`)
* `register_routers()` ist idempotent (testsicher).

---

## Middleware

* **RequestIdMiddleware**: setzt/propagiert `X-Request-ID` (optional vertrauenswürdig).
* **GZipMiddleware**: ab 1 KB.
* **CORS**: vollständig via ENV.
* **SecurityHeadersMiddleware**: HSTS, XFO, Referrer-Policy, Permissions-Policy.

---

## OpenAPI

* `simplify_operation_ids()` → lesbare operationIds.
* `add_bearer_security()` → globales JWT-Scheme, wenn `OPENAPI_ENABLE_BEARER=true`.

---

## Scheduler

* `PublishScheduler` (Background-Task) nur wenn `SCHEDULER_ENABLED=true`.
* Intervall via `AUTO_PUBLISH_INTERVAL_SECONDS`.
* Robust gegen Cancel/Exceptions; Jitter gegen Thundering-Herd.
* **Nie in Test/Local automatisch starten.**

---

## Healthcheck

* `GET /health` → `{}` (Liveness/Readiness).
* `GET /health?config=true` → ausgewählte Settings (ohne Secrets), optional rollenpflichtig.
* `GET /whoami` → Claims des aktuellen Users (Auth-abhängig).

Details: siehe `core/healthcheck/README.md`.

---

## Fehlerbehandlung

* Einheitliches Format `application/problem+json` (RFC 9110).
* 4xx: knappe, nutzerrelevante Infos.
* 5xx: generisch, **keine Interna**. Trace-ID zur Korrelation.
* Mapping: HTTP/Validation/Domain/DB/Unhandled → klare Statuscodes.

Details: siehe `core/error_handling/README.md`.

---

## Qualitätsregeln

* **KISS/SOLID/DRY:** kleine Module, Single Responsibility, kein toter Code.
* **ENV-Driven:** keine Konstantschlachten im Code.
* **Keine Zyklen:** Lazy-Imports in Routern/Jobs.
* **Logs:** strukturiert, ohne PII/Secrets; Trace-ID immer setzen.
* **Tests:** Verhalten > Implementierung (Public API testen).

---

## Quick-Checks (CI-geeignet)

* **CORS:** Origin nicht leer im Prod.
* **Security-Header:** HSTS/XFO/Referrer-Policy aktiv.
* **Routes:** Präfix `API_PREFIX/API_VERSION` korrekt.
* **OpenAPI:** Bearer-Scheme aktiv, wenn Flag true.
* **Scheduler:** startet nur, wenn Flag true.
* **Lifespan:** Prod → DB init/dispose; Test/Local → nicht.

---

## Beispiel: minimale App-Konfiguration (dev)

```dotenv
APP_TITLE=service
API_PREFIX=/api
API_VERSION=v1
ENV=local
OPENAPI_ENABLE_BEARER=true
CORS_ALLOW_ORIGINS=http://localhost:5173
SECURITY_HEADERS_ENABLE=true
TRUST_X_REQUEST_ID=false
SCHEDULER_ENABLED=false
```

---

## Erweiterung

* Neue Middlewares → `register_middleware()`.
* Neue Router → in `build_api_router()` lazy einbinden.
* Zusätzliche Error-Handler → im Paket `error_handling/handlers` ergänzen.
* Weitere Health-Probes → in `core/healthcheck/services.py` kapseln.

# 🩺 Core Healthcheck

Das `core.healthcheck`-Modul stellt zentrale **System- und Diagnoseschnittstellen** bereit.
Es dient sowohl der **technischen Überwachung** (Kubernetes, Docker, Load-Balancer)
als auch der **administrativen Einsicht** (z. B. Versions-, Config- oder Statusprüfung).

---

## 🧩 Ziel

Das Modul erlaubt eine standardisierte Abfrage des Systemzustands:
- Funktioniert der Service?
- Ist die Konfiguration korrekt geladen?
- Welche Datenbank- oder App-Parameter sind aktiv (optional, sicher)?
- Wer ist aktuell authentifiziert (`whoami`-Endpoint)?

Dabei gilt: **Sicherheit vor Bequemlichkeit** – interne Konfiguration wird nur mit explizitem Flag und korrekter Authentifizierung offengelegt.

---

## 📦 Aufbau

```

core/healthcheck
┣ 📜routes.py       # FastAPI-Endpoints (/health, /whoami)
┣ 📜services.py     # interne Logik (Statusprüfung, Config-Abfrage)
┣ 📜schemas.py      # optionale Response-Schemas für OpenAPI
┣ 📜security.py     # Zugriffsschutz & erlaubte Konfiguration
┗ 📜__init__.py

````

---

## ⚙️ Endpoints

### `GET /api/v1/health`
Überprüft, ob der Service erreichbar und konfiguriert ist.

#### 🔹 Standard-Modus
```bash
GET /api/v1/health
````

Antwort:

```json
{}
```

* Rückgabe: `200 OK`
* Zweck: Liveness-Check für Load Balancer, Docker, Kubernetes.

#### 🔹 Diagnose-Modus

```bash
GET /api/v1/health?config=true
```

Antwort:

```json
{
  "Settings": {
    "DB_SETTINGS": { "DB_PORT": 5432, "DB_DATABASE": "database" },
    "APP_SETTINGS": { "LOG_LEVEL": "INFO", "TEST_MODE": false }
  }
}
```

* Nur in geschützten Umgebungen (z. B. intern oder admin-Token).
* Konfigurationswerte werden über `get_app_settings()` und `get_db_settings()` geladen.

---

### `GET /api/v1/whoami`

Gibt Informationen über den aktuell authentifizierten Benutzer zurück.

Beispiel:

```bash
GET /api/v1/whoami
Authorization: Bearer <token>
```

Antwort:

```json
{
  "sub": "f440ded9-925f-4dd2-9faa-2ee6f04c8362",
  "name": "Toni T.",
  "email": "t.toni@example.org",
  "preferred_username": "t.toni@example.org",
  "organization": "GWQ_RehaInside_Org_104444446",
  "roles": ["admin", "reader"]
}
```

* Nutzt `get_current_user()` aus `core.auth`.
* Ideal für Debugging, Token-Validierung und Monitoring.

---

## 🧱 Sicherheitsprinzipien

| Regel                     | Beschreibung                                                                                   |
| ------------------------- | ---------------------------------------------------------------------------------------------- |
| **Keine sensiblen Daten** | `config=true` darf keine Secrets, Passwörter, Tokens oder Verbindungen ausgeben.               |
| **Auth-Trennung**         | `/health` ist öffentlich (für Load Balancer), `/whoami` ist nur mit gültigem Token erreichbar. |
| **Readonly**              | Endpoints führen **nie** Schreiboperationen aus.                                               |
| **Logging-Konsistenz**    | Jeder Aufruf wird über `system_logger` mit `traceId` geloggt.                                  |
| **Keine PII-Leaks**       | Nur minimale Benutzerinfos (Claims) in `/whoami`.                                              |

---

## 🧩 Beispiel-Implementierung (vereinfacht)

```python
from fastapi import APIRouter, Depends, Query
from config import get_app_settings, get_db_settings
from core.auth import get_current_user
from shared.logging.AppLogger import system_logger as syslog

router = APIRouter()

@router.get("/health")
async def healthcheck(config: bool = Query(False)) -> dict:
    if not config:
        return {}
    app_settings = get_app_settings()
    db_settings = get_db_settings()
    settings_data = {
        "Settings": {
            "DB_SETTINGS": {
                "DB_PORT": db_settings.DB_PORT,
                "DB_DATABASE": db_settings.DB_DATABASE,
            },
            "APP_SETTINGS": {
                "LOG_LEVEL": app_settings.LOG_LEVEL,
                "TEST_MODE": app_settings.TEST_MODE,
            },
        }
    }
    syslog.debug("Healthcheck with config called", extra={"Backend-Settings": settings_data})
    return settings_data

@router.get("/whoami")
async def whoami(user=Depends(get_current_user)) -> dict:
    data = {
        "sub": user.sub,
        "name": user.name,
        "email": user.email,
        "preferred_username": user.preferred_username,
        "organization": user.organization,
        "roles": user.roles,
    }
    syslog.debug("whoami called", extra={"User": data})
    return data
```

---

## 🧠 Best Practices

| Empfehlung                                | Begründung                                                       |
| ----------------------------------------- | ---------------------------------------------------------------- |
| `/health` öffentlich, `/whoami` geschützt | Kubernetes & Prometheus dürfen ohne Auth prüfen, Userdaten nicht |
| Keine Passwörter oder Keys ausgeben       | Geheimnisse gehören nur ins ENV oder Vault                       |
| Logs anonymisieren                        | Nie personenbezogene Daten in Logs                               |
| Query-Flag validieren                     | `config=true` sollte optional auth- oder rollenpflichtig sein    |
| Teste Health regelmäßig                   | Automatische Liveness-Probes in CI/CD und Deployment-Pipelines   |

---

## 🧪 Testfälle (empfohlen)

| Test                      | Erwartetes Ergebnis                      |
| ------------------------- | ---------------------------------------- |
| `GET /health`             | 200 OK, `{}`                             |
| `GET /health?config=true` | 200 OK, enthält Settings (keine Secrets) |
| `GET /whoami` ohne Token  | 401 Unauthorized                         |
| `GET /whoami` mit Token   | 200 OK, enthält Claims                   |
| Logging-Test              | `system_logger` enthält Request-TraceId  |

---

## 🧩 Erweiterung

Neue Diagnosepunkte lassen sich einfach hinzufügen, z. B.:

```python
@router.get("/health/db")
async def check_db_connection() -> dict:
    # führt SELECT 1 aus
    return {"db": "ok"}
```

oder:

```python
@router.get("/health/version")
async def get_version() -> dict:
    from config import APP_VERSION
    return {"version": APP_VERSION}
```

---

## ✅ Fazit

Das Healthcheck-Modul liefert eine robuste und sichere Grundlage für:

* Liveness- und Readiness-Probes
* API-Monitoring
* Debugging (authentifizierte Benutzerabfragen)
* Service-Diagnose ohne Risiko von Datenlecks

Es folgt den Prinzipien von **Minimal Disclosure** und **Defense in Depth**.

---

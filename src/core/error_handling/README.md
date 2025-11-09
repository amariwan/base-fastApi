# ⚙️ Core Error Handling

Zentrale Fehlerbehandlung für das Backend.
Dieses Modul kapselt alle Mechanismen, um **interne Ausnahmen in RFC 9110-konforme JSON-Antworten** zu transformieren, sauber zu loggen und sicher gegenüber Clients zu kommunizieren.

---

## 🧩 Ziel

Das Ziel dieses Moduls ist **einheitliches, sicheres und nachvollziehbares Fehlerverhalten** über alle API-Endpunkte hinweg:

- Konsistente API-Responses (`application/problem+json`)
- Einheitliche Struktur für Logs & Trace-IDs
- Trennung zwischen *internen* und *öffentlichen* Fehlern
- Kein Leak von System-, SQL- oder Infrastrukturinformationen
- Erweiterbar für Domain-, Datenbank- und Infrastrukturfehler

---

## 📦 Aufbau

```

core/error_handling
┣ 📂handlers
┃ ┣ 📜http_handlers.py         # HTTP & Validation-Fehler (FastAPI, Pydantic)
┃ ┣ 📜database_handlers.py     # SQLAlchemy & Integrity-Fehler
┃ ┣ 📜domain_handlers.py       # Domain-spezifische Fehler (z. B. NotFound, Conflict)
┃ ┣ 📜system_handlers.py       # AppError & unhandled Exceptions
┃ ┗ 📜__init__.py              # zentrale Registrierung
┣ 📜payload.py                 # RFC9110 ProblemDetails Builder
┣ 📜types.py                   # ErrorType & AppError-Klassen
┗ 📜__init__.py

````

---

## 🧱 Struktur und Verantwortung

| Modul                           | Verantwortung                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------- |
| `handlers/http_handlers.py`     | Wandelt `HTTPException` & `RequestValidationError` in API-konforme Antworten um |
| `handlers/database_handlers.py` | Behandelt `SQLAlchemyError` & `IntegrityError` (keine SQL-Leaks)                |
| `handlers/domain_handlers.py`   | Handhabt Domain-Fehler aus `core.errors`                                        |
| `handlers/system_handlers.py`   | Fängt `AppError` & alle unbekannten Fehler (`Exception`) ab                     |
| `payload.py`                    | Baut RFC 9110-konforme ProblemDetails-Responses                                 |
| `types.py`                      | Definiert Typsicherheit & interne Fehlerobjekte                                 |

---

## 📤 Response-Format (RFC 9110)

Alle Fehler werden als `application/problem+json` ausgegeben.

```json
{
  "type": "https://www.rfc-editor.org/rfc/rfc9110.html#name-400-bad-request",
  "title": "Bad Request",
  "status": 400,
  "errors": {
    "field": ["Invalid value"]
  },
  "traceId": "req-abc123"
}
````

### Felder

| Feld      | Beschreibung                                |
| --------- | ------------------------------------------- |
| `type`    | RFC-Referenz auf den HTTP-Fehlertyp         |
| `title`   | Kurztitel (z. B. *Bad Request*, *Conflict*) |
| `status`  | HTTP-Statuscode                             |
| `errors`  | Key-Value-Map der Fehlermeldungen           |
| `traceId` | Eindeutige Request-ID aus Logging-Context   |

---

## 🚫 Sicherheit

**Grundregel:** Der Client darf nur wissen, *dass* etwas schiefging, nicht *wie*.

| Fehlerquelle                  | Sichtbar für User           | Intern geloggt             |
| ----------------------------- | --------------------------- | -------------------------- |
| **ValidationError (422)**     | ✅ Ja – Feldbezogen          | 🔒 Vollständig              |
| **Auth (401/403)**            | ✅ Ja – generische Nachricht | 🔒 Keine Token-/Headerdaten |
| **ConflictError (409)**       | ✅ Ja – Business-Info        | 🔒 Stacktrace               |
| **SQLAlchemyError (500)**     | ❌ Nein                      | 🔒 Volltext inkl. Query     |
| **Unhandled Exception (500)** | ❌ Nein                      | 🔒 Stacktrace & Kontext     |

**Nie ausgeben:**

* Stacktraces
* SQL/Constraint-Namen
* Systempfade, Hostnamen, ENV
* Tokens, JWKS, Keys, Secrets

---

## ⚡ Registrierung im Startup

```python
from core.error_handling import register_exception_handlers

def create_app() -> FastAPI:
    app = FastAPI(title="Service")
    register_exception_handlers(app)
    return app
```

---

## 🧪 Beispielantworten

### 422 – Validation

```json
{
  "title": "Unprocessable Entity",
  "status": 422,
  "errors": { "email": ["Field required"] },
  "traceId": "req-xyz"
}
```

### 409 – Conflict

```json
{
  "title": "Conflict",
  "status": 409,
  "errors": { "Conflict": ["Already exists"] },
  "traceId": "req-xyz"
}
```

### 500 – Internal Server Error

```json
{
  "title": "Internal Server Error",
  "status": 500,
  "errors": { "Error": ["Internal error"] },
  "traceId": "req-xyz"
}
```

---

## 🧠 Designprinzipien

* **KISS:** Jeder Handler behandelt nur eine Exception-Art.
* **SRP (Single Responsibility):** Kein Handler macht Logging, Response und Mapping gleichzeitig.
* **DRY:** Response-Struktur zentral in `payload.py`.
* **Secure by default:** Keine Details an den Client, keine stack traces.
* **Observable:** Jeder Fehler ist über `traceId` korrelierbar.

---

## ✅ Quickcheck – Testbare Regeln

| Test                     | Erwartetes Verhalten          |
| ------------------------ | ----------------------------- |
| `RequestValidationError` | 422 + Feldfehler              |
| `IntegrityError`         | 409 + „Constraint violation“  |
| `SQLAlchemyError`        | 500 + generisch               |
| `AppError(409)`          | 409 + App-spezifische Message |
| `Unhandled Exception`    | 500 + generisch               |

---

## 🧩 Erweiterung

Neue Fehlerkategorien lassen sich einfach ergänzen:

```python
# handlers/security_handlers.py
async def handle_auth_error(request, exc):
    ...
```

und in `handlers/__init__.py` registrieren:

```python
from .security_handlers import handle_auth_error
app.add_exception_handler(AuthError, handle_auth_error)
```

---

## 🏁 Fazit

Dieses Modul ist die **sichere, einheitliche und erweiterbare Fehlerbasis** für dein gesamtes Backend.
Es stellt sicher, dass deine APIs nach außen konsistent bleiben – unabhängig davon, ob der Fehler aus FastAPI, SQLAlchemy oder der Business-Logik stammt.

---

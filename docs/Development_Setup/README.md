# Development Setup (Backend)

Diese Anleitung beschreibt das lokale Setup fuer den Backend-Service unter `backend/`.

## Voraussetzungen
- Linux, macOS oder Windows mit WSL2 (empfohlen).
- Python `3.13.x` (laut `pyproject.toml`).
- `uv` als Paket-/Umgebungsmanager.
- Optional `just` als Task-Runner.

## 1) Projektordner

```bash
cd /workspace/backend
```

## 2) Tooling installieren

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### just (optional, aber empfohlen)

```bash
sudo apt update
sudo apt install -y just
```

## 3) Dependencies installieren

```bash
uv sync --group dev
```

## 4) Lokale Konfiguration

`.env` aus Vorlage erzeugen:

```bash
cp .env.example .env
```

Wichtige Variablen fuer lokale Entwicklung:

| Variable | Zweck | Empfehlung lokal |
|---|---|---|
| `APP_ENV` | Laufzeitmodus | `local` |
| `API_PREFIX` | API-Prefix | `/api` |
| `LOG_LEVEL` | Log-Level | `INFO` oder `DEBUG` |
| `CORS_ALLOWED_ORIGINS` | CORS-Freigaben | z. B. `http://127.0.0.1:5173,http://127.0.0.1:5500` |
| `DB_ENABLED` | Optionaler DB-Stack | `false` (Default) |
| `STORAGE_BACKEND` | Storage-Adapter (`filesystem`/`s3`) | `filesystem` |
| `FILESYSTEM_ROOT` | Root fuer Filesystem-Storage | `/workspace/backend/data` lokal |
| `STORAGE_BUCKET` | Bucket fuer `STORAGE_BACKEND=s3` | z. B. `docgen-dev` |
| `STORAGE_PREFIX` | Prefix im Bucket | z. B. `documents` |
| `S3_ENDPOINT` | S3 Endpoint (MinIO) | z. B. `http://127.0.0.1:9000` |
| `S3_REGION` | Region fuer S3 Client | z. B. `eu-central-1` |

Hinweis:
- Build/View laufen ohne externen Upstream und nutzen den konfigurierten Storage-Adapter.
- `DB_ENABLED=false` benoetigt keine lokale PostgreSQL-Instanz.

## 5) Service starten

### Mit FastAPI Dev Server (just)

```bash
just dev
```

### Mit Uvicorn (just)

```bash
just dev-uvicorn
```

Direkt ohne `just`:

```bash
uv run -m fastapi dev app/asgi.py --port 5000
```

## 6) Smoke Tests

```bash
curl -sS http://127.0.0.1:5000/api/health
```

Erwartete Antwort:

```json
{"status":"ok"}
```

Optional:

```bash
curl -sS http://127.0.0.1:5000/api/config/
curl -sS http://127.0.0.1:5000/api/config/validate
```

## 7) Tests und Quality Gates

```bash
just test
just test-unit
just test-e2e
just lint
just mypy
```

Mit Coverage:

```bash
just test-cov
```

Hinweise zur Teststrategie:
- Unit-Tests liegen co-located neben dem Code (z. B. `service.py` -> `service_test.py`).
- E2E-Tests liegen unter `tests/e2e/`.
- Marker werden automatisch per Pfad zugewiesen (`unit`, `integration`, `e2e`).
- `just test-cov` misst kombinierte Coverage aus Unit + E2E und erzwingt `--cov-fail-under=75`.

## 8) Frontend-Integration lokal (optional)

Frontend separat starten:

```bash
just dev-frontend
```

Backend + Frontend zusammen:

```bash
just dev-with-frontend
```

Wichtig:
- Die App-Konfiguration liest `CORS_ALLOWED_ORIGINS`.
- Falls Browser-CORS-Fehler auftreten, `CORS_ALLOWED_ORIGINS` explizit in `.env` setzen.

## 9) Profiling (optional)

Profiling aktivieren:

```bash
PROFILING_ENABLED=true
```

Details siehe `../Middleware/Profiler.md`.

## 10) Bekannte Stolperfallen

- `404` auf `/health`: Der Health-Endpoint liegt unter `/api/health`.
- `503` auf DOCX->PDF Konvertierung: lokales `soffice` (LibreOffice) fehlt.
- CORS-Fehler im Browser: `CORS_ALLOWED_ORIGINS` nicht passend gesetzt.
- Falscher Startordner: Befehle immer aus `backend/` ausfuehren.

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set dotenv-load := true
set dotenv-filename := ".env.dev"

# ================================================
# Projekt- und Umgebungsvariablen
# ================================================

# Hauptdatei für ASGI-App und FastAPI
APP_FILE := "src/asgi.py"
ASGI_APP := "app.asgi:app"
HOST     := env("HOST", "0.0.0.0")    # Standard: 0.0.0.0 für alle Netzwerke verfügbar
PORT     := env("PORT", "8001")       # Standard: 8001
WORKERS  := env("WORKERS", "2")       # Standard: 2 Worker-Prozesse
TIMEOUT  := env("TIMEOUT", "60")      # Standard: Timeout von 60 Sekunden
DEBUG    := env("DEBUG", "false")     # Debugging-Modus (false als Standard)
ENV      := env("ENV", "development") # Umgebungsmodus (default: development)

ALEMBIC_DIR := "src/db/migration"     # Verzeichnis für Alembic-Migrationen
ALEMBIC_INI := "alembic.ini"          # Alembic-Konfigurationsdatei

# ================================================
# Default & Umgebungs-Setup
# ================================================

@default:
	just --list  # Listet alle verfügbaren Tasks auf

# ================================================
# Entwicklung (Dev) & Produktion (Prod)
# ================================================

clean:
	rm -rf .venv ENV env .venv .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml dist build *.egg-info pip-wheel-metadata wheelhouse node_modules
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete || true
	find . -type d -name ".tox" -prune -exec rm -rf {} +
	find . -type d -name ".hypothesis" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	# remove common wheel / build metadata
	rm -rf pip-wheel-metadata wheelhouse || true

dev:
	# FastAPI im Entwicklungsmodus starten, mit der Option, einen Fehlercode bei Ctrl+C zu ignorieren
	PYTHONPATH=src uv run fastapi dev --host {{HOST}} --port {{PORT}} {{APP_FILE}} \
	|| code=$$?; [ "$$code" -eq 130 ] && exit 0 || exit "$$code"

dev-uvicorn:
	# Uvicorn-Server für die Entwicklung starten, mit Hot-Reload
	PYTHONPATH=src uv run uvicorn {{ASGI_APP}} --host {{HOST}} --port {{PORT}} --reload

refresh:
	just clean
	just dev

prod:
	# Produktionsserver mit Gunicorn starten, um die FastAPI-Anwendung zu betreiben
	PYTHONPATH=src gunicorn {{ASGI_APP}} -k uvicorn.workers.UvicornWorker --bind {{HOST}}:{{PORT}} --workers {{WORKERS}} --timeout {{TIMEOUT}}

# ================================================
# Tests (Unit, Integration, E2E, Coverage)
# ================================================

test:
	# Allgemeine Tests ausführen
	PYTHONPATH=. uv run pytest -q

test-unit:
	# Unit-Tests ausführen
	PYTHONPATH=. uv run pytest -q -m unit

test-integration:
	# Integrationstests ausführen
	PYTHONPATH=. uv run pytest -q -m integration

test-e2e:
	# End-to-End-Tests ausführen
	PYTHONPATH=. uv run pytest -q -m e2e

test-all:
	# Alle Tests (Unit, Integration, E2E) ausführen
	just test-unit
	just test-integration
	just test-e2e

test-cov:
	# Tests mit Coverage-Bericht ausführen
	PYTHONPATH=. uv run pytest --maxfail=1 --disable-warnings -q --cov=src/ --cov-report=term-missing --cov-report=xml --junitxml=backend_report.xml

# ================================================
# Linting, Type-Checking und Formatierung
# ================================================

lint:
	# Linting durchführen
	uv run ruff check .
	uv run ruff format --check .

mypy:
	# Mypy für statische Typüberprüfung
	uv run mypy -p  -p core -p shared

pyright:
	# Pyright für zusätzliche Typprüfung
	uv run pyright src tests

fmt:
	# Formatierung durch Ruff (automatisch)
	uvx ruff format .

fix:
	# Formatierung und Fehlerbehebung
	uvx ruff check --fix .
	uvx ruff format .

typecheck:
	# Pyright Typprüfung durchführen
	uvx pyright

check-all:
	# Alle Qualitätssicherungs-Tasks ausführen (Linting, Typprüfung, Tests)
	just lint
	just mypy
	just pyright
	just fmt
	just test-all

update:
	# Abhängigkeiten auf den neuesten Stand bringen
	uv sync --upgrade

# ================================================
# Datenbankverwaltung (Alembic Migrationen)
# ================================================

db-check:
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} current
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} heads
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} history -n 10

db-stamp rev="head":
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -z "${DATABASE_URL:-}" ]; then echo "ERROR: DATABASE_URL not set"; exit 1; fi
	export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} stamp {{rev}}

db-up-sql rev="head":
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} upgrade {{rev}} --sql


db-rev msg="migration":
	# Alembic Migration erzeugen (mit ENV-Variablen aus .env oder .env.dev)
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	# Falls DATABASE_URL vorhanden ist, auf den synchronen Driver umstellen
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} revision --autogenerate -m "{{msg}}"

db-up rev="head":
	# Alembic Migration auf "head" (aktuelle Revision) anwenden
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} upgrade {{rev}}

db-down rev="-1":
	# Rückgängig machen einer Migration auf vorherige Revision
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} downgrade {{rev}}

db-current:
	# Aktuelle Datenbankrevision prüfen
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} current

db-history:
	# Historie der Migrationen anzeigen
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} history --verbose


db-reset-soft:
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} downgrade base
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} upgrade head


db-reset:
	# Drop & recreate database
	if [ -f .env ]; then set -a; source .env; set +a; fi
	if [ -f .env.dev ]; then set -a; source .env.dev; set +a; fi
	if [ -n "${DATABASE_URL:-}" ]; then export DATABASE_URL="${DATABASE_URL//+asyncpg/+psycopg}"; fi
	uv run python -c "from sqlalchemy import create_engine, text; import os; url = os.environ['DATABASE_URL'].replace('+asyncpg','+psycopg'); engine = create_engine(url); conn = engine.connect().execution_options(isolation_level='AUTOCOMMIT'); conn.execute(text('DROP SCHEMA public CASCADE')); conn.execute(text('CREATE SCHEMA public')); conn.close()"
	# Run fresh migrations
	cd {{ALEMBIC_DIR}} && PYTHONPATH=../.. uv run alembic -c {{ALEMBIC_INI}} upgrade head


# ================================================
# Health Check
# ================================================

health:
	# Health Check für den laufenden Server
	curl -fsS "http://{{HOST}}:{{PORT}}/health" || true

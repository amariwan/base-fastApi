set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true
set export := true

# ----------------------------------------------------------------------
# Konfiguration
# ----------------------------------------------------------------------
APP_MODULE            := "app.asgi:app"
APP_FILE              := "app/asgi.py"
STATIC_DIR            := "static"
MIGRATION_DIR         := "alembic"
ALEMBIC_INI           := "alembic.ini"

HOST                  := env("HOST", "0.0.0.0")
PORT                  := env("PORT", "5000")
FRONTEND_HOST         := env("FRONTEND_HOST", "127.0.0.1")
FRONTEND_PORT         := env("FRONTEND_PORT", "5173")
WORKERS               := env("WORKERS", "2")
TIMEOUT               := env("TIMEOUT", "60")
ENV                   := env("ENV", "development")
UV_LINK_MODE          := env("UV_LINK_MODE", "copy")

BACKEND_URL           := "http://127.0.0.1:" + PORT
FRONTEND_URL          := "http://" + FRONTEND_HOST + ":" + FRONTEND_PORT
DEV_CORS_ORIGINS      := "http://127.0.0.1:5500," + FRONTEND_URL

RELOAD                := if ENV == "development" { "--reload" } else { "" }

UV                    := "uv run --with-editable ."
PYTEST                := "pytest -q"
COV                   := "--cov=app --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=75 --junitxml=report.xml"

FASTAPI_DEV           := "uv run -m fastapi dev " + APP_FILE + " --port " + PORT
UVICORN_DEV           := "uv run uvicorn " + APP_MODULE + " --host " + HOST + " --port " + PORT + " " + RELOAD
GUNICORN_PROD         := "uv run gunicorn " + APP_MODULE + " -k uvicorn.workers.UvicornWorker --bind " + HOST + ":" + PORT
FRONTEND_DEV          := "cd " + STATIC_DIR + " && npx live-server --port=" + FRONTEND_PORT + " --host=" + FRONTEND_HOST + " --no-browser"

# ----------------------------------------------------------------------
# Default
# ----------------------------------------------------------------------
@default:
    just --list

refresh:
    just clean
    just dev

dev:
    {{FASTAPI_DEV}}

dev-uvicorn:
    {{UVICORN_DEV}}

dev-frontend:
    {{FRONTEND_DEV}}

dev-with-frontend:
    @echo "Starting backend ({{BACKEND_URL}}) + frontend ({{FRONTEND_URL}})"
    sh -lc 'DEMO_CORS_ORIGINS="{{DEV_CORS_ORIGINS}}" {{FASTAPI_DEV}} & backend_pid=$!; {{FRONTEND_DEV}}; kill $backend_pid || true'

dev-with-frontend-uvicorn:
    @echo "Starting backend ({{BACKEND_URL}}) + frontend ({{FRONTEND_URL}})"
    sh -lc 'DEMO_CORS_ORIGINS="{{DEV_CORS_ORIGINS}}" {{UVICORN_DEV}} & backend_pid=$!; {{FRONTEND_DEV}}; kill $backend_pid || true'

prod:
    {{GUNICORN_PROD}}

clean:
    rm -rf .venv .tox .cache .pytest_cache .ruff_cache .mypy_cache \
           .coverage coverage.xml dist build *.egg-info pip-wheel-metadata \
           wheelhouse htmlcov node_modules tmp logs __pypackages__
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

fake_token:
    uv run app/utils/development_helpers/create_fake_token.py

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
test *args="":
    {{UV}} {{PYTEST}} {{args}}

test-unit:        (test "-m unit")
test-integration: (test "-m integration")
test-e2e:         (test "-m e2e")
test-all:         test-unit test-integration test-e2e

test-cov:
    {{UV}} {{PYTEST}} -m "unit or e2e" {{COV}}

test-html:
    (test "--cov=src --cov-report=html")

watch marker:
    {{UV}} ptw -- -m {{marker}} --lf --tb=short

# ----------------------------------------------------------------------
# Qualität
# ----------------------------------------------------------------------
lint:
    {{UV}} ruff check .
    {{UV}} ruff format --check .

fmt:
    uvx ruff format .

fix:
    uvx ruff check --fix .
    just fmt

mypy *args="":
    {{UV}} mypy app {{args}}

mypy-report:
    {{UV}} mypy src --txt-report mypy-report

pyright:
    uvx pyright src tests

check: lint mypy pyright test-all
fix-all: fix fmt

update:
    uv sync --upgrade --all-extras

audit:
    {{UV}} pip-audit

# ----------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------
health:
    curl -fSs "http://{{HOST}}:{{PORT}}/health" && echo "OK" || echo "FAIL"

# ----------------------------------------------------------------------
# 🧨 ALEMBIC / DATABASE
# ----------------------------------------------------------------------

# create migration
migrate msg:
    uv run alembic -c {{ALEMBIC_INI}} revision --autogenerate -m "{{msg}}"

# upgrade DB to latest
db-up:
    uv run alembic -c {{ALEMBIC_INI}} upgrade head

# downgrade 1 step
db-down:
    uv run alembic -c {{ALEMBIC_INI}} downgrade -1

# reset DB migrations (DEV ONLY)
db-reset:
    uv run alembic -c {{ALEMBIC_INI}} downgrade base

# full rebuild (nukes migrations state)
db-nuke:
    uv run alembic -c {{ALEMBIC_INI}} downgrade base
    uv run alembic -c {{ALEMBIC_INI}} stamp base
    uv run alembic -c {{ALEMBIC_INI}} upgrade head

# current migration version
db-current:
    uv run alembic -c {{ALEMBIC_INI}} current

# migration history
db-history:
    uv run alembic -c {{ALEMBIC_INI}} history --verbose

# check heads (multiple heads = danger)
db-check:
    uv run alembic -c {{ALEMBIC_INI}} heads

# DB connectivity test
db-ping:
    uv run python -c "from src.app.db.session import engine; print(engine.connect().exec_driver_sql('SELECT 1').scalar())"

# sanity check for migrations
db-validate:
    uv run alembic -c {{ALEMBIC_INI}} current
    uv run alembic -c {{ALEMBIC_INI}} heads

# ----------------------------------------------------------------------
# Docker Compose
# ----------------------------------------------------------------------
compose-up:
    docker compose up --build -d
compose-up-template-manager:
    docker compose up --build -d backend-template-manager

compose-down:
    docker compose down

compose-logs:
    docker compose logs -f

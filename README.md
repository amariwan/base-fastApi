# Base FastAPI Service

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/amariwan/base-fastApi/actions/workflows/ci.yml/badge.svg)](https://github.com/amariwan/base-fastApi/actions)

**Ein modernes, skalierbares und produktionsreifes Boilerplate für Microservices mit FastAPI.**

Dieses Template bietet einen sofort einsatzbereiten Ausgangspunkt für die Entwicklung von **hochperformanten APIs** mit Best Practices in Bezug auf Struktur, Sicherheit, Testing und Deployment.

---

## 🚀 Features

| Feature                     | Beschreibung                                                  |
| --------------------------- | ------------------------------------------------------------- |
| **FastAPI**                 | Moderne, schnelle (High-Performance) Web-Framework für Python |
| **Uvicorn ASGI Server**     | Produktionsreifer Server mit Hot-Reload im Development        |
| **Docker & Docker Compose** | Vollständige Containerisierung mit Multi-Stage-Builds         |
| **Umgebungsvariablen**      | Konfiguration via `.env` und Pydantic Settings                |
| **Modulare Struktur**       | Saubere Trennung von Routern, Services, Models, Schemas       |
| **Authentifizierung**       | JWT-basierte Auth mit Refresh Tokens (optional OAuth2)        |
| **Error Handling**          | Globale Exception-Handler mit strukturierten Responses        |
| **Health Checks**           | `/health`, `/ready`, `/metrics` Endpunkte                     |
| **Scheduler**               | APScheduler für Hintergrundaufgaben                           |
| **Datenbank**               | SQLAlchemy 2.0 + Alembic Migrationen (PostgreSQL-ready)       |
| **Logging**                 | Strukturiertes JSON-Logging mit Correlation IDs               |
| **Monitoring**              | Prometheus Metrics + OpenAPI Docs (`/docs`, `/redoc`)         |
| **Testing**                 | Pytest + HTTPX mit Test-Datenbank                             |
| **CI/CD**                   | GitHub Actions Pipeline (Lint, Test, Build, Security Scan)    |
| **Dokumentation**           | Vollständige Beispiele, Setup-Guides und Architektur          |

---

## 📂 Projektstruktur

```bash
base-fastapi/
├── app/
│   ├── core/             # Konfiguration, Security, Settings
│   ├── db/               # Datenbank-Setup & Session
│   ├── models/           # SQLAlchemy Models
│   ├── schemas/          # Pydantic Schemas
│   ├── services/         # Business Logic
│   ├── utils/            # Hilfsfunktionen
│   └── main.py           # FastAPI App Instanz
├── migrations/           # Alembic Migrationen
├── tests/                # Unit- & Integrationstests
├── scripts/              # Hilfsskripte (z.B. seed, backup)
├── .env.example          # Beispiel-Umgebungsvariablen
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 🛠 Schnellstart

### Voraussetzungen

- Python 3.11+
- Docker & Docker Compose (optional)
- Git

### 1. Repository klonen

```bash
git clone https://github.com/amariwan/base-fastApi.git
cd base-fastApi
```

### 2. Umgebung einrichten

```bash
cp .env.example .env
# Passe .env nach Bedarf an (DB, JWT_SECRET, etc.)
```

### 3. Mit Docker (empfohlen)

```bash
docker compose up --build
```

> API läuft auf: [http://localhost:8000](http://localhost:8000)
> Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Lokal ohne Docker

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

---

## 🧪 Testing

```bash
pytest tests/ -v
```

- Testet API-Endpunkte mit isolierter Test-Datenbank
- Coverage-Report wird generiert

---

## 🔒 Authentifizierung

Standardmäßig ist JWT-Auth implementiert:

```bash
POST /api/v1/auth/login
{
  "username": "admin@example.com",
  "password": "secret"
}
→ Returns access_token + refresh_token
```

Verwende den `access_token` im Header:

```http
Authorization: Bearer <token>
```

---

## 📊 Monitoring & Health Checks

| Endpoint       | Zweck                             |
| -------------- | --------------------------------- |
| `GET /health`  | Einfacher Status-Check            |
| `GET /ready`   | Datenbank & Abhängigkeiten prüfen |
| `GET /metrics` | Prometheus-kompatible Metriken    |

---

## 🚀 CI/CD Pipeline

Die `.github/workflows/ci.yml` enthält:

- Python Linting (`ruff`)
- Type Checking (`mypy`)
- Unit Tests
- Docker Image Build
- Security Scan (`bandit`)
- Dependency Vulnerability Check

---

## 🗄 Datenbank & Migrationen

```bash
# Migration erstellen
alembic revision --autogenerate -m "Add user table"

# Migration anwenden
alembic upgrade head
```

---

## 📦 Deployment

### Docker

```dockerfile
# Multi-Stage Build für minimale Image-Größe
FROM python:3.11-slim
COPY . /app
RUN pip install --no-cache-dir -e .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes (Beispiel)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: base-fastapi
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: your-registry/base-fastapi:latest
        ports:
        - containerPort: 8000
```

---

## 🤝 Contributing

Wir freuen uns über Beiträge!

1. Fork das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/amazing`)
3. Commit deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Push den Branch (`git push origin feature/amazing`)
5. Öffne einen Pull Request

---

## 📄 Lizenz

Dieses Projekt steht unter der **MIT License** – siehe [LICENSE](LICENSE) für Details.

---

## 💡 Inspiration & Quellen

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Tiangolo Full Stack FastAPI Template](https://github.com/tiangolo/full-stack-fastapi-postgresql)

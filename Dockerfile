FROM ghcr.io/astral-sh/uv:alpine AS base

USER root

ARG INSTALL_LIBREOFFICE="false"

RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  tzdata \
  curl \
  fontconfig \
  && if [ "${INSTALL_LIBREOFFICE}" = "true" ]; then \
    apt-get install -y --no-install-recommends \

    && fc-cache -f -v; \
  fi \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# ============================================================================
# BUILDER
# ============================================================================
FROM base AS builder

WORKDIR /build
COPY . .

ARG SERVICE_NAME=""

RUN if [ -n "${SERVICE_NAME}" ]; then \
  services_dir="app/services"; \
  test -d "${services_dir}/${SERVICE_NAME}" || exit 1; \
  find "${services_dir}" -mindepth 1 -maxdepth 1 -type d ! -name "${SERVICE_NAME}" -exec rm -rf {} +; \
  fi

# ============================================================================
# FINAL
# ============================================================================
FROM base AS final

ENV PYTHONPATH=/app

WORKDIR /app

# user setup
RUN getent passwd containeruser >/dev/null 2>&1 || {
  getent group containeruser >/dev/null 2>&1 || groupadd -r containeruser;
  useradd -r -g containeruser containeruser;
}
USER containeruser

# deps (nur einmal!)
COPY --chown=containeruser:containeruser pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# app
COPY --from=builder --chown=containeruser:containeruser /build /app

WORKDIR /app

EXPOSE 5000

CMD ["/app/.venv/bin/uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "5000"]

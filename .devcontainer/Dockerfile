FROM ghcr.io/uvorg/uv:latest

RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN chown -R vscode:vscode /app 2>/dev/null || true

WORKDIR /workspace

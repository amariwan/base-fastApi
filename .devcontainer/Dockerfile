FROM ghcr.io/astral-sh/uv:0.12.3-python3.13-trixie

RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create vscode user for devcontainer remoteUser
RUN groupadd --gid 1000 vscode 2>/dev/null || true \
 && useradd --uid 1000 --gid 1000 -m vscode 2>/dev/null || true \
 && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/vscode \
 && chown -R vscode:vscode /workspace 2>/dev/null || true

USER vscode
WORKDIR /workspace

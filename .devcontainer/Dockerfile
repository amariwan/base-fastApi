# syntax=docker/dockerfile:1.7
# Lean Python dev container: uv + just + Zsh tooling.
# Application sources are bind-mounted at /workspace.

ARG UV_VERSION=0.12.3
FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python3.13-trixie-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=1000

# Debian 13 provides just, starship, and zoxide directly via apt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       git \
       openssh-client \
       passwd \
       zsh \
       just \
       starship \
       zoxide \
       fzf \
       ripgrep \
       fd-find \
       bat \
       jq \
       tree \
       htop \
       less \
    && ln -s /usr/bin/fdfind /usr/local/bin/fd \
    && ln -s /usr/bin/batcat /usr/local/bin/bat \
    && rm -rf /var/lib/apt/lists/*

# Work as a non-root user; do not grant passwordless sudo.
RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" \
       --create-home --shell /usr/bin/zsh "${USERNAME}" \
    && mkdir -p /workspace /home/${USERNAME}/.venvs \
    && chown "${USER_UID}:${USER_GID}" /workspace /home/${USERNAME}/.venvs

USER ${USERNAME}
ENV HOME="/home/${USERNAME}"
ENV ZSH="${HOME}/.oh-my-zsh" \
    UV_CACHE_DIR="${HOME}/.cache/uv" \
    UV_TOOL_BIN_DIR="${HOME}/.local/bin" \
    UV_PROJECT_ENVIRONMENT="${HOME}/.venvs/service" \
    UV_LINK_MODE=copy \
    SHELL=/usr/bin/zsh \
    PATH="${HOME}/.local/bin:${PATH}"

WORKDIR /workspace

# Keep the original Zsh UX, without remote installer scripts.
RUN git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "${ZSH}" \
    && git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git \
       "${ZSH}/custom/plugins/zsh-autosuggestions" \
    && git clone --depth=1 https://github.com/zsh-users/zsh-history-substring-search.git \
       "${ZSH}/custom/plugins/zsh-history-substring-search" \
    && git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git \
       "${ZSH}/custom/plugins/zsh-syntax-highlighting" \
    && mkdir -p "${UV_CACHE_DIR}" "${HOME}/.local/bin"

RUN <<'ZSH_SETUP'
set -eu
cat > "${HOME}/.zshrc" <<'ZSHRC'
export ZSH="$HOME/.oh-my-zsh"
zstyle ':omz:update' mode disabled
ZSH_THEME=""
plugins=(git zsh-autosuggestions zsh-history-substring-search zsh-syntax-highlighting)
source "$ZSH/oh-my-zsh.sh"

eval "$(zoxide init zsh)"
eval "$(starship init zsh)"

alias ll='ls -lah'
alias la='ls -A'
alias l='ls -CF'
ZSHRC
ZSH_SETUP

# Catch missing tools during the image build.
RUN python --version \
    && uv --version \
    && just --version \
    && zsh --version \
    && starship --version \
    && zoxide --version \
    && git --version

CMD ["zsh"]

# =============================================================================
# KarmaCadabra Swarm — OpenClaw Agent Container
# =============================================================================
# Base image with OpenClaw + workspace bootstrapping + em_bridge.
# Each agent container:
#   1. Generates SOUL.md, IDENTITY.md, AGENTS.md, USER.md from env vars
#   2. Installs em_bridge (KC ↔ EM integration library)
#   3. Syncs workspace to/from S3 for persistence
#   4. Starts OpenClaw Gateway + autonomous agent loop
# =============================================================================

FROM node:22-slim

# System deps
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw globally
RUN npm install -g @anthropic-ai/claude-code@latest 2>/dev/null || \
    echo "OpenClaw package not found — will use manual install"

# Create workspace structure
RUN mkdir -p /agent/workspace /agent/scripts /agent/config /agent/em_bridge

# Install em_bridge Python dependencies
RUN python3 -m venv /agent/venv
ENV PATH="/agent/venv/bin:$PATH"
RUN pip install --no-cache-dir \
    httpx \
    pydantic \
    eth-account \
    eth-keys \
    eth-utils \
    mnemonic \
    web3 \
    pytest

# Copy em_bridge package (KC ↔ EM integration)
COPY em_bridge/ /agent/em_bridge/em_bridge/
RUN pip install -e /agent/em_bridge/ 2>/dev/null || \
    echo "em_bridge not a proper package — using PYTHONPATH"
ENV PYTHONPATH="/agent/em_bridge:${PYTHONPATH}"

# Copy bootstrap and entrypoint scripts
COPY templates/ /agent/templates/
COPY scripts/entrypoint.sh /agent/scripts/entrypoint.sh
COPY scripts/bootstrap-workspace.sh /agent/scripts/bootstrap-workspace.sh
COPY scripts/sync-state.sh /agent/scripts/sync-state.sh
COPY scripts/agent-loop.sh /agent/scripts/agent-loop.sh

RUN chmod +x /agent/scripts/*.sh

# Working directory
WORKDIR /agent/workspace

# Health check port
EXPOSE 18789

# Entrypoint
ENTRYPOINT ["/agent/scripts/entrypoint.sh"]

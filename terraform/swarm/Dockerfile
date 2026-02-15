# =============================================================================
# KarmaCadabra Swarm — OpenClaw Agent Container
# =============================================================================
# Base image with OpenClaw + workspace bootstrapping.
# Each agent container:
#   1. Generates SOUL.md, IDENTITY.md, AGENTS.md, USER.md from env vars
#   2. Syncs workspace to/from S3 for persistence
#   3. Starts OpenClaw Gateway
# =============================================================================

FROM node:22-slim

# System deps
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    python3 \
    python3-pip \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw globally
RUN npm install -g @anthropic-ai/claude-code@latest 2>/dev/null || \
    echo "OpenClaw package not found — will use manual install"

# Create workspace structure
RUN mkdir -p /agent/workspace /agent/scripts /agent/config

# Copy bootstrap and entrypoint scripts
COPY templates/ /agent/templates/
COPY scripts/entrypoint.sh /agent/scripts/entrypoint.sh
COPY scripts/bootstrap-workspace.sh /agent/scripts/bootstrap-workspace.sh
COPY scripts/sync-state.sh /agent/scripts/sync-state.sh

RUN chmod +x /agent/scripts/*.sh

# Working directory
WORKDIR /agent/workspace

# Health check port
EXPOSE 18789

# Entrypoint
ENTRYPOINT ["/agent/scripts/entrypoint.sh"]

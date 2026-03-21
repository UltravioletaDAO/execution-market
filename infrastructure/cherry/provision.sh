#!/bin/bash
# Karma Kadabra V2 — Task 3.1: Cherry Servers Bootstrap Script
#
# Provisions an Ubuntu 22.04 VPS with OpenClaw + Node.js 22 + Docker.
# Designed for Cherry Servers cloud_vds_2 (4GB RAM, 2 vCPU).
#
# Usage (run as root on fresh server):
#   curl -fsSL https://raw.githubusercontent.com/.../provision.sh | bash
#   OR
#   scp provision.sh root@<IP>:~ && ssh root@<IP> 'bash provision.sh'

set -euo pipefail

echo "============================================="
echo "  Karma Kadabra V2 — Server Provisioning"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================="

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
echo "[1/7] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
  curl git jq unzip \
  docker.io docker-compose \
  ufw fail2ban \
  build-essential

# ---------------------------------------------------------------------------
# 2. Docker
# ---------------------------------------------------------------------------
echo "[2/7] Configuring Docker..."
systemctl enable docker
systemctl start docker
usermod -aG docker root

# ---------------------------------------------------------------------------
# 3. Node.js 22 + pnpm
# ---------------------------------------------------------------------------
echo "[3/7] Installing Node.js 22..."
if ! command -v node &>/dev/null || [[ "$(node -v)" != v22* ]]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
echo "  Node: $(node -v)"
echo "  npm:  $(npm -v)"

echo "  Installing pnpm..."
npm install -g pnpm@latest
echo "  pnpm: $(pnpm -v)"

# ---------------------------------------------------------------------------
# 4. OpenClaw
# ---------------------------------------------------------------------------
echo "[4/7] Installing OpenClaw..."
npm install -g openclaw@latest
echo "  OpenClaw: $(openclaw --version 2>/dev/null || echo 'installed')"

# Create directory structure
mkdir -p /root/.openclaw/{workspaces,agents,logs}

# ---------------------------------------------------------------------------
# 5. Firewall
# ---------------------------------------------------------------------------
echo "[5/7] Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH
ufw allow 18789/tcp   # OpenClaw Gateway (restrict to VPN in production)
ufw --force enable
echo "  UFW: $(ufw status | head -1)"

# ---------------------------------------------------------------------------
# 6. fail2ban
# ---------------------------------------------------------------------------
echo "[6/7] Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# ---------------------------------------------------------------------------
# 7. Systemd service for OpenClaw
# ---------------------------------------------------------------------------
echo "[7/7] Creating systemd service..."
cat > /etc/systemd/system/openclaw-gateway.service << 'UNIT'
[Unit]
Description=OpenClaw Gateway - Karma Kadabra Swarm
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw
ExecStart=/usr/bin/openclaw gateway
Restart=always
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
# Don't start yet — need openclaw.json + workspaces first
echo "  Service created (not started — run 'systemctl start openclaw-gateway' after config)"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Provisioning complete!"
echo "  Node.js: $(node -v)"
echo "  pnpm:    $(pnpm -v)"
echo "  Docker:  $(docker --version)"
echo ""
echo "  Next steps:"
echo "    1. Deploy openclaw.json to /root/.openclaw/"
echo "    2. Deploy agent workspaces to /root/.openclaw/workspaces/"
echo "    3. Set env vars (ANTHROPIC_API_KEY, etc.)"
echo "    4. systemctl start openclaw-gateway"
echo "    5. openclaw agents list"
echo "============================================="

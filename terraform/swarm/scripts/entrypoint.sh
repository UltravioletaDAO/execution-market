#!/usr/bin/env bash
# =============================================================================
# KarmaCadabra Swarm — Agent Container Entrypoint
# =============================================================================
# 1. Bootstrap workspace (generate SOUL.md, etc.)
# 2. Restore state from S3 (if exists)
# 3. Start OpenClaw Gateway
# 4. Periodically sync state to S3
# =============================================================================

set -euo pipefail

echo "╔══════════════════════════════════════════════════╗"
echo "║  KarmaCadabra Swarm Agent                        ║"
echo "║  Agent: ${AGENT_NAME:-unknown}                   ║"
echo "║  Index: ${AGENT_INDEX:-?}                        ║"
echo "║  Personality: ${SOUL_PERSONALITY:-default}        ║"
echo "╚══════════════════════════════════════════════════╝"

WORKSPACE="/agent/workspace"
S3_PATH="s3://${S3_BUCKET}/${S3_PREFIX}"

# ── Step 1: Bootstrap workspace ──────────────────────────────────────────────
echo "[boot] Bootstrapping workspace for agent: ${AGENT_NAME}"
/agent/scripts/bootstrap-workspace.sh

# ── Step 2: Restore state from S3 ───────────────────────────────────────────
echo "[boot] Restoring state from S3: ${S3_PATH}"
if aws s3 ls "${S3_PATH}/memory/" 2>/dev/null; then
    aws s3 sync "${S3_PATH}/memory/" "${WORKSPACE}/memory/" --quiet || true
    echo "[boot] Restored memory from S3"
else
    echo "[boot] No previous state found — fresh start"
fi

# Restore MEMORY.md if it exists
if aws s3 cp "${S3_PATH}/MEMORY.md" "${WORKSPACE}/MEMORY.md" 2>/dev/null; then
    echo "[boot] Restored MEMORY.md"
fi

# ── Step 3: Generate OpenClaw config ────────────────────────────────────────
echo "[boot] Generating OpenClaw configuration"

cat > "${WORKSPACE}/.openclaw.json" << EOJSON
{
  "model": "${AGENT_MODEL:-anthropic/claude-haiku-4-5}",
  "customApiKeyResponses": {
    "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
  },
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(*)",
      "Write(*)",
      "WebSearch(*)",
      "WebFetch(*)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(shutdown*)",
      "Bash(reboot*)"
    ]
  }
}
EOJSON

# ── Step 4: Start background state sync ─────────────────────────────────────
echo "[boot] Starting background state sync (every 5 minutes)"
(
    while true; do
        sleep 300
        /agent/scripts/sync-state.sh
    done
) &
SYNC_PID=$!

# ── Step 5: Trap signals for graceful shutdown ──────────────────────────────
cleanup() {
    echo "[shutdown] Syncing final state to S3..."
    /agent/scripts/sync-state.sh
    kill ${SYNC_PID} 2>/dev/null || true
    echo "[shutdown] Agent ${AGENT_NAME} stopped gracefully"
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── Step 6: Start Agent Economic Loop (background) ──────────────────────────
echo "[boot] Starting autonomous economic agent loop"
/agent/scripts/agent-loop.sh &
AGENT_LOOP_PID=$!
echo "[boot] Agent loop started (PID: ${AGENT_LOOP_PID})"

# ── Step 7: Start OpenClaw ──────────────────────────────────────────────────
echo "[boot] Starting OpenClaw Gateway for agent: ${AGENT_NAME}"
echo "[boot] Model: ${AGENT_MODEL:-anthropic/claude-haiku-4-5}"
echo "[boot] Workspace: ${WORKSPACE}"

# Start OpenClaw in daemon/headless mode
# The gateway serves on port 18789 and processes scheduled tasks via cron
cd "${WORKSPACE}"

# If openclaw binary exists, use it; otherwise use node directly
if command -v openclaw &> /dev/null; then
    openclaw gateway start --port 18789 &
elif command -v claude &> /dev/null; then
    claude gateway start --port 18789 &
else
    echo "[boot] OpenClaw CLI not found — running in standby mode"
    echo "[boot] Install OpenClaw: npm install -g @anthropic-ai/claude-code"
    # Keep container alive for debugging
    tail -f /dev/null &
fi

GATEWAY_PID=$!
echo "[boot] OpenClaw Gateway started (PID: ${GATEWAY_PID})"

# Wait for either process to exit
wait -n ${GATEWAY_PID} ${AGENT_LOOP_PID} 2>/dev/null || wait ${GATEWAY_PID}

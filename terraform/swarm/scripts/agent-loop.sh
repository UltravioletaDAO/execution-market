#!/usr/bin/env bash
# =============================================================================
# KarmaCadabra Swarm — Autonomous Agent Loop
# =============================================================================
# Runs the em_bridge autonomous agent in a loop alongside OpenClaw.
# Each cycle: discover → bid → execute → create → reflect
#
# This script is the economic brain of the agent. OpenClaw handles
# general intelligence; this handles EM-specific economic behavior.
# =============================================================================

set -euo pipefail

AGENT_NAME="${AGENT_NAME:-unknown}"
SOUL_PERSONALITY="${SOUL_PERSONALITY:-explorer}"
AGENT_INDEX="${AGENT_INDEX:-0}"
WORKSPACE="${WORKSPACE:-/agent/workspace}"
POLL_INTERVAL="${AGENT_POLL_INTERVAL:-300}"
DAILY_LIMIT="${AGENT_DAILY_LIMIT:-10.00}"

echo "[agent-loop] Starting autonomous loop for ${AGENT_NAME} (${SOUL_PERSONALITY})"
echo "[agent-loop] Poll interval: ${POLL_INTERVAL}s, Daily limit: \$${DAILY_LIMIT}"

# Ensure em_bridge is importable
export PYTHONPATH="/agent/em_bridge:${PYTHONPATH:-}"

# Check if we can import em_bridge
if ! python3 -c "from em_bridge.autonomous import AutonomousAgent" 2>/dev/null; then
    echo "[agent-loop] WARNING: em_bridge not importable. Running in OpenClaw-only mode."
    echo "[agent-loop] Agent will rely on HEARTBEAT.md instructions instead."
    exit 0
fi

# Check for mnemonic
if [ -z "${KC_SWARM_MNEMONIC:-}" ]; then
    echo "[agent-loop] ERROR: KC_SWARM_MNEMONIC not set. Cannot derive wallet."
    exit 1
fi

# Run the autonomous agent (continuous mode)
exec python3 -m em_bridge.autonomous \
    --name "${AGENT_NAME}" \
    --archetype "${SOUL_PERSONALITY}" \
    --index "${AGENT_INDEX}" \
    --workspace "${WORKSPACE}" \
    --poll-interval "${POLL_INTERVAL}" \
    --daily-limit "${DAILY_LIMIT}" \
    --verbose

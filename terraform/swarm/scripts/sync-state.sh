#!/usr/bin/env bash
# =============================================================================
# KarmaCadabra Swarm — State Sync to S3
# =============================================================================
# Syncs agent workspace state to S3 for persistence across container restarts.
# Runs every 5 minutes via background loop in entrypoint.sh.
# =============================================================================

set -uo pipefail

WORKSPACE="/agent/workspace"
S3_PATH="s3://${S3_BUCKET}/${S3_PREFIX}"

# Sync memory files
if [ -d "${WORKSPACE}/memory" ]; then
    aws s3 sync "${WORKSPACE}/memory/" "${S3_PATH}/memory/" --quiet 2>/dev/null || \
        echo "[sync] Warning: Failed to sync memory to S3"
fi

# Sync MEMORY.md
if [ -f "${WORKSPACE}/MEMORY.md" ]; then
    aws s3 cp "${WORKSPACE}/MEMORY.md" "${S3_PATH}/MEMORY.md" --quiet 2>/dev/null || \
        echo "[sync] Warning: Failed to sync MEMORY.md to S3"
fi

# Sync any data files the agent created
if [ -d "${WORKSPACE}/data" ]; then
    aws s3 sync "${WORKSPACE}/data/" "${S3_PATH}/data/" --quiet 2>/dev/null || \
        echo "[sync] Warning: Failed to sync data to S3"
fi

echo "[sync] State synced to ${S3_PATH} at $(date -u +%H:%M:%S)"

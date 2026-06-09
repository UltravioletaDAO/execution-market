#!/usr/bin/env bash
# Phase 1.1 — Start Surfpool mainnet fork for local Solana MPP development.
# Doc: docs/runbooks/surfpool-payshell-dev-env.md
#
# Requires:
#   - surfpool CLI installed (see https://github.com/solana-foundation/surfpool)
#   - $SOLANA_FORK_RPC_URL set to a real mainnet RPC (QuikNode preferred per CLAUDE.md)
#
# Ports:
#   - 8899  : Solana JSON-RPC
#   - 8900  : WebSocket
#   - 18488 : Surfpool Studio UI

set -euo pipefail

if [[ -z "${SOLANA_FORK_RPC_URL:-}" ]]; then
  echo "[FATAL] SOLANA_FORK_RPC_URL must be set (mainnet upstream RPC for forking)." >&2
  echo "        Set it from .env.local or AWS Secrets Manager. Do NOT inline a private key." >&2
  exit 1
fi

if ! command -v surfpool >/dev/null 2>&1; then
  echo "[FATAL] surfpool CLI not on PATH. Install per https://github.com/solana-foundation/surfpool" >&2
  exit 1
fi

echo "[INFO] starting surfpool fork against upstream RPC"
echo "[INFO] RPC=http://127.0.0.1:8899  Studio=http://127.0.0.1:18488"

exec surfpool start \
  --rpc-url "$SOLANA_FORK_RPC_URL" \
  --bind 127.0.0.1:8899 \
  --ws-bind 127.0.0.1:8900 \
  --studio-bind 127.0.0.1:18488

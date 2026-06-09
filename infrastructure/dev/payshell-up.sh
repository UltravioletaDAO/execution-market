#!/usr/bin/env bash
# Phase 1.5 — Boot pay.sh proxy pointing at Surfpool localnet + em-stub upstream.
# Doc: docs/runbooks/surfpool-payshell-dev-env.md
#
# Prereqs:
#   - infrastructure/dev/surfpool-up.sh running (Phase 1.1)
#   - services/em-stub/main.py running (Phase 1.6)
#   - .secrets/surfpool-keys/ populated (Phase 1.2)
#   - pay CLI on PATH (Phase 1.3)

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-infrastructure/pay/em-gateway.yml}"
EM_UPSTREAM_URL="${EM_UPSTREAM_URL:-http://127.0.0.1:8090}"
SOLANA_RPC_URL="${SOLANA_RPC_URL:-http://127.0.0.1:8899}"
SOLANA_WS_URL="${SOLANA_WS_URL:-ws://127.0.0.1:8900}"
FACILITATOR_KEYPAIR_PATH="${FACILITATOR_KEYPAIR_PATH:-.secrets/surfpool-keys/treasury.json}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[FATAL] $CONFIG_FILE not found." >&2; exit 1
fi
if [[ ! -f "$FACILITATOR_KEYPAIR_PATH" ]]; then
  echo "[FATAL] $FACILITATOR_KEYPAIR_PATH not found. Run scripts/dev/surfpool-fund.ts first." >&2; exit 1
fi
if ! command -v pay >/dev/null 2>&1; then
  echo "[FATAL] pay CLI not installed. Run infrastructure/dev/payshell-install.sh first." >&2; exit 1
fi

# Resolve splits from env (placeholders in em-gateway.yml). Wallets are *public* addresses
# read from .secrets/surfpool-keys/*.json — pubkey only, no secret material printed.
ROBOT_WALLET=$(node -e "const k=require('./${FACILITATOR_KEYPAIR_PATH//treasury/payee}');const{Keypair}=require('@solana/web3.js');process.stdout.write(Keypair.fromSecretKey(new Uint8Array(k)).publicKey.toBase58())" 2>/dev/null || true)
TREASURY_WALLET=$(node -e "const k=require('./${FACILITATOR_KEYPAIR_PATH}');const{Keypair}=require('@solana/web3.js');process.stdout.write(Keypair.fromSecretKey(new Uint8Array(k)).publicKey.toBase58())" 2>/dev/null || true)

if [[ -z "$ROBOT_WALLET" || -z "$TREASURY_WALLET" ]]; then
  echo "[WARN] could not resolve split addresses via node. Falling back to placeholders." >&2
  echo "       Set ROBOT_WALLET and TREASURY_WALLET env vars before invoking pay server start." >&2
fi

export EM_UPSTREAM_URL SOLANA_RPC_URL SOLANA_WS_URL FACILITATOR_KEYPAIR_PATH ROBOT_WALLET TREASURY_WALLET

echo "[INFO] starting pay server"
echo "[INFO] upstream=$EM_UPSTREAM_URL  rpc=$SOLANA_RPC_URL  proxy=http://127.0.0.1:7081"

exec pay server start --config "$CONFIG_FILE"

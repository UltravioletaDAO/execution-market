#!/usr/bin/env bash
# Phase 1.8 — End-to-end session hello-world via pay.sh.
# Opens a MPP session against /hello, posts 3 vouchers, closes the session.
# Doc: docs/runbooks/surfpool-payshell-dev-env.md
#
# Prereqs (run each in its own terminal):
#   1) infrastructure/dev/surfpool-up.sh     (Phase 1.1)
#   2) services/em-stub/main.py (uvicorn)    (Phase 1.6)
#   3) infrastructure/dev/payshell-up.sh     (Phase 1.5)
# Then in a 4th terminal:
#   4) bash scripts/dev/session-helloworld.sh

set -euo pipefail

PAY_URL="${PAY_URL:-http://127.0.0.1:7081}"
PAYER_KEY="${PAYER_KEY:-.secrets/surfpool-keys/payer.json}"
ENDPOINT="${ENDPOINT:-/hello}"

if [[ ! -f "$PAYER_KEY" ]]; then
  echo "[FATAL] payer keypair not found at $PAYER_KEY" >&2; exit 1
fi
if ! command -v pay >/dev/null 2>&1; then
  echo "[FATAL] pay CLI not installed." >&2; exit 1
fi

echo "[STEP 1] proxy health"
curl -fsS "$PAY_URL/_health" | tee /dev/stderr; echo

echo "[STEP 2] unauthenticated request — expect 402 challenge"
status=$(curl -s -o /tmp/payshell-challenge.json -w "%{http_code}" "$PAY_URL$ENDPOINT")
echo "[INFO] HTTP $status"
[[ "$status" == "402" ]] || { echo "[FATAL] expected 402, got $status" >&2; exit 1; }
cat /tmp/payshell-challenge.json; echo

echo "[STEP 3] open session"
session_id=$(pay client session open \
  --proxy "$PAY_URL" \
  --endpoint "$ENDPOINT" \
  --keypair "$PAYER_KEY" \
  --output json | tee /tmp/payshell-session.json | python3 -c "import sys,json;print(json.load(sys.stdin)['channelId'])")
echo "[OK] channelId=$session_id"

echo "[STEP 4] three vouchers @ 1µUSDC increments"
for i in 1 2 3; do
  pay client voucher sign \
    --proxy "$PAY_URL" \
    --session "$session_id" \
    --keypair "$PAYER_KEY" \
    --increment-uusdc 1 \
    --output json | jq -c '{tick: .voucherCount, accepted: .acceptedCumulativeUsdc}'
done

echo "[STEP 5] close + settle"
pay client session close \
  --proxy "$PAY_URL" \
  --session "$session_id" \
  --keypair "$PAYER_KEY" \
  --output json | tee /tmp/payshell-settle.json | jq '{txHash: .settlementTxHash, splits: .splits}'

echo
echo "[OK] hello-world session complete."
echo "[INFO] inspect on-chain settlement at http://127.0.0.1:18488 (Surfpool Studio)"

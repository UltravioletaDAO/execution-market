#!/usr/bin/env bash
# FIX-P2-03 — local harness demonstrating the difference between the pre-fix
# (value spliced into script text) and post-fix (value passed as an env var)
# patterns. No secrets, no AWS — uses a sentinel file instead of any real
# command.
#
#   PRE-FIX analogue : `eval "TAG=$PAYLOAD"`  -> the $(...) FIRES (vulnerable)
#   POST-FIX pattern : `TAG="$PAYLOAD" bash`  -> the $(...) is INERT (data only)
#                      and the strict-semver regex rejects the crafted tag.
set -uo pipefail
SENTINEL="$(mktemp -d)/pwned"

# --- PRE-FIX simulation: value spliced into script text (vulnerable) ---
PAYLOAD='v1.0.0$(touch '"$SENTINEL"')'
eval "TAG=$PAYLOAD"            # mimics ${{ }} textual substitution into run:
if [ -f "$SENTINEL" ]; then
  echo "PRE-FIX: INJECTION FIRED (expected)"
  rm -f "$SENTINEL"
else
  echo "PRE-FIX: injection did NOT fire — harness broken"; exit 1
fi

# --- POST-FIX simulation: value passed as an env var (inert) ---
TAG="$PAYLOAD" bash -c '
  if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "POST-FIX: rejected non-semver tag (expected)"; exit 0
  fi
  echo "version=${TAG#v}"
'

if [ -f "$SENTINEL" ]; then
  echo "POST-FIX: INJECTION FIRED — FAIL"; exit 1
fi
echo "POST-FIX: no injection, tag rejected — PASS"

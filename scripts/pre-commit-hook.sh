#!/bin/bash
# Pre-commit hook: scan for private keys and secrets in staged files
#
# Install in any repo:
#   cp scripts/pre-commit-hook.sh /path/to/repo/.git/hooks/pre-commit && chmod +x /path/to/repo/.git/hooks/pre-commit
#
# This is a portable version of the Execution Market pre-commit hook.
# It blocks commits containing private key patterns, AWS keys, and API tokens.
# See INC-2026-03-30 in Execution Market CLAUDE.md for incident context.

set -euo pipefail

log() { echo "$@" 2>/dev/null || true; }

log "[PRE-COMMIT] Scanning staged files for secrets..."

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
SECRETS_FOUND=0

if [ -n "$STAGED_FILES" ]; then
    for file in $STAGED_FILES; do
        # Skip binary files and lock files
        case "$file" in
            *.lock|*.png|*.jpg|*.jpeg|*.gif|*.ico|*.woff*|*.ttf|*.eot|*.svg|*.mp4|*.webm|*.pdf)
                continue
                ;;
        esac

        if [ -f "$file" ]; then
            # Pattern 1: Hex private keys (0x + 64 hex chars)
            # Excludes known test/hardhat default keys
            if git diff --cached -- "$file" | grep -Pn '0x[0-9a-fA-F]{64}' | grep -v '^\-' | grep -v 'test.*anvil\|ANVIL\|hardhat.*default\|0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80' > /dev/null 2>&1; then
                log "[BLOCKED] Private key pattern detected in: $file"
                SECRETS_FOUND=$((SECRETS_FOUND + 1))
            fi

            # Pattern 2: AWS access keys, common API tokens
            if git diff --cached -- "$file" | grep -Pn '(AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{48}|ghp_[a-zA-Z0-9]{36})' | grep -v '^\-' > /dev/null 2>&1; then
                log "[BLOCKED] API key/token pattern detected in: $file"
                SECRETS_FOUND=$((SECRETS_FOUND + 1))
            fi
        fi
    done
fi

if [ $SECRETS_FOUND -gt 0 ]; then
    log ""
    log "=========================================================="
    log " COMMIT BLOCKED: $SECRETS_FOUND file(s) contain secrets"
    log "=========================================================="
    log ""
    log " Private keys MUST be read from:"
    log "   - Environment variables (process.env.*, os.environ.*)"
    log "   - AWS Secrets Manager or similar vault"
    log "   - .env.local (gitignored)"
    log ""
    log " NEVER hardcode keys in source files."
    log ""
    exit 1
fi

log "[SECRETS] No private keys detected in staged files."
exit 0

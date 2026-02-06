#!/bin/bash
# Apply Supabase migrations (008-020) to live DB.
#
# SAFETY:
#   - Migrations 001-007: NOT included (initial schema, NOT idempotent)
#   - Migrations 008-020: ALL safe to re-run (use IF NOT EXISTS, CREATE OR REPLACE, etc.)
#
# Prerequisites:
#   - SUPABASE_DB_URL set to the PostgreSQL connection string
#     Format: postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
#   - Or use the Supabase Dashboard SQL editor to paste each migration
#
# Usage:
#   export SUPABASE_DB_URL="postgresql://..."
#   bash scripts/apply-outstanding-migrations.sh
#
# To apply only 015-020 (if you know 008-014 are already applied):
#   bash scripts/apply-outstanding-migrations.sh --from 15

set -euo pipefail

MIGRATIONS_DIR="$(dirname "$0")/../supabase/migrations"
FROM_NUM=8  # Default: start from migration 008

# Parse --from flag
while [[ $# -gt 0 ]]; do
    case $1 in
        --from)
            FROM_NUM="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--from N]  (default: --from 8)"
            exit 1
            ;;
    esac
done

# All idempotent migrations in order (008-020)
ALL_MIGRATIONS=(
    "008_fix_session_linking.sql"
    "009_require_wallet_signature.sql"
    "010_auto_approve_submissions.sql"
    "011_update_executor_profile.sql"
    "012_fix_executor_overload.sql"
    "013_fix_submissions_and_task_release.sql"
    "014_create_platform_config.sql"
    "015_payment_ledger_canonical.sql"
    "016_add_settlement_method.sql"
    "017_orphaned_payment_alerts.sql"
    "018_add_retry_count.sql"
    "019_add_refund_tx_to_tasks.sql"
    "020_tasks_erc8004_agent_id.sql"
    "021_add_reputation_tx_to_submissions.sql"
    "022_evidence_forensic_metadata.sql"
)

if [ -z "${SUPABASE_DB_URL:-}" ]; then
    echo "ERROR: SUPABASE_DB_URL not set."
    echo "Set it to your Supabase PostgreSQL connection string."
    echo ""
    echo "Alternatively, copy-paste each SQL file into the Supabase Dashboard SQL editor:"
    echo ""
    for name in "${ALL_MIGRATIONS[@]}"; do
        num="${name%%_*}"
        if [ "$((10#$num))" -ge "$FROM_NUM" ] && [ -f "$MIGRATIONS_DIR/$name" ]; then
            echo "  - $name"
        fi
    done
    exit 1
fi

echo "Applying migrations (>= $(printf '%03d' "$FROM_NUM")) to: ${SUPABASE_DB_URL%%@*}@..."
echo ""

applied=0
skipped=0
warned=0

for name in "${ALL_MIGRATIONS[@]}"; do
    num="${name%%_*}"
    if [ "$((10#$num))" -lt "$FROM_NUM" ]; then
        continue
    fi

    migration="$MIGRATIONS_DIR/$name"

    if [ ! -f "$migration" ]; then
        echo "SKIP: $name (file not found)"
        ((skipped++))
        continue
    fi

    echo -n "Applying $name... "
    if psql "$SUPABASE_DB_URL" -f "$migration" > /dev/null 2>&1; then
        echo "OK"
        ((applied++))
    else
        echo "WARN (may already be applied, continuing)"
        ((warned++))
    fi
done

echo ""
echo "Done: $applied applied, $warned warnings, $skipped skipped."
echo ""
echo "Verify with:"
echo "  psql \$SUPABASE_DB_URL -c \"SELECT table_name FROM information_schema.tables WHERE table_name IN ('payments', 'escrows', 'platform_config');\""

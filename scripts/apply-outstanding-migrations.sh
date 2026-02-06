#!/bin/bash
# Apply outstanding Supabase migrations (015-020) to live DB.
#
# These migrations use IF NOT EXISTS / ADD COLUMN IF NOT EXISTS patterns,
# so they're safe to re-run on both fresh and existing databases.
#
# Prerequisites:
#   - SUPABASE_DB_URL set to the PostgreSQL connection string
#     Format: postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
#   - Or use the Supabase Dashboard SQL editor to paste each migration
#
# Usage:
#   export SUPABASE_DB_URL="postgresql://..."
#   bash scripts/apply-outstanding-migrations.sh

set -euo pipefail

MIGRATIONS_DIR="$(dirname "$0")/../supabase/migrations"

if [ -z "${SUPABASE_DB_URL:-}" ]; then
    echo "ERROR: SUPABASE_DB_URL not set."
    echo "Set it to your Supabase PostgreSQL connection string."
    echo ""
    echo "Alternatively, copy-paste each SQL file into the Supabase Dashboard SQL editor:"
    echo ""
    for f in "$MIGRATIONS_DIR"/01[5-9]*.sql "$MIGRATIONS_DIR"/02[0-9]*.sql; do
        [ -f "$f" ] && echo "  - $(basename "$f")"
    done
    exit 1
fi

echo "Applying outstanding migrations to: ${SUPABASE_DB_URL%%@*}@..."
echo ""

for migration in \
    "$MIGRATIONS_DIR/015_payment_ledger_canonical.sql" \
    "$MIGRATIONS_DIR/016_add_settlement_method.sql" \
    "$MIGRATIONS_DIR/017_orphaned_payment_alerts.sql" \
    "$MIGRATIONS_DIR/018_add_retry_count.sql" \
    "$MIGRATIONS_DIR/019_add_refund_tx_to_tasks.sql" \
    "$MIGRATIONS_DIR/020_tasks_erc8004_agent_id.sql"; do

    if [ ! -f "$migration" ]; then
        echo "SKIP: $(basename "$migration") (file not found)"
        continue
    fi

    echo -n "Applying $(basename "$migration")... "
    if psql "$SUPABASE_DB_URL" -f "$migration" > /dev/null 2>&1; then
        echo "OK"
    else
        echo "WARN (may already be applied, continuing)"
    fi
done

echo ""
echo "Done. Verify with:"
echo "  psql \$SUPABASE_DB_URL -c \"SELECT table_name FROM information_schema.tables WHERE table_name IN ('payments', 'escrows');\""

#!/bin/bash

# Phase E: Data Audit Script for Execution Market
# This script audits the current state of the database before cleanup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== EXECUTION MARKET DATA AUDIT ===${NC}"
echo "Timestamp: $(date)"
echo

# Get Supabase credentials
echo -e "${YELLOW}Getting database credentials...${NC}"
SUPABASE_DATA=$(aws secretsmanager get-secret-value --secret-id YOUR_SECRET_PATH/supabase --region us-east-2 --query 'SecretString' --output text)
SUPABASE_URL=$(echo "$SUPABASE_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin)['SUPABASE_URL'])")
SERVICE_KEY=$(echo "$SUPABASE_DATA" | python3 -c "import json,sys; print(json.load(sys.stdin)['SUPABASE_SERVICE_ROLE_KEY'])")

# Helper function to make API calls
query() {
  local endpoint="$1"
  curl -s "${SUPABASE_URL}/rest/v1/${endpoint}" \
    -H "apikey: ${SERVICE_KEY}" \
    -H "Authorization: Bearer ${SERVICE_KEY}"
}

echo -e "${GREEN}✓ Database connection established${NC}"
echo

# 1. Count tasks by status
echo -e "${BLUE}1. TASKS BY STATUS${NC}"
echo "Getting task status distribution..."
TASK_COUNTS=$(query "tasks?select=status&limit=1000" | jq -r '.[] | .status' | sort | uniq -c | sort -nr)
echo "$TASK_COUNTS"

# Get total task count
TOTAL_TASKS=$(query "tasks?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total tasks: $TOTAL_TASKS"
echo

# 2. Tasks with no escrow_tx
echo -e "${BLUE}2. TASKS WITHOUT ESCROW_TX${NC}"
NO_ESCROW=$(query "tasks?select=id,title,status,created_at,bounty_usd&escrow_tx=is.null&limit=50")
NO_ESCROW_COUNT=$(echo "$NO_ESCROW" | jq '. | length')
echo "Tasks without escrow_tx: $NO_ESCROW_COUNT"

if [ "$NO_ESCROW_COUNT" -gt 0 ]; then
  echo "Sample tasks without escrow:"
  echo "$NO_ESCROW" | jq -r '.[] | "  \(.id) | \(.status) | $\(.bounty_usd) | \(.title[0:50])..."' | head -10
fi
echo

# 3. Tasks stuck in intermediate states older than 7 days
echo -e "${BLUE}3. STALE INTERMEDIATE STATE TASKS${NC}"
SEVEN_DAYS_AGO=$(date -u -v-7d +"%Y-%m-%dT%H:%M:%SZ")
STALE_TASKS=$(query "tasks?select=id,title,status,created_at,accepted_at,deadline&status=in.(accepted,in_progress)&created_at=lt.${SEVEN_DAYS_AGO}&limit=50")
STALE_COUNT=$(echo "$STALE_TASKS" | jq '. | length')
echo "Tasks in accepted/in_progress older than 7 days: $STALE_COUNT"

if [ "$STALE_COUNT" -gt 0 ]; then
  echo "Stale tasks:"
  echo "$STALE_TASKS" | jq -r '.[] | "  \(.id) | \(.status) | \(.created_at[0:10]) | \(.title[0:40])..."'
fi
echo

# 4. Executors with zero completed tasks
echo -e "${BLUE}4. EXECUTORS WITH ZERO COMPLETED TASKS${NC}"
ZERO_COMPLETED=$(query "executors?select=id,display_name,wallet_address,tasks_completed,created_at&tasks_completed=eq.0&limit=50")
ZERO_COUNT=$(echo "$ZERO_COMPLETED" | jq '. | length')
echo "Executors with 0 completed tasks: $ZERO_COUNT"

if [ "$ZERO_COUNT" -gt 0 ]; then
  echo "Sample executors with 0 completed tasks:"
  echo "$ZERO_COMPLETED" | jq -r '.[] | "  \(.wallet_address[0:10])... | \(.display_name // "No name") | created: \(.created_at[0:10])"' | head -10
fi
echo

# 5. Count feedback_documents
echo -e "${BLUE}5. FEEDBACK DOCUMENTS${NC}"
FEEDBACK_COUNT=$(query "feedback_documents?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total feedback documents: $FEEDBACK_COUNT"

# Break down by feedback_type
FEEDBACK_TYPES=$(query "feedback_documents?select=feedback_type&limit=1000" | jq -r '.[] | .feedback_type' | sort | uniq -c | sort -nr)
if [ -n "$FEEDBACK_TYPES" ]; then
  echo "Feedback by type:"
  echo "$FEEDBACK_TYPES"
fi
echo

# 6. Check activity_feed count
echo -e "${BLUE}6. ACTIVITY FEED${NC}"
ACTIVITY_COUNT=$(query "activity_feed?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total activity feed events: $ACTIVITY_COUNT"

if [ "$ACTIVITY_COUNT" -gt 0 ]; then
  # Break down by event type
  EVENT_TYPES=$(query "activity_feed?select=event_type&limit=1000" | jq -r '.[] | .event_type' | sort | uniq -c | sort -nr)
  echo "Activity by event type:"
  echo "$EVENT_TYPES"
else
  echo -e "${YELLOW}⚠ Activity feed is empty - this is expected for historical data${NC}"
fi
echo

# 7. Additional useful stats
echo -e "${BLUE}7. ADDITIONAL STATISTICS${NC}"

# Escrow data
ESCROW_COUNT=$(query "escrows?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total escrow records: $ESCROW_COUNT"

# Submissions
SUBMISSION_COUNT=$(query "submissions?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total submissions: $SUBMISSION_COUNT"

# Total executors
EXECUTOR_COUNT=$(query "executors?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total executors: $EXECUTOR_COUNT"

# Payment events
PAYMENT_EVENT_COUNT=$(query "payment_events?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Total payment events: $PAYMENT_EVENT_COUNT"

echo
echo -e "${BLUE}=== AUDIT COMPLETE ===${NC}"
echo "Summary of issues found:"

if [ "$NO_ESCROW_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}  • $NO_ESCROW_COUNT tasks without escrow_tx (may need archiving)${NC}"
fi

if [ "$STALE_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}  • $STALE_COUNT tasks stuck in intermediate states > 7 days${NC}"
fi

if [ "$ACTIVITY_COUNT" -eq 0 ]; then
  echo -e "${YELLOW}  • Activity feed is empty (needs backfill)${NC}"
fi

echo -e "${GREEN}  • $TOTAL_TASKS total tasks in system${NC}"
echo -e "${GREEN}  • $EXECUTOR_COUNT total executors${NC}"
echo -e "${GREEN}  • $FEEDBACK_COUNT feedback documents${NC}"

echo
echo "Next steps:"
echo "  1. Review cleanup-stale-data.sql before running"
echo "  2. Run backfill-activity-feed.sh to populate activity feed"
echo "  3. Monitor stale task states for cleanup"
#!/bin/bash

# Phase E: Activity Feed Backfill Script for Execution Market
# 
# This script backfills the activity_feed table with historical data
# based on the current state of tasks and their executors.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== EXECUTION MARKET ACTIVITY FEED BACKFILL ===${NC}"
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

# Helper function to POST data
post() {
  local endpoint="$1"
  local data="$2"
  curl -s -X POST "${SUPABASE_URL}/rest/v1/${endpoint}" \
    -H "apikey: ${SERVICE_KEY}" \
    -H "Authorization: Bearer ${SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d "$data"
}

echo -e "${GREEN}✓ Database connection established${NC}"
echo

# Check current activity_feed count
EXISTING_ACTIVITY_COUNT=$(query "activity_feed?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
echo "Current activity_feed events: $EXISTING_ACTIVITY_COUNT"

if [ "$EXISTING_ACTIVITY_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}⚠ Activity feed already has data. This script will skip existing entries.${NC}"
fi
echo

# Get all tasks with their agent and executor information
echo -e "${BLUE}1. FETCHING TASK DATA${NC}"
echo "Getting all tasks with agent and executor information..."

# First get tasks and their basic info
ALL_TASKS=$(query "tasks?select=id,agent_id,status,title,bounty_usd,category,created_at,accepted_at,completed_at,executor_id&order=created_at.asc&limit=1000")
TASK_COUNT=$(echo "$ALL_TASKS" | jq '. | length')
echo "Found $TASK_COUNT tasks to process"

# Get executor information for the tasks that have executors
echo "Getting executor information..."
EXECUTORS=$(query "executors?select=id,wallet_address,display_name&limit=100")

echo -e "${GREEN}✓ Data fetched${NC}"
echo

# Function to get executor info by ID
get_executor_info() {
  local executor_id="$1"
  if [ -z "$executor_id" ] || [ "$executor_id" = "null" ]; then
    echo "null"
  else
    echo "$EXECUTORS" | jq -r --arg id "$executor_id" '.[] | select(.id == $id) | {wallet: .wallet_address, name: .display_name}'
  fi
}

# Track statistics
CREATED_EVENTS=0
SKIPPED_EVENTS=0
ERROR_EVENTS=0

echo -e "${BLUE}2. GENERATING ACTIVITY FEED EVENTS${NC}"

# Process each task and generate appropriate activity feed events
echo "$ALL_TASKS" | jq -c '.[]' | while read -r task; do
  TASK_ID=$(echo "$task" | jq -r '.id')
  AGENT_ID=$(echo "$task" | jq -r '.agent_id')
  STATUS=$(echo "$task" | jq -r '.status')
  TITLE=$(echo "$task" | jq -r '.title')
  BOUNTY=$(echo "$task" | jq -r '.bounty_usd')
  CATEGORY=$(echo "$task" | jq -r '.category')
  CREATED_AT=$(echo "$task" | jq -r '.created_at')
  ACCEPTED_AT=$(echo "$task" | jq -r '.accepted_at')
  COMPLETED_AT=$(echo "$task" | jq -r '.completed_at')
  EXECUTOR_ID=$(echo "$task" | jq -r '.executor_id')
  
  echo "Processing task: ${TASK_ID:0:8}... ($STATUS)"
  
  # Check if we already have activity feed events for this task
  EXISTING_EVENTS=$(query "activity_feed?task_id=eq.$TASK_ID&select=event_type" | jq '. | length')
  
  if [ "$EXISTING_EVENTS" -gt 0 ]; then
    echo "  → Skipping (already has $EXISTING_EVENTS events)"
    SKIPPED_EVENTS=$((SKIPPED_EVENTS + 1))
    continue
  fi
  
  # Generate task_created event (always for every task)
  TASK_METADATA=$(jq -n \
    --arg title "$TITLE" \
    --arg bounty "$BOUNTY" \
    --arg category "$CATEGORY" \
    '{
      title: $title,
      bounty_usd: ($bounty | tonumber),
      category: $category
    }')
  
  CREATE_EVENT_DATA=$(jq -n \
    --arg event_type "task_created" \
    --arg actor_wallet "$AGENT_ID" \
    --arg actor_name "$AGENT_ID" \
    --arg actor_type "agent" \
    --arg task_id "$TASK_ID" \
    --arg created_at "$CREATED_AT" \
    --argjson metadata "$TASK_METADATA" \
    '{
      event_type: $event_type,
      actor_wallet: $actor_wallet,
      actor_name: $actor_name,
      actor_type: $actor_type,
      task_id: $task_id,
      metadata: $metadata,
      created_at: $created_at
    }')
  
  # Insert task_created event
  RESULT=$(post "activity_feed" "$CREATE_EVENT_DATA")
  if echo "$RESULT" | jq -e '. | type == "array"' > /dev/null 2>&1; then
    echo "  → Created task_created event"
    CREATED_EVENTS=$((CREATED_EVENTS + 1))
  else
    echo "  → Error creating task_created event: $RESULT"
    ERROR_EVENTS=$((ERROR_EVENTS + 1))
  fi
  
  # If task has an executor and appropriate status, create additional events
  if [ "$EXECUTOR_ID" != "null" ] && [ "$EXECUTOR_ID" != "" ]; then
    EXECUTOR_INFO=$(get_executor_info "$EXECUTOR_ID")
    EXECUTOR_WALLET=$(echo "$EXECUTOR_INFO" | jq -r '.wallet // "unknown"')
    EXECUTOR_NAME=$(echo "$EXECUTOR_INFO" | jq -r '.name // "Unknown Executor"')
    
    # Create task_accepted event for accepted/in_progress/submitted/completed/disputed tasks
    if [[ "$STATUS" =~ ^(accepted|in_progress|submitted|completed|disputed)$ ]]; then
      ACCEPT_EVENT_DATA=$(jq -n \
        --arg event_type "task_accepted" \
        --arg actor_wallet "$EXECUTOR_WALLET" \
        --arg actor_name "$EXECUTOR_NAME" \
        --arg actor_type "human" \
        --arg task_id "$TASK_ID" \
        --arg created_at "${ACCEPTED_AT:-$CREATED_AT}" \
        --argjson metadata "$TASK_METADATA" \
        '{
          event_type: $event_type,
          actor_wallet: $actor_wallet,
          actor_name: $actor_name,
          actor_type: $actor_type,
          task_id: $task_id,
          metadata: $metadata,
          created_at: $created_at
        }')
      
      RESULT=$(post "activity_feed" "$ACCEPT_EVENT_DATA")
      if echo "$RESULT" | jq -e '. | type == "array"' > /dev/null 2>&1; then
        echo "  → Created task_accepted event"
        CREATED_EVENTS=$((CREATED_EVENTS + 1))
      else
        echo "  → Error creating task_accepted event: $RESULT"
        ERROR_EVENTS=$((ERROR_EVENTS + 1))
      fi
    fi
    
    # Create task_completed event for completed tasks
    if [ "$STATUS" = "completed" ]; then
      COMPLETE_EVENT_DATA=$(jq -n \
        --arg event_type "task_completed" \
        --arg actor_wallet "$EXECUTOR_WALLET" \
        --arg actor_name "$EXECUTOR_NAME" \
        --arg actor_type "human" \
        --arg task_id "$TASK_ID" \
        --arg created_at "${COMPLETED_AT:-$CREATED_AT}" \
        --argjson metadata "$TASK_METADATA" \
        '{
          event_type: $event_type,
          actor_wallet: $actor_wallet,
          actor_name: $actor_name,
          actor_type: $actor_type,
          task_id: $task_id,
          metadata: $metadata,
          created_at: $created_at
        }')
      
      RESULT=$(post "activity_feed" "$COMPLETE_EVENT_DATA")
      if echo "$RESULT" | jq -e '. | type == "array"' > /dev/null 2>&1; then
        echo "  → Created task_completed event"
        CREATED_EVENTS=$((CREATED_EVENTS + 1))
      else
        echo "  → Error creating task_completed event: $RESULT"
        ERROR_EVENTS=$((ERROR_EVENTS + 1))
      fi
    fi
    
    # Create dispute_opened event for disputed tasks
    if [ "$STATUS" = "disputed" ]; then
      DISPUTE_EVENT_DATA=$(jq -n \
        --arg event_type "dispute_opened" \
        --arg actor_wallet "$AGENT_ID" \
        --arg actor_name "$AGENT_ID" \
        --arg actor_type "agent" \
        --arg target_wallet "$EXECUTOR_WALLET" \
        --arg target_name "$EXECUTOR_NAME" \
        --arg task_id "$TASK_ID" \
        --arg created_at "${COMPLETED_AT:-$CREATED_AT}" \
        --argjson metadata "$TASK_METADATA" \
        '{
          event_type: $event_type,
          actor_wallet: $actor_wallet,
          actor_name: $actor_name,
          actor_type: $actor_type,
          target_wallet: $target_wallet,
          target_name: $target_name,
          task_id: $task_id,
          metadata: $metadata,
          created_at: $created_at
        }')
      
      RESULT=$(post "activity_feed" "$DISPUTE_EVENT_DATA")
      if echo "$RESULT" | jq -e '. | type == "array"' > /dev/null 2>&1; then
        echo "  → Created dispute_opened event"
        CREATED_EVENTS=$((CREATED_EVENTS + 1))
      else
        echo "  → Error creating dispute_opened event: $RESULT"
        ERROR_EVENTS=$((ERROR_EVENTS + 1))
      fi
    fi
  fi
  
  echo "  → Done"
  
  # Add small delay to avoid rate limiting
  sleep 0.1
done

echo
echo -e "${BLUE}3. BACKFILL COMPLETE${NC}"

# Get final count
FINAL_ACTIVITY_COUNT=$(query "activity_feed?select=count" -H "Prefer: count=exact" | jq -r '.[0].count // 0')
NEW_EVENTS=$((FINAL_ACTIVITY_COUNT - EXISTING_ACTIVITY_COUNT))

echo "Results:"
echo -e "${GREEN}  • $NEW_EVENTS new activity feed events created${NC}"
echo -e "${YELLOW}  • $SKIPPED_EVENTS tasks skipped (already had events)${NC}"
if [ "$ERROR_EVENTS" -gt 0 ]; then
  echo -e "${RED}  • $ERROR_EVENTS events failed to create${NC}"
fi

echo
echo "Activity feed summary:"
echo "  Before: $EXISTING_ACTIVITY_COUNT events"
echo "  After:  $FINAL_ACTIVITY_COUNT events"
echo "  Added:  $NEW_EVENTS events"

# Show breakdown by event type
echo
echo "Event breakdown:"
EVENT_TYPES=$(query "activity_feed?select=event_type&limit=2000" | jq -r '.[] | .event_type' | sort | uniq -c | sort -nr)
echo "$EVENT_TYPES"

echo
echo -e "${GREEN}✅ Activity feed backfill completed successfully!${NC}"
echo
echo "Next steps:"
echo "  1. Verify the activity feed data looks correct"
echo "  2. Test the activity feed display in the dashboard"
echo "  3. Set up triggers for future task status changes"
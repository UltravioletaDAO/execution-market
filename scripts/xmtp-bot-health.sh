#!/bin/bash
# XMTP Bot Health Check & Diagnostics
# Usage: bash scripts/xmtp-bot-health.sh

set -euo pipefail

CLUSTER="em-production"
SERVICE="em-xmtp-bot"
REGION="us-east-2"
LOG_GROUP="/ecs/em-xmtp-bot"

echo "=== XMTP Bot Health Check ==="
echo ""

# 1. Service status
echo "--- ECS Service ---"
MSYS_NO_PATHCONV=1 aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --region "$REGION" \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
  --output table 2>/dev/null || echo "ERROR: Could not query ECS service"

echo ""

# 2. Recent task status
echo "--- Recent Tasks ---"
MSYS_NO_PATHCONV=1 aws ecs list-tasks \
  --cluster "$CLUSTER" \
  --service-name "$SERVICE" \
  --region "$REGION" \
  --query 'taskArns' \
  --output text 2>/dev/null | while read -r task_arn; do
    if [ -n "$task_arn" ]; then
      MSYS_NO_PATHCONV=1 aws ecs describe-tasks \
        --cluster "$CLUSTER" \
        --tasks "$task_arn" \
        --region "$REGION" \
        --query 'tasks[0].{Status:lastStatus,Health:healthStatus,Started:startedAt,StopCode:stopCode}' \
        --output table 2>/dev/null
    fi
done

echo ""

# 3. Recent logs (last 20 lines)
echo "--- Recent Logs (last 20) ---"
MSYS_NO_PATHCONV=1 aws logs tail "$LOG_GROUP" \
  --since 30m \
  --region "$REGION" \
  --format short 2>/dev/null | tail -20 || echo "No recent logs"

echo ""

# 4. Error count in last hour
echo "--- Errors (last 1h) ---"
MSYS_NO_PATHCONV=1 aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --start-time $(($(date +%s) * 1000 - 3600000)) \
  --filter-pattern '"error"' \
  --region "$REGION" \
  --query 'events | length(@)' \
  --output text 2>/dev/null || echo "Could not query errors"

echo ""

# 5. CloudWatch alarms
echo "--- Alarm States ---"
MSYS_NO_PATHCONV=1 aws cloudwatch describe-alarms \
  --alarm-name-prefix "em-xmtp-bot" \
  --region "$REGION" \
  --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue}' \
  --output table 2>/dev/null || echo "No alarms configured"

echo ""
echo "=== Done ==="

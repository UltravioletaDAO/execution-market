#!/bin/bash
# verify_post_deploy.sh — Post-deployment verification for swarm endpoints
#
# Run AFTER deploying EM backend with swarm modules.
# Tests that all swarm API endpoints respond correctly in production.
#
# Usage: bash scripts/kk/verify_post_deploy.sh [BASE_URL]

set -uo pipefail

BASE_URL="${1:-https://api.execution.market}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

check_endpoint() {
    local label="$1"
    local method="$2"
    local path="$3"
    local expected_status="${4:-200}"
    local body="${5:-}"

    printf "  %-50s" "$label"

    if [ "$method" = "GET" ]; then
        STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL$path" 2>/dev/null || echo "000")
    else
        STATUS=$(curl -sf -o /dev/null -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$body" "$BASE_URL$path" 2>/dev/null || echo "000")
    fi

    if [ "$STATUS" = "$expected_status" ]; then
        echo -e "${GREEN}✅ $STATUS${NC}"
        ((PASS++))
    else
        echo -e "${RED}❌ Got $STATUS (expected $expected_status)${NC}"
        ((FAIL++))
    fi
}

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  KK V2 Swarm — Post-Deployment Verification          ${NC}"
echo -e "${BLUE}  Target: $BASE_URL                                    ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# ─── Core Health ──────────────────────────────────────
echo -e "${BLUE}▸ Core API Health${NC}"
check_endpoint "Health endpoint" "GET" "/health"
check_endpoint "Auth nonce" "GET" "/api/v1/auth/nonce"
check_endpoint "ERC-8128 info" "GET" "/api/v1/auth/erc8128/info"
echo ""

# ─── Swarm Endpoints ─────────────────────────────────
echo -e "${BLUE}▸ Swarm API Endpoints${NC}"
check_endpoint "Swarm status" "GET" "/api/v1/swarm/status"
check_endpoint "Swarm health" "GET" "/api/v1/swarm/health"
check_endpoint "Swarm agents" "GET" "/api/v1/swarm/agents"
check_endpoint "Swarm dashboard" "GET" "/api/v1/swarm/dashboard"
check_endpoint "Swarm metrics" "GET" "/api/v1/swarm/metrics"
check_endpoint "Swarm events" "GET" "/api/v1/swarm/events"
check_endpoint "Swarm tasks" "GET" "/api/v1/swarm/tasks"
echo ""

# ─── Swarm Write Operations ──────────────────────────
echo -e "${BLUE}▸ Swarm Write Operations (expect 401/403 without auth)${NC}"
check_endpoint "Poll (no auth)" "POST" "/api/v1/swarm/poll" "401" '{}'
check_endpoint "Config (no auth)" "POST" "/api/v1/swarm/config" "401" '{"mode":"passive"}'
echo ""

# ─── Task API ────────────────────────────────────────
echo -e "${BLUE}▸ Task API${NC}"
check_endpoint "List tasks" "GET" "/api/v1/tasks?limit=1"
check_endpoint "Task categories" "GET" "/api/v1/tasks/categories"
echo ""

# ─── Response Content Checks ─────────────────────────
echo -e "${BLUE}▸ Response Content${NC}"
printf "  %-50s" "Health returns JSON with 'status'"
if curl -sf "$BASE_URL/health" 2>/dev/null | grep -q '"status"'; then
    echo -e "${GREEN}✅ OK${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Missing 'status' field${NC}"
    ((FAIL++))
fi

printf "  %-50s" "Swarm status returns JSON"
SWARM_RESP=$(curl -sf "$BASE_URL/api/v1/swarm/status" 2>/dev/null || echo "")
if echo "$SWARM_RESP" | python -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    echo -e "${GREEN}✅ Valid JSON${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ Invalid JSON or no response${NC}"
    ((FAIL++))
fi
echo ""

# ─── Summary ──────────────────────────────────────────
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo -e "${RED}  ❌ DEPLOYMENT ISSUES — $FAIL endpoints not responding correctly${NC}"
    echo ""
    echo "  Troubleshooting:"
    echo "    1. Check ECS task is running: aws ecs describe-services --cluster <YOUR_ECS_CLUSTER> --services <YOUR_ECS_SERVICE> --region us-east-2"
    echo "    2. Check logs: aws logs get-log-events --log-group-name <YOUR_LOG_GROUP> --region us-east-2"
    echo "    3. Check SWARM_ENABLED env var is set in ECS task definition"
    echo ""
    exit 1
else
    echo ""
    echo -e "${GREEN}  ✅ ALL ENDPOINTS RESPONDING — Swarm deployment verified!${NC}"
    echo ""
    exit 0
fi

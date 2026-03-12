#!/bin/bash
# verify_merge_ready.sh — Pre-merge validation for feat/karmacadabra-swarm
#
# Runs all checks needed before merging the swarm branch to main.
# Exit 0 = safe to merge. Non-zero = fix issues first.
#
# Usage: bash scripts/kk/verify_merge_ready.sh

set -uo pipefail
# NOTE: Not using -e because individual checks should continue on failure

# Fix broken GITHUB_TOKEN if present
if [ -n "${GITHUB_TOKEN:-}" ]; then
    unset GITHUB_TOKEN
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
    local label="$1"
    shift
    printf "  %-45s" "$label"
    if eval "$@" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAIL++))
    fi
}

warn_check() {
    local label="$1"
    shift
    printf "  %-45s" "$label"
    if eval "$@" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠️  WARN${NC}"
        ((WARN++))
    fi
}

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  KK V2 Swarm — Pre-Merge Validation                  ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

cd "$(dirname "$0")/../.."

# ─── Git Status ───────────────────────────────────────
echo -e "${BLUE}▸ Git Status${NC}"
check "On swarm branch" "git branch --show-current | grep -q 'feat/karmacadabra-swarm'"
# Allow the verify script itself to be modified (it's in scripts/)
check "Working tree clean (excl. scripts/)" "test -z \"\$(git status --porcelain -- ':!scripts/')\""
warn_check "Up to date with remote" "git fetch origin feat/karmacadabra-swarm 2>/dev/null && git diff --quiet HEAD origin/feat/karmacadabra-swarm 2>/dev/null"
warn_check "Can push to remote" "git push --dry-run origin feat/karmacadabra-swarm 2>/dev/null"
echo ""

# ─── Swarm Module Integrity ──────────────────────────
echo -e "${BLUE}▸ Swarm Modules (10 expected)${NC}"
SWARM_DIR="mcp_server/swarm"
check "__init__.py exists" "test -f $SWARM_DIR/__init__.py"
check "coordinator.py exists" "test -f $SWARM_DIR/coordinator.py"
check "orchestrator.py exists" "test -f $SWARM_DIR/orchestrator.py"
check "event_listener.py exists" "test -f $SWARM_DIR/event_listener.py"
check "evidence_parser.py exists" "test -f $SWARM_DIR/evidence_parser.py"
check "reputation_bridge.py exists" "test -f $SWARM_DIR/reputation_bridge.py"
check "lifecycle_manager.py exists" "test -f $SWARM_DIR/lifecycle_manager.py"
check "autojob_client.py exists" "test -f $SWARM_DIR/autojob_client.py"
check "heartbeat_handler.py exists" "test -f $SWARM_DIR/heartbeat_handler.py"
check "mcp_tools.py exists" "test -f $SWARM_DIR/mcp_tools.py"

SWARM_LOC=$(wc -l $SWARM_DIR/*.py 2>/dev/null | tail -1 | awk '{print $1}')
echo -e "  Swarm LOC: ${GREEN}${SWARM_LOC}${NC}"
echo ""

# ─── API Routes ───────────────────────────────────────
echo -e "${BLUE}▸ API Route Registration${NC}"
check "swarm.py in api/" "test -f mcp_server/api/swarm.py"
check "Registered in main.py" "grep -q 'swarm_router' mcp_server/main.py"
check "ACTIVATION.md exists" "test -f $SWARM_DIR/ACTIVATION.md"
check "ARCHITECTURE.md exists" "test -f $SWARM_DIR/ARCHITECTURE.md"
check "OPERATIONS.md exists" "test -f $SWARM_DIR/OPERATIONS.md"
echo ""

# ─── Tests ────────────────────────────────────────────
echo -e "${BLUE}▸ Test Suites${NC}"

# Swarm tests
printf "  %-45s" "Swarm tests (mcp_server/tests/test_swarm*)"
SWARM_RESULT=$(python3 -m pytest mcp_server/tests/test_swarm*.py -q --tb=no 2>&1 | tail -1)
SWARM_PASSED=$(echo "$SWARM_RESULT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
if echo "$SWARM_RESULT" | grep -q "passed" && ! echo "$SWARM_RESULT" | grep -q "failed"; then
    echo -e "${GREEN}✅ $SWARM_PASSED passed${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ $SWARM_RESULT${NC}"
    ((FAIL++))
fi

# Core EM tests
printf "  %-45s" "Core EM tests (mcp_server/tests/)"
CORE_RESULT=$(python3 -m pytest mcp_server/tests/ -q --tb=no 2>&1 | tail -1)
CORE_PASSED=$(echo "$CORE_RESULT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
if echo "$CORE_RESULT" | grep -q "passed" && ! echo "$CORE_RESULT" | grep -qw "failed"; then
    echo -e "${GREEN}✅ $CORE_PASSED passed${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ $CORE_RESULT${NC}"
    ((FAIL++))
fi

# Root tests
printf "  %-45s" "Root tests (tests/)"
ROOT_RESULT=$(python3 -m pytest tests/ -q --tb=no 2>&1 | tail -1)
ROOT_PASSED=$(echo "$ROOT_RESULT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
if echo "$ROOT_RESULT" | grep -q "passed" && ! echo "$ROOT_RESULT" | grep -q "failed"; then
    echo -e "${GREEN}✅ $ROOT_PASSED passed${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ $ROOT_RESULT${NC}"
    ((FAIL++))
fi

TOTAL_TESTS=$((SWARM_PASSED + CORE_PASSED + ROOT_PASSED))
echo -e "  Total tests: ${GREEN}${TOTAL_TESTS}${NC}"
echo ""

# ─── Live API Health ──────────────────────────────────
echo -e "${BLUE}▸ Production API Health${NC}"
warn_check "EM API healthy" "curl -sf https://api.execution.market/health | grep -q healthy"
warn_check "ERC-8128 nonce endpoint" "curl -sf https://api.execution.market/api/v1/auth/nonce | grep -q nonce"
echo ""

# ─── Import Check ─────────────────────────────────────
echo -e "${BLUE}▸ Python Import Verification${NC}"
check "Can import swarm package" "python3 -c 'import sys; sys.path.insert(0, \"mcp_server\"); from swarm import SwarmCoordinator, SwarmOrchestrator'"
check "Can import API routes" "python3 -c 'import sys; sys.path.insert(0, \"mcp_server\"); from api.swarm import router'"
check "Can import MCP tools" "python3 -c 'import sys; sys.path.insert(0, \"mcp_server\"); from swarm.mcp_tools import register_swarm_tools'"
echo ""

# ─── Summary ──────────────────────────────────────────
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}  ${YELLOW}Warnings: $WARN${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo -e "${RED}  ❌ NOT READY TO MERGE — Fix $FAIL failing checks${NC}"
    echo ""
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}  ⚠️  MERGE POSSIBLE — $WARN warnings (review before merging)${NC}"
    echo ""
    exit 0
else
    echo ""
    echo -e "${GREEN}  ✅ ALL CHECKS PASSED — Ready to merge!${NC}"
    echo ""
    echo "  Next steps:"
    echo "    git checkout main"
    echo "    git merge feat/karmacadabra-swarm --no-ff -m 'feat: KK V2 Swarm — 10 modules, ${TOTAL_TESTS}+ tests'"
    echo "    git push origin main"
    echo "    bash scripts/deploy-manual.sh"
    echo ""
    exit 0
fi

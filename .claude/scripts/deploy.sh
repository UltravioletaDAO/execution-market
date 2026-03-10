#!/bin/bash
# =============================================================================
# deploy.sh — Unified Execution Market Deployment
# =============================================================================
#
# Builds, tags with immutable git SHA, pushes to ECR, deploys to ECS,
# and runs post-deploy health checks.
#
# Usage:
#   ./deploy.sh                      # Deploy all services
#   ./deploy.sh --dashboard          # Dashboard only
#   ./deploy.sh --mcp                # MCP server only
#   ./deploy.sh --dry-run            # Show what would happen
#   ./deploy.sh --skip-build         # Push existing images
#   ./deploy.sh --skip-health-check  # Skip post-deploy verification
#
# Environment overrides:
#   AWS_ACCOUNT_ID  (default: YOUR_AWS_ACCOUNT_ID)
#   AWS_REGION      (default: us-east-2)
#   IMAGE_TAG       (default: git SHA)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Config ──────────────────────────────────────────────────────────────────
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_AWS_ACCOUNT_ID}"
AWS_REGION="${AWS_REGION:-us-east-2}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECS_CLUSTER="em-production-cluster"

# Git-based immutable tag
GIT_SHA="$(cd "$PROJECT_ROOT" && git rev-parse --short=8 HEAD)"
GIT_BRANCH="$(cd "$PROJECT_ROOT" && git branch --show-current)"
IMAGE_TAG="${IMAGE_TAG:-${GIT_SHA}}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Service definitions
declare -A SERVICES=(
  [dashboard]="em-production-dashboard"
  [mcp]="em-production-mcp-server"
)
declare -A DOCKERFILES=(
  [dashboard]="dashboard/Dockerfile"
  [mcp]="mcp_server/Dockerfile"
)
declare -A BUILD_CONTEXTS=(
  [dashboard]="./dashboard"
  [mcp]="./mcp_server"
)
declare -A BUILD_ARGS=(
  [dashboard]="--build-arg VITE_SUPABASE_URL=${SUPABASE_URL} --build-arg VITE_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY} --build-arg VITE_EVIDENCE_API_URL=${EVIDENCE_API_URL} --build-arg VITE_DYNAMIC_ENVIRONMENT_ID=${DYNAMIC_ENVIRONMENT_ID}"
  [mcp]=""
)

# Health check URLs
API_URL="https://api.execution.market"
DASHBOARD_URL="https://execution.market"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Options ─────────────────────────────────────────────────────────────────
DRY_RUN=false
SKIP_BUILD=false
SKIP_HEALTH=false
DEPLOY_DASHBOARD=false
DEPLOY_MCP=false
DEPLOY_ALL=true

for arg in "$@"; do
  case $arg in
    --dry-run)           DRY_RUN=true ;;
    --skip-build)        SKIP_BUILD=true ;;
    --skip-health-check) SKIP_HEALTH=true ;;
    --dashboard)         DEPLOY_DASHBOARD=true; DEPLOY_ALL=false ;;
    --mcp)               DEPLOY_MCP=true; DEPLOY_ALL=false ;;
    --help|-h)
      sed -n '2,/^$/p' "$0" | sed 's/^# //' | sed 's/^#//'
      exit 0 ;;
  esac
done

# Determine which services to deploy
TARGETS=()
if [ "$DEPLOY_ALL" = true ]; then
  TARGETS=(dashboard mcp)
else
  [ "$DEPLOY_DASHBOARD" = true ] && TARGETS+=(dashboard)
  [ "$DEPLOY_MCP" = true ] && TARGETS+=(mcp)
fi

# ── Helpers ─────────────────────────────────────────────────────────────────
header() {
  echo -e "\n${BLUE}━━━ $1 ━━━${NC}\n"
}

run() {
  echo -e "  ${CYAN}> $*${NC}"
  if [ "$DRY_RUN" = true ]; then
    echo -e "  ${YELLOW}[DRY-RUN]${NC}"
    return 0
  fi
  "$@"
}

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }

# ── Pre-flight ──────────────────────────────────────────────────────────────
header "Execution Market Deploy"

echo "  Commit:    ${GIT_SHA} (${GIT_BRANCH})"
echo "  Tag:       ${IMAGE_TAG}"
echo "  Timestamp: ${TIMESTAMP}"
echo "  Account:   ${AWS_ACCOUNT_ID}"
echo "  Region:    ${AWS_REGION}"
echo "  Targets:   ${TARGETS[*]}"
[ "$DRY_RUN" = true ] && echo -e "  ${YELLOW}DRY-RUN MODE${NC}"
echo ""

# Check for uncommitted changes
if [ -n "$(cd "$PROJECT_ROOT" && git status --porcelain)" ]; then
  warn "Uncommitted changes detected — deploy will use committed code only"
fi

# ── ECR Login ───────────────────────────────────────────────────────────────
header "ECR Login"

if [ "$DRY_RUN" = false ]; then
  aws ecr get-login-password --region "$AWS_REGION" \
    | docker login --username AWS --password-stdin "$ECR_URI" 2>/dev/null
  ok "Authenticated to ECR"
else
  echo -e "  ${YELLOW}[DRY-RUN] Skip ECR login${NC}"
fi

# ── Build + Push ────────────────────────────────────────────────────────────
for svc in "${TARGETS[@]}"; do
  ECR_REPO="${SERVICES[$svc]}"
  FULL_IMAGE="${ECR_URI}/${ECR_REPO}"

  header "Deploy: ${svc}"

  # Build
  if [ "$SKIP_BUILD" = false ]; then
    echo "  Building ${svc}..."
    cd "$PROJECT_ROOT"

    BUILD_CMD="docker build --no-cache -f ${DOCKERFILES[$svc]} -t ${ECR_REPO}:${IMAGE_TAG}"
    # Add build args if any
    if [ -n "${BUILD_ARGS[$svc]}" ]; then
      BUILD_CMD="${BUILD_CMD} ${BUILD_ARGS[$svc]}"
    fi
    BUILD_CMD="${BUILD_CMD} ${BUILD_CONTEXTS[$svc]}"

    if [ "$DRY_RUN" = true ]; then
      echo -e "  ${CYAN}> ${BUILD_CMD}${NC}"
      echo -e "  ${YELLOW}[DRY-RUN]${NC}"
    else
      eval "${BUILD_CMD}" > /dev/null 2>&1
      ok "Built ${svc} image"
    fi
  else
    warn "Skipping build (--skip-build)"
  fi

  # Tag with both SHA and latest
  run docker tag "${ECR_REPO}:${IMAGE_TAG}" "${FULL_IMAGE}:${IMAGE_TAG}" 2>/dev/null || true
  run docker tag "${ECR_REPO}:${IMAGE_TAG}" "${FULL_IMAGE}:latest" 2>/dev/null || true

  # Push
  if [ "$DRY_RUN" = false ]; then
    echo "  Pushing ${svc} (${IMAGE_TAG} + latest)..."
    docker push "${FULL_IMAGE}:${IMAGE_TAG}" > /dev/null 2>&1
    docker push "${FULL_IMAGE}:latest" > /dev/null 2>&1
    ok "Pushed ${svc} to ECR"
  fi

  # Deploy to ECS
  if [ "$DRY_RUN" = false ]; then
    aws ecs update-service \
      --cluster "$ECS_CLUSTER" \
      --service "$ECR_REPO" \
      --force-new-deployment \
      --region "$AWS_REGION" > /dev/null 2>&1
    ok "ECS deployment initiated for ${svc}"
  fi
done

# ── Post-Deploy Health Check ────────────────────────────────────────────────
if [ "$SKIP_HEALTH" = false ] && [ "$DRY_RUN" = false ]; then
  header "Post-Deploy Health Check"

  echo "  Waiting 30s for ECS to stabilize..."
  sleep 30

  HEALTH_PASS=0
  HEALTH_FAIL=0

  # Check API health
  if curl -sf "${API_URL}/health" > /dev/null 2>&1; then
    ok "API health"
    ((HEALTH_PASS++))
  else
    fail "API health"
    ((HEALTH_FAIL++))
  fi

  # Check sanity
  SANITY=$(curl -sf "${API_URL}/health/sanity" 2>/dev/null || echo '{}')
  SANITY_STATUS=$(echo "$SANITY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")
  if [ "$SANITY_STATUS" = "ok" ] || [ "$SANITY_STATUS" = "warnings" ]; then
    ok "Sanity check (${SANITY_STATUS})"
    ((HEALTH_PASS++))
  else
    fail "Sanity check (${SANITY_STATUS})"
    ((HEALTH_FAIL++))
  fi

  # Check version
  VERSION=$(curl -sf "${API_URL}/health/version" 2>/dev/null || echo '{}')
  DEPLOYED_COMMIT=$(echo "$VERSION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('git_commit','unknown'))" 2>/dev/null || echo "unknown")
  echo -e "  Deployed commit: ${DEPLOYED_COMMIT}"

  # Check dashboard
  if curl -sf "${DASHBOARD_URL}" > /dev/null 2>&1; then
    ok "Dashboard reachable"
    ((HEALTH_PASS++))
  else
    fail "Dashboard unreachable"
    ((HEALTH_FAIL++))
  fi

  # Check routes
  ROUTE_COUNT=$(curl -sf "${API_URL}/health/routes" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
  if [ "$ROUTE_COUNT" -gt 50 ]; then
    ok "Route parity (${ROUTE_COUNT} routes)"
    ((HEALTH_PASS++))
  else
    warn "Route count low (${ROUTE_COUNT})"
    ((HEALTH_FAIL++))
  fi

  echo ""
  echo -e "  Health: ${GREEN}${HEALTH_PASS} passed${NC}, ${RED}${HEALTH_FAIL} failed${NC}"

  if [ "$HEALTH_FAIL" -gt 0 ]; then
    warn "Some health checks failed — monitor closely"
  fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────
header "Deploy Complete"

echo "  Commit:  ${GIT_SHA}"
echo "  Tag:     ${IMAGE_TAG}"
echo "  Services: ${TARGETS[*]}"
echo ""
echo "  Monitor:"
echo "    aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${SERVICES[dashboard]} ${SERVICES[mcp]} --region ${AWS_REGION} --query 'services[].{name:serviceName,desired:desiredCount,running:runningCount,status:status}'"
echo ""
echo "  Rollback (if needed):"
echo "    aws ecs update-service --cluster ${ECS_CLUSTER} --service <SERVICE> --task-definition <PREVIOUS_TASK_DEF> --region ${AWS_REGION}"

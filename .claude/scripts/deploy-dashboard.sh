#!/bin/bash
# =============================================================================
# deploy-dashboard.sh - Deploy Dashboard to AWS ECS via ECR
# =============================================================================
# Usage: ./deploy-dashboard.sh [--dry-run] [--skip-build] [--skip-push]
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed and running
#   - Access to ECR repository and ECS cluster
#
# Environment variables (can override defaults):
#   AWS_ACCOUNT_ID   - AWS account ID (default: <YOUR_ACCOUNT_ID>)
#   AWS_REGION       - AWS region (default: us-east-2)
#   ECR_REPO         - ECR repository name (default: em-production-dashboard)
#   ECS_CLUSTER      - ECS cluster name (default: em-production-cluster)
#   ECS_SERVICE      - ECS service name (default: em-production-dashboard)
#   IMAGE_TAG        - Docker image tag (default: latest)
# =============================================================================

set -e  # Exit on first error

# Project root (relative to this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# =============================================================================
# Configuration - Update these for your environment
# =============================================================================
# IMPORTANT: Replace <YOUR_ACCOUNT_ID> with your actual AWS account ID
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_AWS_ACCOUNT_ID}"
AWS_REGION="${AWS_REGION:-us-east-2}"
ECR_REPO="${ECR_REPO:-em-production-dashboard}"
ECS_CLUSTER="${ECS_CLUSTER:-em-production-cluster}"
ECS_SERVICE="${ECS_SERVICE:-em-production-dashboard}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Derived values
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE="${ECR_URI}/${ECR_REPO}:${IMAGE_TAG}"

# Options
DRY_RUN=false
SKIP_BUILD=false
SKIP_PUSH=false

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

run_cmd() {
    local desc="$1"
    shift

    echo -e "${CYAN}> $*${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN] Skipped${NC}"
        return 0
    fi

    if "$@"; then
        echo -e "${GREEN}[OK]${NC} $desc"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $desc"
        return 1
    fi
}

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)    DRY_RUN=true ;;
        --skip-build) SKIP_BUILD=true ;;
        --skip-push)  SKIP_PUSH=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--skip-build] [--skip-push]"
            echo ""
            echo "Options:"
            echo "  --dry-run     Show commands without executing"
            echo "  --skip-build  Skip Docker build step"
            echo "  --skip-push   Skip ECR push step"
            echo ""
            echo "Environment variables:"
            echo "  AWS_ACCOUNT_ID   AWS account ID (current: $AWS_ACCOUNT_ID)"
            echo "  AWS_REGION       AWS region (current: $AWS_REGION)"
            echo "  ECR_REPO         ECR repository (current: $ECR_REPO)"
            echo "  ECS_CLUSTER      ECS cluster (current: $ECS_CLUSTER)"
            echo "  ECS_SERVICE      ECS service (current: $ECS_SERVICE)"
            echo "  IMAGE_TAG        Image tag (current: $IMAGE_TAG)"
            exit 0
            ;;
    esac
done

# =============================================================================
# Validation
# =============================================================================
print_header "Deploy Dashboard to ECS"

echo "Configuration:"
echo "  AWS Account:  $AWS_ACCOUNT_ID"
echo "  Region:       $AWS_REGION"
echo "  ECR Repo:     $ECR_REPO"
echo "  ECS Cluster:  $ECS_CLUSTER"
echo "  ECS Service:  $ECS_SERVICE"
echo "  Image:        $FULL_IMAGE"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY-RUN MODE - No changes will be made${NC}\n"
fi

# Check for placeholder
if [ "$AWS_ACCOUNT_ID" = "<YOUR_ACCOUNT_ID>" ]; then
    echo -e "${RED}ERROR: AWS_ACCOUNT_ID is not set${NC}"
    echo "Set it via environment variable or edit this script:"
    echo "  export AWS_ACCOUNT_ID=123456789012"
    echo "  $0"
    exit 1
fi

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI not found. Install it first.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} AWS CLI"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found. Install it first.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured or expired.${NC}"
    echo "Run: aws configure"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} AWS credentials"

# Verify dashboard directory exists
if [ ! -d "$PROJECT_ROOT/dashboard" ]; then
    echo -e "${RED}ERROR: Dashboard directory not found at $PROJECT_ROOT/dashboard${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Dashboard directory"

# =============================================================================
# Step 1: ECR Login
# =============================================================================
print_header "Step 1/4: ECR Login"

run_cmd "ECR authentication" \
    aws ecr get-login-password --region "$AWS_REGION" \
    | docker login --username AWS --password-stdin "$ECR_URI"

# =============================================================================
# Step 2: Docker Build
# =============================================================================
print_header "Step 2/4: Docker Build"

if [ "$SKIP_BUILD" = true ]; then
    echo -e "${YELLOW}[SKIP] Docker build (--skip-build)${NC}"
else
    cd "$PROJECT_ROOT"

    # Build with no cache to ensure fresh build
    run_cmd "Docker build" \
        docker build \
            --no-cache \
            -f dashboard/Dockerfile \
            -t "${ECR_REPO}:${IMAGE_TAG}" \
            ./dashboard

    # Tag for ECR
    run_cmd "Docker tag" \
        docker tag "${ECR_REPO}:${IMAGE_TAG}" "$FULL_IMAGE"
fi

# =============================================================================
# Step 3: Push to ECR
# =============================================================================
print_header "Step 3/4: Push to ECR"

if [ "$SKIP_PUSH" = true ]; then
    echo -e "${YELLOW}[SKIP] ECR push (--skip-push)${NC}"
else
    run_cmd "Docker push to ECR" \
        docker push "$FULL_IMAGE"
fi

# =============================================================================
# Step 4: ECS Deployment
# =============================================================================
print_header "Step 4/4: ECS Deployment"

run_cmd "Force new ECS deployment" \
    aws ecs update-service \
        --cluster "$ECS_CLUSTER" \
        --service "$ECS_SERVICE" \
        --force-new-deployment \
        --region "$AWS_REGION"

# =============================================================================
# Post-deployment
# =============================================================================
print_header "Deployment Initiated"

echo -e "${GREEN}Dashboard deployment has been initiated!${NC}"
echo ""
echo "Monitor the deployment:"
echo -e "  ${CYAN}aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION --query 'services[0].deployments'${NC}"
echo ""
echo "View logs:"
echo -e "  ${CYAN}aws logs tail /ecs/$ECS_SERVICE --follow --region $AWS_REGION${NC}"
echo ""
echo "Or check the AWS Console:"
echo -e "  ${CYAN}https://${AWS_REGION}.console.aws.amazon.com/ecs/v2/clusters/${ECS_CLUSTER}/services/${ECS_SERVICE}${NC}"

# Wait for deployment (optional, controlled by flag)
if [ "$DRY_RUN" = false ]; then
    echo ""
    read -p "Wait for deployment to complete? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Waiting for deployment to stabilize (this may take a few minutes)..."
        if aws ecs wait services-stable \
            --cluster "$ECS_CLUSTER" \
            --services "$ECS_SERVICE" \
            --region "$AWS_REGION"; then
            echo -e "\n${GREEN}Deployment completed successfully!${NC}"
        else
            echo -e "\n${RED}Deployment may have issues. Check the AWS Console.${NC}"
            exit 1
        fi
    fi
fi

echo -e "\n${GREEN}Done!${NC}"

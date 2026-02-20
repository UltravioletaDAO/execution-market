#!/usr/bin/env bash
# =============================================================================
# KarmaCadabra Swarm — Sequential Deployment Script
# =============================================================================
# Deploys OpenClaw agents sequentially on AWS ECS Fargate.
#
# Usage:
#   ./deploy.sh --api-key sk-ant-xxx                    # Deploy 5 agents (default)
#   ./deploy.sh --api-key sk-ant-xxx --agents 55        # Deploy 55 agents
#   ./deploy.sh --api-key sk-ant-xxx --agents 200 --batch 10  # Deploy in batches of 10
#   ./deploy.sh --destroy                                # Tear down everything
#   ./deploy.sh --status                                 # Check deployment status
#
# The ONLY required input is the Anthropic API key.
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(dirname "${SCRIPT_DIR}")"
DEFAULT_AGENTS=5
DEFAULT_BATCH=5
DEFAULT_REGION="us-east-2"
DEFAULT_MODEL="anthropic/claude-haiku-4-5"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# ── Functions ────────────────────────────────────────────────────────────────
usage() {
    cat << EOF
╔══════════════════════════════════════════════════════════════╗
║              KarmaCadabra Swarm Deployer 🪄                 ║
╚══════════════════════════════════════════════════════════════╝

Usage: $(basename "$0") [OPTIONS]

Required (for deploy):
  --api-key KEY         Anthropic API key (sk-ant-...)

Options:
  --agents N            Number of agents to deploy (default: ${DEFAULT_AGENTS})
  --batch N             Deploy in batches of N (default: ${DEFAULT_BATCH})
  --region REGION       AWS region (default: ${DEFAULT_REGION})
  --model MODEL         LLM model (default: ${DEFAULT_MODEL})
  --no-spot             Use on-demand Fargate (no Spot, 3x more expensive)
  --destroy             Tear down all infrastructure
  --status              Show deployment status
  --plan                Show plan without applying
  --build               Build and push Docker image only
  -h, --help            Show this help

Examples:
  # Phase 0: 5 agents (~\$104/mo with Spot)
  $(basename "$0") --api-key sk-ant-xxx

  # Phase 1: 55 agents, deploy 5 at a time
  $(basename "$0") --api-key sk-ant-xxx --agents 55 --batch 5

  # Phase 2: 200 agents, deploy 10 at a time
  $(basename "$0") --api-key sk-ant-xxx --agents 200 --batch 10

  # Check what's running
  $(basename "$0") --status

  # Tear it all down
  $(basename "$0") --destroy
EOF
}

log() { echo -e "${BLUE}[deploy]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*" >&2; }

check_prerequisites() {
    local missing=()

    command -v terraform &>/dev/null || missing+=("terraform")
    command -v aws &>/dev/null || missing+=("aws-cli")
    command -v docker &>/dev/null || missing+=("docker")
    command -v jq &>/dev/null || missing+=("jq")

    if [ ${#missing[@]} -gt 0 ]; then
        error "Missing prerequisites: ${missing[*]}"
        echo "Install them:"
        for tool in "${missing[@]}"; do
            case $tool in
                terraform) echo "  brew install terraform" ;;
                aws-cli)   echo "  brew install awscli" ;;
                docker)    echo "  brew install --cask docker" ;;
                jq)        echo "  brew install jq" ;;
            esac
        done
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi

    success "Prerequisites check passed"
}

build_image() {
    log "Building OpenClaw agent Docker image..."

    local account_id
    account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_url="${account_id}.dkr.ecr.${REGION}.amazonaws.com"
    local repo_url="${ecr_url}/kk-swarm/openclaw-agent"

    # Login to ECR
    aws ecr get-login-password --region "${REGION}" | \
        docker login --username AWS --password-stdin "${ecr_url}" 2>/dev/null

    # Create repo if it doesn't exist
    aws ecr describe-repositories --repository-names "kk-swarm/openclaw-agent" --region "${REGION}" 2>/dev/null || \
        aws ecr create-repository --repository-name "kk-swarm/openclaw-agent" --region "${REGION}" >/dev/null

    # Build
    docker build -t kk-swarm-openclaw-agent:latest "${TERRAFORM_DIR}"

    # Tag and push
    docker tag kk-swarm-openclaw-agent:latest "${repo_url}:latest"
    docker push "${repo_url}:latest"

    success "Docker image pushed to ECR: ${repo_url}:latest"
}

deploy_batch() {
    local current_count=$1
    local target_count=$2

    log "Deploying agents ${current_count} → ${target_count}..."

    cd "${TERRAFORM_DIR}"

    terraform apply \
        -var="anthropic_api_key=${API_KEY}" \
        -var="agent_count=${target_count}" \
        -var="aws_region=${REGION}" \
        -var="agent_model=${MODEL}" \
        -var="use_spot=${USE_SPOT}" \
        -auto-approve \
        -compact-warnings

    success "Deployed ${target_count} agents"
}

deploy_sequential() {
    local total=$1
    local batch=$2
    local current=0

    log "Sequential deployment: ${total} agents in batches of ${batch}"

    # Initialize Terraform
    cd "${TERRAFORM_DIR}"
    terraform init -upgrade -compact-warnings

    # Build Docker image first
    build_image

    while [ $current -lt $total ]; do
        local next=$((current + batch))
        if [ $next -gt $total ]; then
            next=$total
        fi

        echo ""
        echo -e "${PURPLE}════════════════════════════════════════════════════════════${NC}"
        echo -e "${PURPLE}  Deploying batch: agents $((current + 1)) to ${next} of ${total}${NC}"
        echo -e "${PURPLE}════════════════════════════════════════════════════════════${NC}"
        echo ""

        deploy_batch $current $next
        current=$next

        if [ $current -lt $total ]; then
            log "Waiting 30 seconds before next batch..."
            sleep 30
        fi
    done

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Deployment Complete! 🪄✨                       ║${NC}"
    echo -e "${GREEN}║  ${total} agents deployed successfully                        ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"

    # Show outputs
    terraform output
}

show_status() {
    log "Checking deployment status..."

    cd "${TERRAFORM_DIR}"

    if [ ! -f "terraform.tfstate" ] && [ ! -d ".terraform" ]; then
        warn "No Terraform state found. Nothing deployed yet."
        return
    fi

    # Check ECS cluster
    local cluster_name
    cluster_name=$(terraform output -raw cluster_name 2>/dev/null || echo "")

    if [ -z "$cluster_name" ]; then
        warn "No cluster found in Terraform state."
        return
    fi

    echo ""
    echo -e "${BLUE}Cluster:${NC} ${cluster_name}"
    echo ""

    # List services
    echo -e "${BLUE}Agent Services:${NC}"
    aws ecs list-services --cluster "${cluster_name}" --region "${REGION}" --query 'serviceArns[*]' --output table 2>/dev/null || \
        warn "Could not list services"

    # Show running tasks
    echo ""
    echo -e "${BLUE}Running Tasks:${NC}"
    aws ecs list-tasks --cluster "${cluster_name}" --region "${REGION}" --desired-status RUNNING --query 'taskArns[*]' --output table 2>/dev/null || \
        warn "Could not list tasks"

    echo ""
    terraform output 2>/dev/null || true
}

destroy() {
    warn "This will DESTROY all KarmaCadabra Swarm infrastructure!"
    echo ""
    read -p "Type 'destroy' to confirm: " confirmation

    if [ "$confirmation" != "destroy" ]; then
        log "Cancelled."
        exit 0
    fi

    cd "${TERRAFORM_DIR}"
    terraform init -upgrade -compact-warnings 2>/dev/null
    terraform destroy \
        -var="anthropic_api_key=placeholder" \
        -auto-approve

    success "All infrastructure destroyed"
}

show_plan() {
    cd "${TERRAFORM_DIR}"
    terraform init -upgrade -compact-warnings 2>/dev/null
    terraform plan \
        -var="anthropic_api_key=${API_KEY}" \
        -var="agent_count=${AGENTS}" \
        -var="aws_region=${REGION}" \
        -var="agent_model=${MODEL}" \
        -var="use_spot=${USE_SPOT}"
}

# ── Parse Arguments ──────────────────────────────────────────────────────────
API_KEY=""
AGENTS=${DEFAULT_AGENTS}
BATCH=${DEFAULT_BATCH}
REGION=${DEFAULT_REGION}
MODEL=${DEFAULT_MODEL}
USE_SPOT="true"
ACTION="deploy"

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-key)   API_KEY="$2"; shift 2 ;;
        --agents)    AGENTS="$2"; shift 2 ;;
        --batch)     BATCH="$2"; shift 2 ;;
        --region)    REGION="$2"; shift 2 ;;
        --model)     MODEL="$2"; shift 2 ;;
        --no-spot)   USE_SPOT="false"; shift ;;
        --destroy)   ACTION="destroy"; shift ;;
        --status)    ACTION="status"; shift ;;
        --plan)      ACTION="plan"; shift ;;
        --build)     ACTION="build"; shift ;;
        -h|--help)   usage; exit 0 ;;
        *) error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# ── Execute ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║              KarmaCadabra Swarm Deployer 🪄                 ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

case $ACTION in
    deploy)
        if [ -z "$API_KEY" ]; then
            error "Anthropic API key is required. Use --api-key sk-ant-..."
            usage
            exit 1
        fi
        check_prerequisites
        deploy_sequential "$AGENTS" "$BATCH"
        ;;
    destroy)
        check_prerequisites
        destroy
        ;;
    status)
        show_status
        ;;
    plan)
        if [ -z "$API_KEY" ]; then
            error "Anthropic API key is required for plan. Use --api-key sk-ant-..."
            exit 1
        fi
        check_prerequisites
        show_plan
        ;;
    build)
        check_prerequisites
        build_image
        ;;
esac

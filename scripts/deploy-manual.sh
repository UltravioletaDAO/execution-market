#!/bin/bash
# Execution Market Manual Deployment Script
# Run this after Docker Desktop is running

set -e

# Configuration
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-YOUR_AWS_ACCOUNT_ID}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
MCP_REPO="em-production-mcp-server"
DASHBOARD_REPO="em-production-dashboard"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Execution Market Deployment Script ==="
echo "Region: $AWS_REGION"
echo "ECR Registry: $ECR_REGISTRY"
echo ""

# Check Docker
echo "1. Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "   Docker is running."

# Login to ECR
echo ""
echo "2. Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build MCP Server
echo ""
echo "3. Building MCP Server..."
cd "$PROJECT_ROOT/mcp_server"
docker build --platform linux/amd64 -t $MCP_REPO:latest .
docker tag $MCP_REPO:latest $ECR_REGISTRY/$MCP_REPO:latest

# Build Dashboard
echo ""
echo "4. Building Dashboard..."
cd "$PROJECT_ROOT/dashboard"
docker build --platform linux/amd64 -t $DASHBOARD_REPO:latest \
  --build-arg VITE_API_URL=https://api.execution.market .
docker tag $DASHBOARD_REPO:latest $ECR_REGISTRY/$DASHBOARD_REPO:latest

# Push to ECR
echo ""
echo "5. Pushing images to ECR..."
docker push $ECR_REGISTRY/$MCP_REPO:latest
docker push $ECR_REGISTRY/$DASHBOARD_REPO:latest

echo ""
echo "6. Images pushed successfully!"
echo ""
echo "   MCP Server: $ECR_REGISTRY/$MCP_REPO:latest"
echo "   Dashboard:  $ECR_REGISTRY/$DASHBOARD_REPO:latest"
echo ""
echo "Next steps:"
echo "  1. Apply Terraform: cd infrastructure/terraform && terraform apply"
echo "  2. Update ECS services (if they exist)"
echo ""
echo "=== Done ==="

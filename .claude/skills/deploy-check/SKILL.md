# Deploy Check — ECS Deployment Verification

Verify ECS deployment state for Execution Market services. Use when the user says "deploy check", "check deployment", "verify ECS", "is it running", "check health", "deployment status", or after deploying new code.

## Quick Health Check

Run all checks in parallel:

```bash
# 1. Check what revision each service is running
aws ecs describe-services \
  --cluster em-production-cluster \
  --services em-production-mcp-server em-production-dashboard \
  --region us-east-2 \
  --query 'services[*].{name:serviceName,taskDef:taskDefinition,running:runningCount,desired:desiredCount,pending:pendingCount}' \
  --output table

# 2. Check health endpoints
curl -s https://mcp.execution.market/health/ | python3 -m json.tool
curl -s https://execution.market/ | head -5

# 3. Check x402 payment health
curl -s https://mcp.execution.market/health/ | python3 -c "import sys,json; h=json.load(sys.stdin); print('x402:', h.get('components',{}).get('x402',{}))"
```

## Full Deployment Verification

### Step 1: Service Status

```bash
aws ecs describe-services \
  --cluster em-production-cluster \
  --services em-production-mcp-server em-production-dashboard \
  --region us-east-2 \
  --query 'services[*].{name:serviceName,taskDef:taskDefinition,running:runningCount,desired:desiredCount,deployments:deployments[*].{status:status,taskDef:taskDefinition,running:runningCount}}' \
  --output json
```

**What to check:**
- `runningCount == desiredCount` (usually 1)
- Only ONE deployment with status "PRIMARY" and `runningCount > 0`
- If there are TWO deployments, one is draining (old revision)

### Step 2: Task Definition Revision

```bash
# MCP Server
aws ecs describe-task-definition \
  --task-definition em-production-mcp-server \
  --region us-east-2 \
  --query 'taskDefinition.{rev:revision,image:containerDefinitions[0].image,env:containerDefinitions[0].environment[*].name,secrets:containerDefinitions[0].secrets[*].name}'

# Dashboard
aws ecs describe-task-definition \
  --task-definition em-production-dashboard \
  --region us-east-2 \
  --query 'taskDefinition.{rev:revision,image:containerDefinitions[0].image}'
```

**Expected MCP (rev 150+):**
- Env: PORT, ENVIRONMENT, ERC8004_NETWORK, EM_AGENT_ID, EM_PAYMENT_MODE, EM_ESCROW_MODE, EM_PAYMENT_OPERATOR, EM_FEE_MODEL, EM_ENABLED_NETWORKS, EM_BASE_URL, EM_FEEDBACK_BASE_URL, ERC8128_NONCE_STORE, EVIDENCE_BUCKET, EVIDENCE_PUBLIC_BASE_URL
- Secrets: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET, EM_ADMIN_KEY, WALLET_PRIVATE_KEY, X402_NETWORK, X402_RPC_URL, X402_FACILITATOR_URL, EM_ESCROW_ADDRESS, USDC_ADDRESS, EM_TREASURY_ADDRESS, ANTHROPIC_API_KEY, EM_WORKER_PRIVATE_KEY
- Image: `<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest`

### Step 3: Health Endpoints

```bash
# Detailed health (includes component latency)
curl -s https://mcp.execution.market/health/ | python3 -m json.tool

# Version info
curl -s https://mcp.execution.market/health/version

# Route count
curl -s https://mcp.execution.market/health/routes | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'{r[\"total_routes\"]} routes')"
```

### Step 4: Smoke Test

```bash
cd /mnt/z/ultravioleta/dao/execution-market/scripts
npx tsx smoke-test.ts
```

## CRITICAL: ECS Gotchas

### Service Can Run Old Revision
ECS services can keep running an old task definition even after registering new revisions. Always verify:
```bash
# Check ACTUAL running revision (not just latest registered)
aws ecs describe-services \
  --cluster em-production-cluster \
  --services em-production-mcp-server \
  --region us-east-2 \
  --query 'services[0].taskDefinition'
```

### Force New Deployment
If the service is stuck on an old revision:
```bash
aws ecs update-service \
  --cluster em-production-cluster \
  --service em-production-mcp-server \
  --task-definition em-production-mcp-server:<LATEST_REV> \
  --force-new-deployment \
  --region us-east-2
```

### Image Tag Must Be :latest
Task definitions MUST reference `:latest` tag. If a `ship-*` tag is referenced, register a new revision.

## Deploy Workflow

```bash
# Full deploy script (builds, pushes, deploys both services)
.claude/scripts/deploy.sh

# Or manual:
# 1. Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com

# 2. Build + push
docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server
docker tag em-mcp:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest

# 3. Force new deployment
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2

# 4. Wait and verify
sleep 60
aws ecs describe-services --cluster em-production-cluster --services em-production-mcp-server --region us-east-2 --query 'services[0].{running:runningCount,desired:desiredCount}'
```

## AWS Details

| Resource | Value |
|----------|-------|
| Account | <YOUR_AWS_ACCOUNT_ID> |
| Region | us-east-2 |
| Cluster | em-production-cluster |
| MCP Service | em-production-mcp-server |
| Dashboard Service | em-production-dashboard |
| MCP ECR | em-production-mcp-server |
| Dashboard ECR | em-production-dashboard |
| MCP Task Def Rev | 150+ (`:latest` tag) |
| Dashboard Task Def Rev | 12 |

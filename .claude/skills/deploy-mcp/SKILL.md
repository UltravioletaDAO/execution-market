# Skill: Deploy MCP Server to ECS

## Trigger
When code changes in `mcp_server/` need to go to production. Use after committing changes, or when the user says "deploy", "despliega", "push to production", "redeploy".

## Prerequisites
- AWS CLI configured (default profile `518898403364`)
- Docker running locally
- Code committed to `main` branch
- `MSYS_NO_PATHCONV=1` prefix on ALL aws commands (Git Bash Windows path bug)

## Step 1: Build Docker Image

```bash
cd mcp_server
docker build --no-cache -f Dockerfile -t em-mcp .
```

**IMPORTANT**: Always `--no-cache` for code changes.

## Step 2: Login to ECR

```bash
MSYS_NO_PATHCONV=1 aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 518898403364.dkr.ecr.us-east-2.amazonaws.com
```

## Step 3: Tag and Push

```bash
docker tag em-mcp:latest 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
```

## Step 4: Force New Deployment

```bash
MSYS_NO_PATHCONV=1 aws ecs update-service \
  --cluster em-production-cluster \
  --service em-production-mcp-server \
  --force-new-deployment \
  --region us-east-2 \
  --query 'service.deployments[0].{status:status,taskDef:taskDefinition}' \
  --output json
```

## Step 5: Verify (wait ~90s)

```bash
sleep 90

# Health check
curl -s https://api.execution.market/api/v1/health | python -m json.tool

# Verify new code is active (check OpenAPI for new endpoints, etc.)
curl -s https://api.execution.market/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d[\"paths\"])} endpoints registered')"
```

## CRITICAL: Task Definition Must Use :latest

The ECS task definition (revision 150+) MUST reference `:latest` tag, not a commit SHA. If CI/CD creates a revision with a SHA tag:

```bash
# Check current image tag
MSYS_NO_PATHCONV=1 aws ecs describe-task-definition \
  --task-definition em-production-mcp-server \
  --region us-east-2 \
  --query 'taskDefinition.containerDefinitions[0].image' --output text
```

If it shows a SHA tag instead of `:latest`, register a new revision:

```bash
# Get current container defs
MSYS_NO_PATHCONV=1 aws ecs describe-task-definition \
  --task-definition em-production-mcp-server \
  --region us-east-2 --output json > taskdef.json

# Fix image to :latest in Python
python -c "
import json
with open('taskdef.json') as f:
    td = json.load(f)['taskDefinition']
cd = td['containerDefinitions'][0]
cd['image'] = '518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest'
with open('container-defs.json', 'w') as f:
    json.dump([cd], f)
"

# Register new revision
MSYS_NO_PATHCONV=1 aws ecs register-task-definition \
  --family em-production-mcp-server \
  --container-definitions "$(cat container-defs.json)" \
  --task-role-arn "arn:aws:iam::518898403364:role/em-production-ecs-task" \
  --execution-role-arn "arn:aws:iam::518898403364:role/em-production-ecs-execution" \
  --network-mode awsvpc --requires-compatibilities FARGATE \
  --cpu 256 --memory 512 --region us-east-2

# Deploy with new revision
MSYS_NO_PATHCONV=1 aws ecs update-service \
  --cluster em-production-cluster \
  --service em-production-mcp-server \
  --task-definition "em-production-mcp-server:NEW_REV" \
  --force-new-deployment --region us-east-2
```

## Quick Reference

| Resource | Value |
|----------|-------|
| Account | `518898403364` |
| Region | `us-east-2` |
| Cluster | `em-production-cluster` |
| Service | `em-production-mcp-server` |
| ECR Repo | `em-production-mcp-server` |
| Task Def Rev | 150 (`:latest`, 14 secrets) |
| Health URL | `https://api.execution.market/api/v1/health` |
| Docs URL | `https://api.execution.market/docs` |

## Dashboard Deploy (separate)

```bash
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard
docker tag em-dashboard:latest 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
docker push 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
MSYS_NO_PATHCONV=1 aws ecs update-service --cluster em-production-cluster --service em-production-dashboard --force-new-deployment --region us-east-2
```

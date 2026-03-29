# Skill: Deploy MCP Server to ECS

## Trigger
When code changes in `mcp_server/` need to go to production. Use after committing changes, or when the user says "deploy", "despliega", "push to production", "redeploy".

## Prerequisites
- AWS CLI configured (default profile `<YOUR_AWS_ACCOUNT_ID>`)
- Docker running locally
- Code committed to `main` branch
- `MSYS_NO_PATHCONV=1` prefix on ALL aws commands (Git Bash Windows path bug)

## CRITICAL: Never Modify Task Definition Env Vars Manually

**ABSOLUTE RULE: NEVER register a new ECS task definition to add/change/remove environment variables.**

Environment variables are owned by Terraform (`infrastructure/terraform/ecs.tf`). If you need to add or change an env var:

1. Edit `infrastructure/terraform/ecs.tf` (the `environment` block in `aws_ecs_task_definition.mcp_server`)
2. Commit the change
3. Push to `main` — CI/CD will run `terraform apply` automatically
4. Or run terraform apply locally (see "Terraform Apply" section below)

**Why**: Manual task definition updates create "shadow" revisions that diverge from Terraform state. The next deploy inherits the shadow revision, and Terraform changes (like adding SKALE to `EM_ENABLED_NETWORKS`) get silently lost. This caused the SKALE outage on 2026-03-28 (rev 337).

**The ONLY thing this skill should change in task definitions is the Docker image tag.**

## Step 1: Build Docker Image

```bash
cd mcp_server
docker build --no-cache -f Dockerfile -t em-mcp .
```

**IMPORTANT**: Always `--no-cache` for code changes.

## Step 2: Login to ECR

```bash
MSYS_NO_PATHCONV=1 aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com
```

## Step 3: Tag and Push

```bash
docker tag em-mcp:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
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

**This is safe** — it re-uses the existing task definition and just pulls the `:latest` image. No env vars are touched.

## Step 5: Verify (wait ~90s)

```bash
sleep 90

# Health check
curl -s https://api.execution.market/api/v1/health | python -m json.tool

# Verify new code is active (check OpenAPI for new endpoints, etc.)
curl -s https://api.execution.market/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d[\"paths\"])} endpoints registered')"
```

## Terraform Apply (for env var / infra changes)

When you need to change environment variables, CPU/memory, secrets, or other infrastructure:

1. **Edit Terraform** — modify `infrastructure/terraform/ecs.tf`
2. **Plan** (verify changes):
```bash
cd infrastructure/terraform
MSYS_NO_PATHCONV=1 terraform init -backend-config="key=em/terraform.tfstate"
MSYS_NO_PATHCONV=1 terraform plan -var="enable_evidence_pipeline=true"
```
3. **Apply** (after user confirms):
```bash
MSYS_NO_PATHCONV=1 terraform apply -var="enable_evidence_pipeline=true"
```
4. **Force deploy** to pick up changes:
```bash
MSYS_NO_PATHCONV=1 aws ecs update-service \
  --cluster em-production-cluster \
  --service em-production-mcp-server \
  --force-new-deployment --region us-east-2
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

If it shows a SHA tag instead of `:latest`, the simplest fix is to push `:latest` to ECR and force deploy (Steps 1-4 above). Do NOT register a new task definition manually.

## Quick Reference

| Resource | Value |
|----------|-------|
| Account | `<YOUR_AWS_ACCOUNT_ID>` |
| Region | `us-east-2` |
| Cluster | `em-production-cluster` |
| Service | `em-production-mcp-server` |
| ECR Repo | `em-production-mcp-server` |
| TF State Key | `em/terraform.tfstate` |
| Health URL | `https://api.execution.market/api/v1/health` |
| Docs URL | `https://api.execution.market/docs` |

## Dashboard Deploy (S3 + CloudFront — NOT ECS)

**IMPORTANT**: Dashboard is served via S3+CloudFront, NOT ECS (ECS service is desiredCount=0).

```bash
# 1. Build
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard

# 2. Extract built files from image
docker create --name em-dashboard-tmp em-dashboard:latest
docker cp em-dashboard-tmp:/usr/share/nginx/html/. ./dashboard-dist/
docker rm em-dashboard-tmp

# 3. Sync to S3
MSYS_NO_PATHCONV=1 aws s3 sync ./dashboard-dist/ s3://em-production-dashboard/ --delete --region us-east-2

# 4. Invalidate CloudFront cache
MSYS_NO_PATHCONV=1 aws cloudfront create-invalidation --distribution-id E2SD27QZ0GK40U --paths "/*" --region us-east-2

# 5. Cleanup
rm -rf ./dashboard-dist/
```

| Resource | Value |
|----------|-------|
| S3 Bucket | `em-production-dashboard` |
| CloudFront | `E2SD27QZ0GK40U` |
| URL | `https://execution.market` |

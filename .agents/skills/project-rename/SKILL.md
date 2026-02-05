---
name: project-rename
description: Rename a project across all layers — code, infrastructure, Docker, CI/CD, DNS, docs, SDKs, and environment variables. Use when the user wants to rebrand, rename, or change the prefix/name of a project throughout the entire codebase and deployed infrastructure. Triggers on requests like "rename the project", "rebrand from X to Y", "change all references from old-name to new-name", or "migrate infrastructure names".
---

# Project Rename

Systematic checklist for renaming a project across every layer. Run each phase in order.

## Phase 0: Preparation

1. Identify the old name and all its variants (lowercase, UPPERCASE, CamelCase, kebab-case, snake_case, with/without prefix)
2. Identify the new name and generate all equivalent variants
3. Create a branch for the rename work
4. Run a global grep for every variant to build the full scope:
   ```bash
   grep -rn "old_name\|old-name\|OldName\|OLD_NAME\|oldname" \
     --include='*.{ts,tsx,js,py,md,json,yaml,yml,tf,sql,toml,cfg,conf,env,sh}' \
     --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=contracts/lib .
   ```

## Phase 1: Infrastructure (Terraform / IaC)

See [references/terraform-patterns.md](references/terraform-patterns.md) for detailed Terraform rename patterns and code examples.

| Item | What to rename |
|------|---------------|
| Resource prefix | `name_prefix` in main.tf |
| State backend key | S3 key in backend config |
| ECR repos | Repository names |
| ECS cluster & services | Cluster name, service names |
| IAM policies | Resource ARNs referencing old name |
| Secrets Manager paths | Secret path prefix |
| ALB & target groups | Via prefix (automatic) |
| Route53 records | Verify zone lookups match the domain |
| CloudWatch log groups | Log group paths |

**Gotcha — ACM + Route53 zone mismatch**: If the Terraform zone lookup references zone A but the ACM cert needs validation in zone B, cert validation fails silently. Ensure the zone lookup matches `var.domain`.

**Destroy & recreate workflow**:
1. Disable ALB deletion protection
2. `terraform destroy -auto-approve`
3. Force-delete non-empty ECR repos via `aws ecr delete-repository --force`, then `terraform state rm`
4. Update all `.tf` files with new names
5. `terraform apply`
6. Import pre-existing DNS records: `terraform import`

## Phase 2: AWS Secrets Manager

Copy each secret from old path to new path:

```bash
for secret in supabase admin-key commission contracts api-keys x402; do
  VALUE=$(aws secretsmanager get-secret-value --secret-id "old/$secret" --query SecretString --output text)
  aws secretsmanager create-secret --name "new/$secret" --secret-string "$VALUE"
done
```

## Phase 3: Docker & Build

| File | What to rename |
|------|---------------|
| Dockerfiles | Linux user/group names, header comments, example commands |
| docker-compose*.yml | Service names, network names, image tags |
| .dockerignore | Header comments |
| Makefile | Echo messages, network names, image tags |
| nginx configs | Header comments |

## Phase 4: CI/CD (GitHub Actions)

| Item | Files |
|------|-------|
| ECR repo names | deploy*.yml |
| ECS cluster/service names | deploy*.yml |
| Container names in task defs | deploy*.yml + task-def-*.json |
| AWS region (verify!) | all workflow files |
| CODEOWNERS | team name references |

## Phase 5: Application Code

| What to find | What to do |
|-------------|-----------|
| `OLD_NAME_*` env var fallbacks | Remove the fallback, keep only new name |
| `old_prefix_*` API key prefixes | Replace with new prefix |
| Backward-compat aliases (`OldClient = NewClient`) | Delete them |
| Rate limit prefix checks in middleware | Update to new prefix |
| Storage bucket references | Update bucket names |
| i18n keys referencing old name | Rename keys + update all locales |
| SDK/CLI env var fallbacks | Remove all old fallback chains |

## Phase 6: Documentation

Update: README.md, CLAUDE.md, SPEC.md, PLAN.md, agent-card.json, IDEA.yaml — project name, URLs, infrastructure details, deploy commands, secret paths, ECR repos.

## Phase 7: Final Sweep

```bash
grep -rn "old_name\|old-name\|OldName\|OLD_NAME" \
  --include='*.{ts,tsx,js,py,md,json,yaml,yml,tf,toml,cfg,conf,sh}' \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=contracts/lib .
```

**Do NOT rename**: immutable on-chain contracts, historical SQL migrations, git history, third-party libraries.

## Phase 8: Build, Deploy & Verify

1. Build and push Docker images to new ECR repos
2. Force ECS redeployment
3. Verify health endpoints + dashboard loads
4. Check DNS points to new ALB
5. Commit with a clear message

## Key Lessons

- Grep for ALL name variants including UPPERCASE env vars, kebab-case, camelCase
- ECR repos cannot be destroyed if not empty — force-delete via CLI first
- Route53 zone lookups cause silent cert validation failures when mismatched
- Stale DNS records pointing to destroyed ALBs need manual UPSERT
- Remove backward-compat aliases completely — they accumulate tech debt
- Check Terraform state for imported resources that may conflict on apply

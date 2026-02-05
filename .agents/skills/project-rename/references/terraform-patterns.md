# Terraform Rename Patterns

## State Migration

When changing the S3 backend key:

```hcl
# Before
terraform {
  backend "s3" {
    key = "old-name/terraform.tfstate"
  }
}

# After
terraform {
  backend "s3" {
    key = "new-name/terraform.tfstate"
  }
}
```

Run `terraform init -migrate-state` OR destroy-and-recreate for a full rename.

## Common Resource Patterns

### ECS + ECR

```hcl
locals {
  name_prefix = "${var.project_prefix}-${var.environment}"
}

resource "aws_ecr_repository" "dashboard" {
  name = "${local.name_prefix}-dashboard"
}

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
}

resource "aws_ecs_service" "dashboard" {
  name    = "${local.name_prefix}-dashboard"
  cluster = aws_ecs_cluster.main.id
}
```

### Secrets Manager IAM Policy

```hcl
resource "aws_iam_policy" "secrets_access" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_prefix}/*"
    }]
  })
}
```

### Route53 Zone Lookup

```hcl
# CRITICAL: zone name must match the domain being validated
data "aws_route53_zone" "main" {
  name = var.domain  # NOT a parent domain like "example.org"
}
```

## Destroy Sequence

1. Disable ALB deletion protection:
   ```bash
   aws elbv2 modify-load-balancer-attributes \
     --load-balancer-arn <arn> \
     --attributes Key=deletion_protection.enabled,Value=false
   ```
2. `terraform destroy -auto-approve`
3. Force-delete non-empty ECR repos:
   ```bash
   aws ecr delete-repository --repository-name <name> --force
   terraform state rm 'aws_ecr_repository.name'
   ```
4. Update `.tf` files with new prefix
5. `terraform apply`
6. Import pre-existing DNS records:
   ```bash
   terraform import 'aws_route53_record.name' 'ZONEID_domain.com_A'
   ```

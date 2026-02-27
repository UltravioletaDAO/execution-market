---
date: 2026-02-26
tags:
  - domain/infrastructure
  - terraform
  - iac
status: active
aliases:
  - IaC
  - Terraform
  - Infrastructure as Code
related-files:
  - infrastructure/
---

# Terraform

All Execution Market infrastructure is managed as code via Terraform.

## Absolute Rule

**NEVER CloudFormation.** Terraform only.

**NEVER manual AWS CLI** for production infrastructure changes. If it can be terraformed, it must be.

Temporary exceptions:
- Security group changes for debugging (close after)
- One-off ECS task definition updates during incident response

## Source

All Terraform configurations live in `infrastructure/`.

## Managed Resources

| Resource | Terraform Module |
|----------|-----------------|
| ECS Cluster + Services | [[ecs-fargate]] |
| ECR Repositories | [[ecr-registry]] |
| ALB + Target Groups | [[alb-dns-routing]] |
| Route53 DNS Records | [[alb-dns-routing]] |
| ACM Certificates | TLS termination |
| S3 Buckets | [[cloudfront-s3]] (evidence + admin) |
| CloudFront Distributions | [[cloudfront-s3]] |
| Security Groups | Network rules |
| IAM Roles | ECS task execution roles |

## Workflow

```bash
cd infrastructure
terraform init
terraform plan    # Always review before apply
terraform apply   # Apply changes
```

## State

Terraform state is stored remotely (S3 backend with DynamoDB locking) to enable team collaboration and prevent state conflicts.

## Related

- [[aws-account]] -- target AWS account
- [[ecs-fargate]] -- primary compute resource

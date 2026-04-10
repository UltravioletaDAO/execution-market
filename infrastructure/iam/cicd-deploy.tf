# IAM Policy for Execution Market CI/CD (GitHub Actions)
#
# Minimal permissions: ECR push, ECS deploy, S3 dashboard sync, CloudFront invalidation.
# Attached to user `cuchorapido` for GitHub Actions deployments.
#
# Created: 2026-03-13
# Applied manually via AWS CLI, Terraform for persistence/drift detection.

locals {
  aws_account_id      = "<YOUR_AWS_ACCOUNT_ID>"
  aws_region          = "us-east-2"
  cloudfront_dist_id  = "E2SD27QZ0GK40U"
  dashboard_s3_bucket = "em-production-dashboard"
  cicd_user           = "execution-market-deployer"
}

resource "aws_iam_policy" "em_cicd_deploy" {
  name        = "em-cicd-deploy"
  description = "Minimal permissions for Execution Market CI/CD: ECR push, ECS deploy, S3 dashboard, CloudFront invalidation"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "ECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ]
        Resource = [
          "arn:aws:ecr:${local.aws_region}:${local.aws_account_id}:repository/em-production-mcp-server",
          "arn:aws:ecr:${local.aws_region}:${local.aws_account_id}:repository/em-production-dashboard",
        ]
      },
      {
        Sid    = "ECSDeployServices"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:ListTasks",
          "ecs:DescribeTasks",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = local.aws_region
          }
        }
      },
      {
        Sid    = "PassRolesToECS"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          "arn:aws:iam::${local.aws_account_id}:role/em-production-ecs-task",
          "arn:aws:iam::${local.aws_account_id}:role/em-production-ecs-execution",
        ]
      },
      {
        Sid    = "S3DashboardDeploy"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ]
        Resource = [
          "arn:aws:s3:::${local.dashboard_s3_bucket}",
          "arn:aws:s3:::${local.dashboard_s3_bucket}/*",
        ]
      },
      {
        Sid      = "CloudFrontInvalidate"
        Effect   = "Allow"
        Action   = "cloudfront:CreateInvalidation"
        Resource = "arn:aws:cloudfront::${local.aws_account_id}:distribution/${local.cloudfront_dist_id}"
      },
    ]
  })
}

resource "aws_iam_user_policy_attachment" "cicd_deploy" {
  user       = local.cicd_user
  policy_arn = aws_iam_policy.em_cicd_deploy.arn
}

# ── Terraform-specific policy ───────────────────────────────────────────────
#
# Grants the deployer permissions needed for `terraform plan/apply` in the
# infrastructure/terraform/ workspace. Covers: ECS, VPC/SGs, IAM (em-* scoped),
# CloudWatch/SNS, ALB, WAFv2, Secrets, ECR, DynamoDB, Route53, CloudFront, ACM,
# S3, EFS, Lambda, API Gateway, AutoScaling.
#
# Managed manually via AWS CLI until now. Tracked here for drift detection.
# Source of truth: infrastructure/iam/em-cicd-terraform-policy.json
#
# Updated 2026-04-04: Added TerraformWAFv2 + TerraformWAFLogDelivery statements
# to support waf.tf resources (IP blocklist, Web ACL, association, logging).

resource "aws_iam_policy" "em_cicd_terraform" {
  name        = "em-cicd-terraform"
  description = "Terraform plan/apply permissions for Execution Market infrastructure: ECS, VPC, IAM, CloudWatch, ALB, WAFv2, Route53, etc."
  policy      = file("${path.module}/em-cicd-terraform-policy.json")
}

resource "aws_iam_user_policy_attachment" "cicd_terraform" {
  user       = local.cicd_user
  policy_arn = aws_iam_policy.em_cicd_terraform.arn
}

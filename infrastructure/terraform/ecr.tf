# Execution Market Infrastructure - ECR Repositories
#
# Dashboard ECR repo is kept for CI/CD artifact storage (deploy.yml pushes here
# even though the runtime serves from S3+CloudFront). Lifecycle policy set to 5
# images (down from 10) — ECR storage cost is ~$0.10/GB/month.

# MCP Server Repository
resource "aws_ecr_repository" "mcp_server" {
  name                 = "${local.name_prefix}-mcp-server"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${local.name_prefix}-mcp-server"
  }
}

# Dashboard Repository (used by CI/CD to build and push; runtime is S3+CloudFront)
resource "aws_ecr_repository" "dashboard" {
  name                 = "${local.name_prefix}-dashboard"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${local.name_prefix}-dashboard"
  }
}

# Lifecycle policies — keep last 5 images to minimize ECR storage costs
resource "aws_ecr_lifecycle_policy" "mcp_server" {
  repository = aws_ecr_repository.mcp_server.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 tagged images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["latest", "v"]
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus  = "untagged"
          countType  = "sinceImagePushed"
          countUnit  = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "dashboard" {
  repository = aws_ecr_repository.dashboard.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 tagged images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["latest", "v"]
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus  = "untagged"
          countType  = "sinceImagePushed"
          countUnit  = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

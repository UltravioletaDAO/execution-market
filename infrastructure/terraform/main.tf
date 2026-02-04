# Execution Market Infrastructure - Main Terraform Configuration
# AWS ECS Fargate deployment

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "ultravioleta-terraform-state"
    key     = "chamba/terraform.tfstate" # Kept as "chamba" to preserve existing state
    region  = "us-east-2"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Execution Market"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values
locals {
  # NOTE: name_prefix kept as "chamba" to avoid recreating existing AWS resources
  name_prefix = "chamba-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
}

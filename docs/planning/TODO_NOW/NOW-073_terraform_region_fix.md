# NOW-073: Terraform Region Configuration Fix

## Status: REQUIRED
## Priority: P0 - Blocker for deployment

## Problem

El Terraform state bucket está en **us-east-2**, pero el código original tenía configurado us-east-1.

**Error**:
```
Error: Failed to get existing workspaces: S3 bucket does not exist.
The referenced S3 bucket must have been previously created...
requested bucket from us-east-1, actual location us-east-2
```

## Archivos a Modificar

### 1. `infrastructure/terraform/main.tf`

```diff
  backend "s3" {
    bucket       = "ultravioleta-terraform-state"
    key          = "chamba/terraform.tfstate"
-   region       = "us-east-1"
+   region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
```

### 2. `infrastructure/terraform/variables.tf`

```diff
variable "aws_region" {
  description = "AWS region"
  type        = string
- default     = "us-east-1"
+ default     = "us-east-2"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
- default     = ["us-east-1a", "us-east-1b"]
+ default     = ["us-east-2a", "us-east-2b"]
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
- default     = "chamba.example.com"
+ default     = "execution.market"
}
```

## Verificar

```bash
cd infrastructure/terraform
terraform init
terraform plan
```

## Nota Importante

**TODA la infraestructura debe estar en us-east-2**:
- Terraform state bucket: us-east-2
- ECR repositories: us-east-2
- ECS cluster: us-east-2
- VPC: us-east-2

**Excepción**: ACM Certificate para CloudFront DEBE estar en us-east-1 (requerimiento de AWS).

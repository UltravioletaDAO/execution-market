# NOW-004: Terraform para AWS ECS

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-001, NOW-002
- **Archivos a crear**: `infrastructure/terraform/`
- **Tiempo estimado**: 2-4 horas

## Descripción
Crear configuración Terraform completa para deployar Chamba en AWS ECS Fargate.

## Contexto Técnico
- **Provider**: AWS
- **Compute**: ECS Fargate (serverless containers)
- **Load Balancer**: ALB
- **Registry**: ECR
- **Secrets**: AWS Secrets Manager
- **DNS**: Route53

## Estructura de Archivos

```
infrastructure/terraform/
├── main.tf           # Provider, backend
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── vpc.tf            # VPC, subnets
├── ecr.tf            # Container registry
├── ecs.tf            # ECS cluster, services
├── alb.tf            # Load balancer
├── secrets.tf        # Secrets Manager
├── route53.tf        # DNS records
└── terraform.tfvars.example
```

## Código de Referencia

### main.tf
```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "ultravioleta-terraform-state"
    key    = "chamba/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "chamba"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

### variables.tf
```hcl
variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "production"
}

variable "domain" {
  default = "chamba.ultravioleta.xyz"
}

variable "mcp_server_cpu" {
  default = 256
}

variable "mcp_server_memory" {
  default = 512
}

variable "dashboard_cpu" {
  default = 256
}

variable "dashboard_memory" {
  default = 512
}
```

### ecs.tf (parcial)
```hcl
resource "aws_ecs_cluster" "chamba" {
  name = "chamba-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "mcp_server" {
  name            = "mcp-server"
  cluster         = aws_ecs_cluster.chamba.id
  task_definition = aws_ecs_task_definition.mcp_server.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.mcp_server.arn
    container_name   = "mcp-server"
    container_port   = 8000
  }
}
```

## Criterios de Éxito
- [ ] Todos los archivos .tf creados
- [ ] `terraform init` exitoso
- [ ] `terraform plan` sin errores
- [ ] `terraform apply` crea toda la infra
- [ ] Servicios accesibles via ALB
- [ ] SSL/TLS configurado
- [ ] Secrets en Secrets Manager (no en task definition)

## Recursos AWS Creados
- VPC + 2 public subnets + 2 private subnets
- Internet Gateway + NAT Gateway
- ECS Cluster
- 2 ECR repositories (mcp-server, dashboard)
- 2 ECS Services (mcp-server, dashboard)
- ALB + Target Groups
- Route53 records (api.chamba.*, app.chamba.*)
- ACM Certificate (SSL)
- Secrets Manager secrets

## Comandos de Verificación
```bash
cd infrastructure/terraform

# Init
terraform init

# Plan
terraform plan -var-file="production.tfvars"

# Apply
terraform apply -var-file="production.tfvars"

# Outputs
terraform output alb_dns_name
terraform output ecr_repository_urls
```

## Costos Estimados
- ECS Fargate: ~$30-50/mes (2 servicios x 0.25 vCPU)
- ALB: ~$20/mes
- NAT Gateway: ~$35/mes
- Route53: ~$0.50/mes
- **Total**: ~$85-105/mes

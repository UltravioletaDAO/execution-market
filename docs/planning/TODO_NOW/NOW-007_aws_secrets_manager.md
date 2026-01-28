# NOW-007: Mover secrets a AWS Secrets Manager

## Metadata
- **Prioridad**: P0 (SECURITY)
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-004
- **Archivos a modificar**: `infrastructure/terraform/secrets.tf`, ECS task definitions
- **Tiempo estimado**: 1-2 horas

## Descripción
Migrar todos los secrets de variables de entorno hardcodeadas a AWS Secrets Manager para seguridad.

## Contexto Técnico
- **Servicio**: AWS Secrets Manager
- **Rotación**: Automática donde sea posible
- **Acceso**: IAM roles para ECS tasks

## Secrets a Migrar

| Secret | Uso | Rotación |
|--------|-----|----------|
| SUPABASE_SERVICE_KEY | DB admin | Manual |
| X402_PRIVATE_KEY | Pagos | Manual |
| PINATA_JWT | IPFS uploads | Manual |
| ANTHROPIC_API_KEY | AI verification | Manual |

## Código de Referencia

### secrets.tf
```hcl
# Create secrets
resource "aws_secretsmanager_secret" "supabase" {
  name        = "chamba/${var.environment}/supabase"
  description = "Supabase credentials for Chamba"

  tags = {
    Service = "chamba"
  }
}

resource "aws_secretsmanager_secret_version" "supabase" {
  secret_id = aws_secretsmanager_secret.supabase.id
  secret_string = jsonencode({
    url         = var.supabase_url
    service_key = var.supabase_service_key
    anon_key    = var.supabase_anon_key
  })
}

resource "aws_secretsmanager_secret" "x402" {
  name        = "chamba/${var.environment}/x402"
  description = "x402 payment credentials"
}

resource "aws_secretsmanager_secret_version" "x402" {
  secret_id = aws_secretsmanager_secret.x402.id
  secret_string = jsonencode({
    rpc_url     = var.x402_rpc_url
    private_key = var.x402_private_key
  })
}

resource "aws_secretsmanager_secret" "anthropic" {
  name        = "chamba/${var.environment}/anthropic"
  description = "Anthropic API key for AI verification"
}

# IAM policy for ECS to access secrets
resource "aws_iam_policy" "secrets_access" {
  name        = "chamba-secrets-access"
  description = "Allow ECS tasks to access Chamba secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.supabase.arn,
          aws_secretsmanager_secret.x402.arn,
          aws_secretsmanager_secret.anthropic.arn
        ]
      }
    ]
  })
}
```

### ECS Task Definition (ecs.tf)
```hcl
resource "aws_ecs_task_definition" "mcp_server" {
  family                   = "chamba-mcp-server"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.mcp_server_cpu
  memory                   = var.mcp_server_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "mcp-server"
      image = "${aws_ecr_repository.mcp_server.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      # Secrets from Secrets Manager
      secrets = [
        {
          name      = "SUPABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.supabase.arn}:url::"
        },
        {
          name      = "SUPABASE_SERVICE_KEY"
          valueFrom = "${aws_secretsmanager_secret.supabase.arn}:service_key::"
        },
        {
          name      = "X402_RPC_URL"
          valueFrom = "${aws_secretsmanager_secret.x402.arn}:rpc_url::"
        },
        {
          name      = "X402_PRIVATE_KEY"
          valueFrom = "${aws_secretsmanager_secret.x402.arn}:private_key::"
        },
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.anthropic.arn}:api_key::"
        }
      ]

      # Non-sensitive environment variables
      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/chamba-mcp-server"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}
```

## Criterios de Éxito
- [ ] Secrets creados en Secrets Manager
- [ ] IAM policy permite acceso desde ECS
- [ ] Task definitions usan `secrets` en vez de `environment`
- [ ] No hay secrets en código o task definitions en plaintext
- [ ] ECS tasks pueden leer secrets al iniciar
- [ ] Logs no muestran valores de secrets

## Comandos de Verificación
```bash
# List secrets
aws secretsmanager list-secrets --filter Key=name,Values=chamba

# Get secret (para verificar existe, NO mostrar en logs)
aws secretsmanager get-secret-value \
  --secret-id chamba/production/supabase \
  --query 'SecretString' \
  --output text | jq 'keys'  # Solo muestra keys, no values

# Verify ECS can access
aws ecs describe-task-definition \
  --task-definition chamba-mcp-server \
  --query 'taskDefinition.containerDefinitions[0].secrets'
```

## Security Checklist
- [ ] Nunca logear valores de secrets
- [ ] Nunca commitear secrets en git
- [ ] Usar IAM roles, no access keys en containers
- [ ] Secrets tienen least-privilege access
- [ ] Rotation policy definida (aunque sea manual)

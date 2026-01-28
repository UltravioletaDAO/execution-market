# NOW-075: Push Docker Images to ECR

## Status: REQUIRED
## Priority: P0 - Blocker for ECS deployment

## Pre-requisitos
- Docker Desktop running
- ECR repositories creados (NOW-070)
- Docker images buildeadas (NOW-071, NOW-072)

## Paso 1: Login a ECR

```bash
# Login a ECR us-east-2
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com
```

**Output esperado**: `Login Succeeded`

## Paso 2: Tag y Push MCP Server

```bash
# Tag
docker tag chamba-mcp-server:latest \
  YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest

# Push
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest
```

## Paso 3: Tag y Push Dashboard

```bash
# Tag
docker tag chamba-dashboard:latest \
  YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest

# Push
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest
```

## Verificar

```bash
# Listar imágenes en ECR
aws ecr list-images --repository-name chamba-mcp-server --region us-east-2
aws ecr list-images --repository-name chamba-dashboard --region us-east-2
```

## Script Completo (Windows)

Para Windows con Docker Desktop, usar `cmd //c`:

```bash
# Login
aws ecr get-login-password --region us-east-2 | \
  cmd //c "docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com"

# Build y push MCP Server
cmd //c "cd /d Z:\ultravioleta\dao\control-plane\ideas\chamba\mcp_server && \
  docker build --no-cache --platform linux/amd64 -t chamba-mcp-server:latest . && \
  docker tag chamba-mcp-server:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest && \
  docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest"

# Build y push Dashboard
cmd //c "cd /d Z:\ultravioleta\dao\control-plane\ideas\chamba\dashboard && \
  docker build --no-cache --platform linux/amd64 -t chamba-dashboard:latest . && \
  docker tag chamba-dashboard:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest && \
  docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest"
```

## Errores Comunes

### Error: Repository does not exist
**Causa**: Repos no creados o creados en región incorrecta
**Fix**: Ejecutar NOW-070 primero

### Error: no basic auth credentials
**Causa**: Login expirado (dura 12 horas)
**Fix**: Re-ejecutar `aws ecr get-login-password` y login

### Error: denied: Your authorization token has expired
**Causa**: Token expirado
**Fix**: Re-login a ECR

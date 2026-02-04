# NOW-078: Full Deployment Checklist

## Status: REFERENCE
## Priority: P0 - Master checklist

Este es el checklist completo para deployment desde una PC nueva.

---

## Pre-requisitos

- [ ] AWS CLI instalado y configurado
- [ ] Docker Desktop instalado y corriendo
- [ ] Node.js 20+ instalado
- [ ] Python 3.11+ instalado
- [ ] Git configurado

---

## Fase 1: Infraestructura AWS

### 1.1 Fix Terraform Config (NOW-073)
```bash
# Editar infrastructure/terraform/main.tf
# Cambiar region a us-east-2
```

### 1.2 Crear ECR Repositories (NOW-070)
```bash
aws ecr create-repository --repository-name chamba-mcp-server --region us-east-2
aws ecr create-repository --repository-name chamba-dashboard --region us-east-2
```

### 1.3 Crear S3 Bucket para Landing (NOW-074)
```bash
aws s3 mb s3://chamba-landing-ultravioleta --region us-east-2
```

---

## Fase 2: Fix Código

### 2.1 MCP Server Fixes (NOW-071)

```bash
# requirements.txt - websockets version
sed -i 's/websockets>=12.0/websockets>=15.0,<16/' mcp_server/requirements.txt

# x402/client.py - geth_poa_middleware
# (ver NOW-071 para código completo)
```

### 2.2 Dashboard Fixes (NOW-072)

```bash
# Crear .dockerignore
echo "node_modules
.git
dist
.env*" > dashboard/.dockerignore

# package.json - build script
sed -i 's/"build": "tsc && vite build"/"build": "vite build"/' dashboard/package.json
```

### 2.3 Test Fixes (NOW-076)

```bash
# timestamp.py - Tuple import
sed -i 's/from typing import Optional/from typing import Optional, Tuple/' \
  mcp_server/verification/checks/timestamp.py
```

---

## Fase 3: Build Docker Images

### 3.1 Build MCP Server
```bash
cd mcp_server
docker build --no-cache --platform linux/amd64 -t chamba-mcp-server:latest .
```

### 3.2 Build Dashboard
```bash
cd dashboard
docker build --no-cache --platform linux/amd64 \
  -t chamba-dashboard:latest \
  --build-arg VITE_API_URL=https://api.execution.market .
```

---

## Fase 4: Push to ECR (NOW-075)

```bash
# Login
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  518898403364.dkr.ecr.us-east-2.amazonaws.com

# Push MCP Server
docker tag chamba-mcp-server:latest \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest
docker push 518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest

# Push Dashboard
docker tag chamba-dashboard:latest \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest
docker push 518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest
```

---

## Fase 5: Landing Page (NOW-074)

```bash
# Subir landing page a S3
cd landing
aws s3 sync . s3://chamba-landing-ultravioleta/ --delete

# Crear CloudFront distribution
# (ver NOW-074 para configuración completa)

# Configurar DNS
# A record -> CloudFront distribution
```

---

## Fase 6: Verificación

### 6.1 Landing Page
```bash
curl -I https://execution.market
# Debe retornar 200 OK
```

### 6.2 Tests
```bash
docker run --rm chamba-mcp-server:latest python -m pytest tests/ -v
# Debe pasar 92%+ de tests
```

### 6.3 ECR Images
```bash
aws ecr list-images --repository-name chamba-mcp-server --region us-east-2
aws ecr list-images --repository-name chamba-dashboard --region us-east-2
# Debe mostrar latest tag
```

---

## Orden de Ejecución

1. NOW-073 (Terraform region)
2. NOW-070 (ECR repos)
3. NOW-071 (MCP Server fixes)
4. NOW-072 (Dashboard fixes)
5. NOW-076 (Test fixes)
6. NOW-075 (ECR push)
7. NOW-074 (CloudFront)

---

## Windows Específico

Ver **NOW-077** para notas de Windows:
- Usar `cmd //c` para Docker commands
- Usar `python` no `python3`
- Paths con backslash o forward slash

---

## Rollback

Si algo falla:
```bash
# Revertir a imagen anterior
docker pull 518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:previous
docker tag ... :latest
docker push ...

# Invalidar CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id <ID> \
  --paths "/*"
```

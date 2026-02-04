# NOW-082: API Subdomain Configuration

## Status: PENDING
## Priority: P0 - Required for production API

## Objetivo

Configurar `api.execution.market` para el MCP Server API.

## Opción A: Con ECS + ALB (recomendado para producción)

### 1. Crear Application Load Balancer

```bash
# Esto se crea con Terraform (infrastructure/terraform/)
terraform apply
```

### 2. Obtener ALB DNS Name

```bash
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?LoadBalancerName==`chamba-production-alb`].DNSName' \
  --output text
```

### 3. Crear DNS Record

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z05485241GVL9TJOHP0TM \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.execution.market",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "<ALB_HOSTED_ZONE_ID>",
          "DNSName": "<ALB_DNS_NAME>",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

## Opción B: Sin ECS (desarrollo/testing)

### Usar ngrok o similar para exponer local

```bash
# Correr MCP server localmente
cd mcp_server
uvicorn server:app --host 0.0.0.0 --port 8000

# En otra terminal
ngrok http 8000
```

## SSL Certificate

El ALB debe tener un certificado SSL para `api.execution.market`.

```bash
# Solicitar certificado (puede ser wildcard)
aws acm request-certificate \
  --domain-name "*.execution.market" \
  --validation-method DNS \
  --region us-east-2
```

## Verificar

```bash
# Health check
curl https://api.execution.market/health

# Debe retornar:
# {"status": "healthy", "version": "0.1.0"}
```

## CORS Configuration

El MCP server debe permitir requests desde el dashboard:

```python
# server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://execution.market",
        "http://localhost:3000"  # desarrollo
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

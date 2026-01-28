# NOW-204: Deploy a chamba.ultravioletadao.xyz

## Metadata
- **Prioridad**: P0 (CRÍTICO)
- **Fase**: Production Deployment
- **Dependencias**: NOW-202, NOW-203
- **Tiempo estimado**: 3-4 horas

## Descripción
Desplegar Chamba en producción en el dominio chamba.ultravioletadao.xyz.

## Opciones de Deployment

### Opción A: AWS ECS (Recomendado - igual que facilitator)
```bash
# Similar al facilitator x402-rs

# 1. Crear repositorios ECR
aws ecr create-repository --repository-name chamba-mcp-server
aws ecr create-repository --repository-name chamba-dashboard

# 2. Build y push imágenes
docker build -f Dockerfile.mcp -t chamba-mcp-server .
docker tag chamba-mcp-server:latest <account>.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server:latest

docker build -f Dockerfile.dashboard -t chamba-dashboard .
docker tag chamba-dashboard:latest <account>.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest
docker push <account>.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard:latest

# 3. Crear cluster ECS
aws ecs create-cluster --cluster-name chamba-production

# 4. Crear task definitions (ver terraform/)

# 5. Crear servicios
aws ecs create-service \
  --cluster chamba-production \
  --service-name chamba-api \
  --task-definition chamba-mcp-server:1 \
  --desired-count 1 \
  --launch-type FARGATE
```

### Opción B: Mac Mini Local (Rápido para MVP)
```bash
# En el Mac Mini nuevo

# 1. Clonar repo
git clone https://github.com/ultravioletadao/control-plane
cd control-plane/ideas/chamba

# 2. Configurar .env
cp .env.example .env
# Editar con credenciales reales

# 3. Levantar con docker compose
docker compose up -d

# 4. Configurar Cloudflare Tunnel para exponer
cloudflared tunnel create chamba
cloudflared tunnel route dns chamba chamba.ultravioletadao.xyz
cloudflared tunnel run chamba
```

### Opción C: Railway/Render (Más simple)
```bash
# 1. Conectar repo a Railway
# 2. Configurar variables de entorno
# 3. Deploy automático

# Railway detecta Dockerfile automáticamente
```

## DNS Configuration
```
# En Cloudflare (ultravioletadao.xyz)
chamba.ultravioletadao.xyz -> [IP o Tunnel]
api.chamba.ultravioletadao.xyz -> [IP o Tunnel] (opcional)
```

## SSL/TLS
- Cloudflare maneja SSL automáticamente
- O usar Let's Encrypt con certbot

## Variables de Entorno en Producción
```bash
# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# x402
CHAMBA_ESCROW_WALLET=0x...
CHAMBA_PRIVATE_KEY=...  # Para pagos a workers

# API
API_BASE_URL=https://chamba.ultravioletadao.xyz
CORS_ORIGINS=https://chamba.ultravioletadao.xyz

# Frontend
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_URL=https://chamba.ultravioletadao.xyz
```

## Health Check
```bash
# Verificar deployment
curl https://chamba.ultravioletadao.xyz/health
# Debe retornar: {"status": "healthy", ...}

curl https://chamba.ultravioletadao.xyz/docs
# Debe mostrar Swagger UI
```

## Criterios de Éxito
- [ ] https://chamba.ultravioletadao.xyz responde
- [ ] /health retorna status healthy
- [ ] /docs muestra Swagger UI
- [ ] Dashboard carga correctamente
- [ ] Login funciona
- [ ] Se pueden ver tareas (aunque estén vacías)

## Rollback Plan
```bash
# Si algo falla, revertir a versión anterior
docker compose down
git checkout HEAD~1
docker compose up -d
```

## ESTADO: 2026-01-25

### Infraestructura EXISTENTE
Todo el código de deployment ya está creado:

```
mcp_server/
├── Dockerfile                    # ✅ Multi-stage build, non-root user, health check
├── docker-compose.yml            # ✅ Development compose
├── docker-compose.prod.yml       # ✅ Production compose
└── requirements.txt              # ✅ Todas las dependencias

.github/workflows/
├── deploy.yml                    # ✅ AWS ECS deployment completo (306 líneas)
├── test.yml                      # ✅ Tests CI
└── pr-checks.yml                 # ✅ PR validation

terraform/
├── main.tf                       # ✅ ECS cluster, services, ALB
├── variables.tf                  # ✅ Variables configurables
└── outputs.tf                    # ✅ Outputs para CI/CD
```

### Workflow de Deploy (`deploy.yml`)
El workflow ya tiene:
- Jobs: test-mcp-server, test-dashboard, build-and-push, deploy, e2e-tests
- Build multi-arch para linux/amd64
- Push a ECR con tag latest y SHA
- Deploy a ECS con force-new-deployment
- E2E tests post-deployment

### BLOQUEADO: Requiere Acción del Usuario

```
1. AWS Credentials en GitHub Secrets:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_REGION (us-east-2)
   - AWS_ACCOUNT_ID

2. Crear recursos AWS (o aplicar terraform):
   - ECR repositories: chamba-mcp-server, chamba-dashboard
   - ECS cluster: chamba-production
   - ALB y target groups
   - Route 53 / CloudFlare DNS

3. Supabase credentials:
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - SUPABASE_SERVICE_KEY

4. x402 credentials:
   - CHAMBA_TREASURY_ADDRESS
   - X402_NETWORK=base
```

### Opciones de Deploy Rápido (sin AWS)

**Opción A: Mac Mini + Cloudflare Tunnel** (recomendado para MVP):
```bash
cd ideas/chamba
cp .env.example .env
# Editar .env con credenciales reales
docker compose -f docker-compose.prod.yml up -d
cloudflared tunnel create chamba
cloudflared tunnel route dns chamba chamba.ultravioletadao.xyz
cloudflared tunnel run chamba
```

**Opción B: Railway** (más simple):
1. Conectar repo a Railway
2. Configurar variables de entorno
3. Deploy automático detecta Dockerfile

### Criterios de Éxito Actualizados
- [x] Dockerfile MCP server listo
- [x] Dockerfile dashboard listo
- [x] docker-compose.prod.yml listo
- [x] GitHub Actions workflow listo
- [x] Terraform configs listas
- [ ] AWS credentials configuradas (ACCIÓN REQUERIDA)
- [ ] DNS configurado (ACCIÓN REQUERIDA)
- [ ] https://chamba.ultravioletadao.xyz responde
- [ ] /health retorna healthy
- [ ] /docs muestra Swagger UI

# NOW-001: Crear Dockerfile para MCP Server

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: Ninguna
- **Archivos a crear**: `mcp_server/Dockerfile`
- **Tiempo estimado**: 15-30 min

## Descripción
Crear un Dockerfile para el MCP Server de Chamba que permita deployar el servicio en AWS ECS.

## Contexto Técnico
- **Runtime**: Python 3.11
- **Framework**: FastAPI + MCP SDK
- **Puerto**: 8000
- **Base image**: `python:3.11-slim`

## Estructura del Proyecto MCP Server
```
mcp_server/
├── server.py          # Entry point
├── requirements.txt   # Dependencies
├── config/           # Configuration
└── integrations/     # x402, ERC-8004, etc.
```

## Código de Referencia

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Criterios de Éxito
- [ ] Dockerfile creado en `mcp_server/Dockerfile`
- [ ] `docker build` exitoso sin errores
- [ ] Container inicia y responde en `/health`
- [ ] Tamaño de imagen < 500MB
- [ ] No secrets hardcodeados en imagen

## Variables de Entorno Requeridas
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
X402_RPC_URL=
X402_PRIVATE_KEY=
```

## Comandos de Verificación
```bash
# Build
docker build -t chamba-mcp:latest mcp_server/

# Run locally
docker run -p 8000:8000 --env-file .env chamba-mcp:latest

# Test health
curl http://localhost:8000/health
```

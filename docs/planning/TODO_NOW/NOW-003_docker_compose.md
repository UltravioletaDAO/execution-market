# NOW-003: Crear docker-compose.yml para desarrollo local

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-001, NOW-002
- **Archivos a crear**: `docker-compose.yml`
- **Tiempo estimado**: 20-30 min

## Descripción
Crear docker-compose.yml que levante todo el stack de Execution Market localmente para desarrollo.

## Contexto Técnico
- **Servicios**: mcp-server, dashboard, supabase (opcional)
- **Networks**: chamba-network
- **Volumes**: Para persistencia local

## Código de Referencia

```yaml
version: '3.8'

services:
  mcp-server:
    build:
      context: ./mcp_server
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - X402_RPC_URL=${X402_RPC_URL}
      - X402_PRIVATE_KEY=${X402_PRIVATE_KEY}
      - ENVIRONMENT=development
    volumes:
      - ./mcp_server:/app  # Hot reload en dev
    networks:
      - chamba-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_SUPABASE_URL=${SUPABASE_URL}
      - VITE_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    depends_on:
      - mcp-server
    networks:
      - chamba-network

  # Optional: Local Supabase for full offline dev
  # supabase-db:
  #   image: supabase/postgres:15.1.0.117
  #   ports:
  #     - "5432:5432"
  #   environment:
  #     POSTGRES_PASSWORD: postgres
  #   volumes:
  #     - supabase-data:/var/lib/postgresql/data

networks:
  chamba-network:
    driver: bridge

volumes:
  supabase-data:
```

## .env.example Requerido

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...

# x402
X402_RPC_URL=https://mainnet.base.org
X402_PRIVATE_KEY=

# Environment
ENVIRONMENT=development
```

## Criterios de Éxito
- [ ] docker-compose.yml creado en root
- [ ] .env.example creado con todas las variables
- [ ] `docker-compose up` levanta ambos servicios
- [ ] Dashboard accesible en http://localhost:3000
- [ ] MCP Server accesible en http://localhost:8000
- [ ] Health checks pasan

## Comandos de Verificación
```bash
# Copiar env
cp .env.example .env
# Editar .env con valores reales

# Levantar todo
docker-compose up -d

# Ver logs
docker-compose logs -f

# Verificar servicios
curl http://localhost:8000/health
curl http://localhost:3000/

# Bajar todo
docker-compose down
```

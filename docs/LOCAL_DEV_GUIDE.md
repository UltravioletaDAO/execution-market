# Guía de Desarrollo Local - Execution Market

**Stack completo con Docker Compose** para desarrollo rápido sin esperas de GitHub Actions.

---

## 🚀 Quick Start (3 pasos)

```bash
# 1. Ya tienes el .env configurado con valores de demo
# Si necesitas regenerarlo:
# cp .env.docker.example .env

# 2. Levantar todos los servicios
make up

# 3. Abrir dashboard
# http://localhost:5173
```

**Listo!** En ~30 segundos tienes el stack completo corriendo.

---

## 📦 Servicios Incluidos

| Servicio | Puerto | URL | Descripción |
|----------|--------|-----|-------------|
| **Dashboard** | 5173 | http://localhost:5173 | React + Vite frontend |
| **MCP Server** | 8000 | http://localhost:8000 | FastAPI backend |
| **MCP Health** | 8000 | http://localhost:8000/health | Health check |
| **Supabase API** | 54321 | http://localhost:54321 | API Gateway (Kong) |
| **Supabase Studio** | 54322 | http://localhost:54322 | Admin UI (DB explorer) |
| **Email Testing** | 54323 | http://localhost:54323 | Inbucket (catch-all SMTP) |
| **PostgreSQL** | 54320 | localhost:54320 | Database directo |
| **Anvil** | 8545 | http://localhost:8545 | Local blockchain |
| **Redis** | 6379 | localhost:6379 | Cache y rate limiting |

---

## 🛠️ Comandos Útiles

### Servicios

```bash
make up          # Levantar todos los servicios
make down        # Parar todos los servicios
make restart     # Reiniciar todos los servicios
make status      # Ver estado de servicios
make urls        # Ver todas las URLs
```

### Logs

```bash
make logs-f              # Ver logs de todo (follow)
make logs-mcp            # Solo logs del MCP server
make logs-dashboard      # Solo logs del dashboard
make logs-db             # Solo logs de PostgreSQL
make logs-anvil          # Solo logs de Anvil
```

### Build

```bash
make build               # Build todas las imágenes
make rebuild             # Rebuild sin cache
make rebuild-mcp         # Rebuild solo MCP server
make rebuild-dashboard   # Rebuild solo dashboard
```

### Database

```bash
make db-shell            # Abrir psql en PostgreSQL
make migrate             # Correr migraciones
make seed                # Seed con datos de prueba
make db-reset            # ⚠️ Reset completo de DB
```

### Desarrollo

```bash
make dev                 # Dev mode con hot reload
make watch               # Dev + follow logs
make health              # Check health de todos los servicios
make shell               # Shell en MCP server container
make shell-dashboard     # Shell en dashboard container
```

### Testing

```bash
make test                # Todos los tests
make test-mcp            # Tests del MCP server
make test-dashboard      # Tests del dashboard
make lint                # Linters
make format              # Formatear código
```

### Blockchain

```bash
make anvil-console       # Anvil console (cast)
make contracts-deploy    # Deploy contracts a Anvil
make contracts-test      # Tests de contracts
make redis-cli           # Redis CLI
```

### Limpieza

```bash
make reset               # Reset todo y reiniciar
make clean               # ⚠️ Borrar TODOS los contenedores/volúmenes
make prune               # Limpiar recursos Docker no usados
```

---

## 🔄 Flujo de Desarrollo Rápido

### 1️⃣ Cambios en el Frontend (Dashboard)

**Opción A: Hot Reload (recomendado)**

```bash
# Levantar en modo dev (una vez)
make dev

# Editar código en dashboard/src/
# Los cambios se reflejan automáticamente en http://localhost:5173
```

**Opción B: Rebuild manual**

```bash
# Editar código
cd dashboard && code .

# Rebuild + restart
make rebuild-dashboard
make restart

# Refrescar navegador (Ctrl+Shift+R)
```

### 2️⃣ Cambios en el Backend (MCP Server)

**Opción A: Hot Reload (recomendado)**

```bash
# Levantar en modo dev (una vez)
make dev

# Editar código en mcp_server/
# Uvicorn detecta cambios y reinicia automáticamente
```

**Opción B: Rebuild manual**

```bash
# Editar código
cd mcp_server && code .

# Rebuild + restart
make rebuild-mcp
make restart

# Verificar health
curl http://localhost:8000/health
```

### 3️⃣ Cambios en Base de Datos

```bash
# Agregar migración en supabase/migrations/
# Ejemplo: 999_new_feature.sql

# Recrear DB
make db-reset

# O aplicar manualmente
make db-shell
# \i /docker-entrypoint-initdb.d/999_new_feature.sql
```

### 4️⃣ Verificar Todo Funciona

```bash
# Health check de todos los servicios
make health

# Logs de todos los servicios
make logs-f

# Status de contenedores
make status
```

---

## 🐛 Troubleshooting

### Puerto ocupado

```bash
# Ver qué proceso usa el puerto
netstat -ano | findstr :5173
netstat -ano | findstr :8000

# Matar proceso
taskkill /F /PID <PID>

# O cambiar puerto en docker-compose.yml
```

### Contenedor no levanta

```bash
# Ver logs del servicio específico
make logs-mcp
make logs-dashboard

# Reconstruir sin cache
make rebuild-mcp
# o
make rebuild-dashboard

# Reset completo
make reset
```

### Base de datos no responde

```bash
# Ver logs
make logs-db

# Verificar que esté corriendo
make status

# Reset DB
make db-reset
```

### "Cannot connect to Docker daemon"

```bash
# Iniciar Docker Desktop
# Esperar a que diga "Docker Desktop is running"

# Verificar
docker ps

# Reintentar
make up
```

### Cache de build antiguo

```bash
# Rebuild sin cache
make rebuild

# O solo un servicio
make rebuild-mcp
make rebuild-dashboard
```

---

## 🔐 Credenciales de Demo

### Supabase (local)

```bash
URL: http://localhost:54321
Anon Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
Service Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
```

### PostgreSQL (local)

```bash
Host: localhost
Port: 54320
User: postgres
Password: postgres
Database: postgres
```

### Anvil (blockchain local)

```bash
RPC: http://localhost:8545
Chain ID: 31337
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
Private Key: [ver .env para la key de test]
Balance: 10,000 ETH (cada cuenta)
```

### Redis (local)

```bash
URL: redis://localhost:6379/0
Password: (ninguno)
```

---

## 📊 Comparación: Local vs GitHub Actions

| Aspecto | GitHub Actions | Docker Local |
|---------|----------------|--------------|
| **Tiempo de deploy** | ~20 minutos | ~30 segundos |
| **Iteraciones por hora** | 3 | ∞ |
| **Hot reload** | ❌ | ✅ |
| **Costo** | $0 (pero lento) | $0 |
| **Debugging** | Difícil (logs remotos) | Fácil (logs locales) |
| **Requiere push** | Sí | No |
| **Internet** | Requerido | Solo para deps |

**Resultado**: Con Docker local vas **40x más rápido** que con GitHub Actions para desarrollo.

---

## 🎯 Workflow Recomendado

```bash
# 1. Levantar stack una vez al día
make dev

# 2. Ver logs en terminal aparte
make logs-f

# 3. Editar código (hot reload automático)
# - dashboard/src/
# - mcp_server/

# 4. Probar en navegador
# http://localhost:5173

# 5. Cuando funcione TODO:
git add .
git commit -m "feat: nueva feature testeada localmente"
git push

# 6. GitHub Actions hace el deploy a producción
# (solo cuando estás seguro que funciona)
```

---

## 🌐 Conectarse a Supabase Cloud (opcional)

Si quieres usar la DB de producción en vez de local:

```bash
# Editar .env
SUPABASE_URL=https://puyhpytmtkyevnxffksl.supabase.co
SUPABASE_ANON_KEY=<tu-anon-key-de-produccion>
SUPABASE_SERVICE_KEY=<tu-service-key-de-produccion>

# Restart
make restart
```

⚠️ **Cuidado**: Esto escribe en la DB de producción.

---

## 📝 Notas

- El archivo `.env` **nunca** se commitea (está en `.gitignore`)
- Las API keys de demo solo funcionan localmente
- Anvil se resetea cada vez que haces `make down` (blockchain efímero)
- Para data persistente, usar volúmenes Docker (ya configurados)
- Supabase Studio es súper útil para explorar la DB: http://localhost:54322

---

## 🆘 Ayuda

```bash
# Ver todos los comandos disponibles
make help

# Ver estado de servicios
make status

# Ver URLs
make urls

# Health check
make health
```

**Documentación completa:**
- `README.md` - Overview general
- `CLAUDE.md` - Instrucciones para Claude
- `docker-compose.yml` - Configuración de servicios
- `Makefile` - Todos los comandos disponibles

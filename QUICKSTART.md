# Quick Start - Desarrollo Local

## ✅ Stack Actual (Funcionando)

| Servicio | Status | URL/Puerto |
|----------|--------|------------|
| **Dashboard** | ✅ Running | http://localhost:5173 |
| **MCP Server** | ✅ Healthy | http://localhost:8000 |
| **Redis** | ✅ Running | localhost:6379 |
| **Anvil** | ✅ Running | http://localhost:8545 |
| **Supabase** | ✅ Cloud | https://YOUR_PROJECT_REF.supabase.co |

---

## 🚀 Comandos Esenciales

### Iniciar Todo

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Ver Logs

```bash
# Todos los servicios
docker compose -f docker-compose.dev.yml logs -f

# Solo uno
docker compose -f docker-compose.dev.yml logs -f mcp-server
docker compose -f docker-compose.dev.yml logs -f dashboard
```

### Detener Todo

```bash
docker compose -f docker-compose.dev.yml down
```

### Rebuild Después de Cambios

```bash
# MCP Server
docker compose -f docker-compose.dev.yml up -d --build mcp-server

# Dashboard (auto-reload, no rebuild necesario)
# Solo edita los archivos en dashboard/src/ y recarga navegador
```

---

## 📂 Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `.env` | **Configuración activa** (usa Supabase Cloud) |
| `.env.cloud` | Template para desarrollo con Supabase Cloud |
| `.env.docker.example` | Template para stack completo local (complejo) |
| `docker-compose.dev.yml` | **Stack simplificado** (4 servicios) |
| `docker-compose.yml` | Stack completo Supabase (complejo, no usar) |

---

## 🔄 Workflow de Desarrollo

### 1. Frontend (Dashboard)

```bash
# Editar código
cd dashboard/src
# Cambios se reflejan automáticamente (hot reload)
# Refrescar navegador: Ctrl+Shift+R
```

**No necesitas rebuild** - Vite tiene hot reload automático.

### 2. Backend (MCP Server)

```bash
# Editar código
cd mcp_server

# Rebuild + restart
docker compose -f docker-compose.dev.yml up -d --build mcp-server

# Verificar health
curl http://localhost:8000/health
```

---

## 🌐 URLs Útiles

- **Dashboard**: http://localhost:5173
- **MCP Health**: http://localhost:8000/health
- **MCP Docs**: http://localhost:8000/docs (Swagger UI)
- **Anvil RPC**: http://localhost:8545
- **Supabase Dashboard**: https://supabase.com/dashboard/project/YOUR_PROJECT_REF

---

## 🐛 Troubleshooting

### Dashboard no carga

```bash
# Ver logs
docker compose -f docker-compose.dev.yml logs dashboard

# Restart
docker compose -f docker-compose.dev.yml restart dashboard
```

### MCP Server unhealthy

```bash
# Verificar health
curl http://localhost:8000/health | python -m json.tool

# Ver logs
docker compose -f docker-compose.dev.yml logs mcp-server

# Verificar env vars
docker compose -f docker-compose.dev.yml exec mcp-server env | grep SUPABASE
```

### Puerto ocupado

```bash
# Ver qué proceso usa el puerto
netstat -ano | findstr :5173
netstat -ano | findstr :8000

# Matar proceso (Windows)
taskkill /F /PID <PID>
```

### Reset completo

```bash
# Bajar todo y limpiar volúmenes
docker compose -f docker-compose.dev.yml down -v

# Levantar de nuevo
docker compose -f docker-compose.dev.yml up -d
```

---

## ⚡ Comparación vs GitHub Actions

| Métrica | GitHub Actions | Docker Local |
|---------|----------------|--------------|
| **Deploy time** | ~20 minutos | ~30 segundos |
| **Iteraciones/hora** | 3 | ∞ |
| **Hot reload** | ❌ | ✅ |
| **Debugging** | Difícil | Fácil |
| **Costo** | $0 (lento) | $0 (rápido) |

**Resultado**: 40x más rápido 🚀

---

## 📝 Notas

- `.env` **nunca** se commitea (está en `.gitignore`)
- Usa Supabase Cloud en desarrollo (más confiable que local)
- Anvil se resetea cada vez que bajas el stack (blockchain efímero)
- Dashboard tiene auto-reload, MCP Server necesita rebuild

---

## 🔗 Más Info

- **Guía completa**: `docs/LOCAL_DEV_GUIDE.md`
- **CLAUDE.md**: Instrucciones del proyecto
- **README.md**: Documentación general

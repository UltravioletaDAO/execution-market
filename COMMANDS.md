# Quick Commands Reference

Comandos rápidos para desarrollo diario con Execution Market.

---

## 🧪 Testing

### Correr Todos los Tests

```powershell
# PowerShell
.\scripts\test-local.ps1

# Git Bash
bash scripts/test-local.sh

# Claude Code command
/test
```

**Resultado**: Corre backend (pytest) + frontend (vitest) + E2E (playwright) en ~5-7 min

### Tests Rápidos (Solo Unit)

```powershell
# PowerShell
.\scripts\test-local.ps1 -SkipE2E

# Claude Code command
/test-quick
```

**Resultado**: Solo unit tests, sin E2E. ~2-3 min.

### Solo E2E

```powershell
.\scripts\test-local.ps1 -SkipUnit
```

**Resultado**: Solo E2E tests. ~3-5 min.

---

## 🚀 Desarrollo Local

### Iniciar Stack

```powershell
# PowerShell/CMD
docker compose -f docker-compose.dev.yml up -d

# Claude Code command
/dev-start
```

**Servicios disponibles:**
- Dashboard: http://localhost:5173
- MCP Server: http://localhost:8000
- Anvil: http://localhost:8545

### Ver Logs

```powershell
# Todos los servicios
docker compose -f docker-compose.dev.yml logs -f

# Claude Code command
/dev-logs

# Servicio específico
docker compose -f docker-compose.dev.yml logs -f mcp-server
docker compose -f docker-compose.dev.yml logs -f dashboard
```

### Detener Stack

```powershell
# PowerShell/CMD
docker compose -f docker-compose.dev.yml down

# Claude Code command
/dev-stop
```

### Rebuild Servicios

```powershell
# MCP Server (después de cambios en código)
docker compose -f docker-compose.dev.yml up -d --build mcp-server

# Dashboard (tiene hot reload, no necesita rebuild)
# Solo refresca el navegador: Ctrl+Shift+R
```

---

## 🔍 Debug & Inspección

### Health Checks

```powershell
# MCP Server health
curl http://localhost:8000/health | python -m json.tool

# Ver estado de servicios
docker compose -f docker-compose.dev.yml ps

# Ver logs de un servicio
docker compose -f docker-compose.dev.yml logs mcp-server --tail 50
```

### Acceder a Contenedores

```powershell
# Shell en MCP Server
docker compose -f docker-compose.dev.yml exec mcp-server bash

# Shell en Dashboard
docker compose -f docker-compose.dev.yml exec dashboard sh

# PostgreSQL (vía psql directo)
# Conecta a Supabase Cloud con DBeaver/TablePlus
# Host: db.puyhpytmtkyevnxffksl.supabase.co
# Port: 5432
```

---

## 📦 Tests Individuales

### Backend (pytest)

```powershell
cd mcp_server

# Todos los tests
pytest -v

# Con coverage
pytest --cov=. -v

# Test específico
pytest tests/test_specific.py -v

# Con más detalle
pytest tests/test_specific.py -vv --tb=long
```

### Frontend (vitest)

```powershell
cd dashboard

# Modo watch (auto-rerun)
npm run test

# Run once
npm run test:run

# Con coverage
npm run test:coverage
```

### E2E (playwright)

```powershell
cd e2e

# Todos los tests
npm run test

# Con UI (visual)
npm run test:ui

# Con navegador visible
npm run test:headed

# Debug mode
npm run test:debug

# Test específico
npm run test tests/auth.spec.ts

# Ver reporte
npm run report
```

---

## 🔧 Linting & Formatting

### Backend (Python)

```powershell
cd mcp_server

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy . --ignore-missing-imports
```

### Frontend (TypeScript)

```powershell
cd dashboard

# Lint
npm run lint

# Type check
npm run typecheck
```

---

## 📊 Workflow Completo

```powershell
# 1. Iniciar stack local
docker compose -f docker-compose.dev.yml up -d

# 2. Hacer cambios en código
code dashboard/src/MyComponent.tsx

# 3. Ver cambios en navegador (hot reload)
# http://localhost:5173

# 4. Commit
git add .
git commit -m "feat: nueva feature"

# 5. Correr tests ANTES de push
.\scripts\test-local.ps1

# 6. Si todos pasan → Push
git push

# 7. GitHub Actions confirma (20 min)
```

---

## ⌨️ Aliases Sugeridos (PowerShell)

Agrega a tu `$PROFILE`:

```powershell
# Test commands
function Test-All { .\scripts\test-local.ps1 }
function Test-Quick { .\scripts\test-local.ps1 -SkipE2E }

# Docker commands
function Dev-Up { docker compose -f docker-compose.dev.yml up -d }
function Dev-Down { docker compose -f docker-compose.dev.yml down }
function Dev-Logs { docker compose -f docker-compose.dev.yml logs -f $args }
function Dev-PS { docker compose -f docker-compose.dev.yml ps }

# Shortcuts
Set-Alias -Name test -Value Test-All
Set-Alias -Name tq -Value Test-Quick
Set-Alias -Name dup -Value Dev-Up
Set-Alias -Name ddown -Value Dev-Down
Set-Alias -Name dlogs -Value Dev-Logs
Set-Alias -Name dps -Value Dev-PS
```

**Uso después de aliases:**

```powershell
test      # .\scripts\test-local.ps1
tq        # .\scripts\test-local.ps1 -SkipE2E
dup       # docker compose up
ddown     # docker compose down
dlogs     # docker compose logs -f
```

---

## 📚 Documentación

- **QUICKSTART.md** - Guía rápida de inicio
- **TEST_WORKFLOW.md** - Guía completa de testing
- **README.md** - Documentación general del proyecto
- **CLAUDE.md** - Instrucciones específicas para Claude Code
- **.claude/commands/README.md** - Comandos personalizados

---

## 💡 Tips

1. **Hot reload funciona** - Dashboard se recarga automáticamente al editar
2. **MCP necesita rebuild** - Después de cambios en Python
3. **Tests antes de push** - Ahorra 40 min de iteraciones
4. **Logs son tu amigo** - `docker compose logs -f` muestra todo
5. **Health check primero** - Verifica que servicios estén ok antes de debuggear

---

¿Necesitas más comandos? Edita `.claude/commands/` o crea aliases en tu shell.

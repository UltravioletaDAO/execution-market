# Workflow de Testing Local

## 🎯 Objetivo

Correr TODOS los tests localmente ANTES de hacer push, para no esperar 20 minutos en GitHub Actions solo para descubrir que algo falló.

---

## 🚀 Uso Rápido

### **Opción 1: Todo en Uno (Recomendado)**

```powershell
# PowerShell (Windows)
.\scripts\test-local.ps1
```

```bash
# Git Bash
bash scripts/test-local.sh
```

**Esto hace:**
1. ✅ Para Docker
2. ✅ Tests backend (pytest) → `test-backend.log`
3. ✅ Tests frontend (vitest) → `test-frontend.log`
4. ✅ Levanta Docker
5. ✅ Tests E2E (playwright) → `test-e2e.log`
6. ✅ Para Docker
7. ✅ Reporte final

**Tiempo**: ~5-10 minutos (vs 20 min en CI)

---

## 🎛️ Opciones Avanzadas

### **Dejar Stack Corriendo (para debug)**

```powershell
.\scripts\test-local.ps1 -KeepRunning
```

Útil cuando:
- Tests E2E fallan y quieres investigar en el navegador
- Necesitas revisar logs del MCP
- Quieres seguir desarrollando después

### **Solo Tests Rápidos (unitarios)**

```powershell
.\scripts\test-local.ps1 -SkipE2E
```

**Tiempo**: ~2-3 minutos

Útil cuando:
- Hiciste cambios pequeños en backend/frontend
- Solo quieres verificación rápida antes de commit

### **Solo Tests E2E**

```powershell
.\scripts\test-local.ps1 -SkipUnit
```

**Tiempo**: ~3-5 minutos

Útil cuando:
- Solo cambiaste algo en el dashboard
- Los tests unitarios ya pasaron

---

## 📊 Interpretando Resultados

### ✅ **Todo Pasó**

```
================================
Resumen de Tests
================================
✓ Backend Tests (pytest)
✓ Frontend Tests (vitest)
✓ E2E Tests (playwright)

✓ TODOS LOS TESTS PASARON
Listo para hacer push!
```

**Acción**: `git push` con confianza 🚀

### ❌ **Algo Falló**

```
================================
Resumen de Tests
================================
✗ Backend Tests (pytest)
✓ Frontend Tests (vitest)
✓ E2E Tests (playwright)

✗ ALGUNOS TESTS FALLARON
Revisa los logs antes de hacer push
```

**Acción**:
1. Revisar logs: `test-backend.log`, `test-frontend.log`, `test-e2e.log`
2. Arreglar el problema
3. Re-correr tests

---

## 🔍 Debugging Tests Fallidos

### **Backend (pytest) Falló**

```powershell
# Ver detalles
cat test-backend.log

# Correr solo ese test
cd mcp_server
pytest tests/test_specific.py -v

# Correr con más detalle
pytest tests/test_specific.py -vv --tb=long
```

### **Frontend (vitest) Falló**

```powershell
# Ver detalles
cat test-frontend.log

# Correr en modo watch
cd dashboard
npm run test

# Correr con coverage
npm run test:coverage
```

### **E2E (playwright) Falló**

```powershell
# Ver detalles
cat test-e2e.log

# Ver reporte visual
cd e2e
npm run report

# Correr con UI (ver tests en vivo)
npm run test:ui

# Correr en modo debug
npm run test:debug

# Correr test específico
npm run test tests/auth.spec.ts
```

**Tip**: Playwright genera screenshots y videos de tests fallidos en `e2e/test-results/`

---

## 🎬 Workflow Completo Recomendado

```powershell
# 1. Hacer cambios en código
code dashboard/src/MyComponent.tsx

# 2. Commit local
git add .
git commit -m "feat: nueva feature"

# 3. Correr tests ANTES de push
.\scripts\test-local.ps1

# 4. Si pasan → Push
git push

# 5. GitHub Actions hace deploy (ya sabemos que pasa)
```

**Resultado**: De 20% de éxito en CI a 95% de éxito 📈

---

## ⚙️ Configuración Inicial

### **Primera Vez**

```powershell
# Instalar dependencias de tests
cd mcp_server
pip install -e ".[dev]"

cd ../dashboard
npm install --legacy-peer-deps

cd ../e2e
npm install
npx playwright install
```

Esto se hace **automáticamente** la primera vez que corres `test-local.ps1`

---

## 🆚 Comparación

| Aspecto | Sin Tests Locales | Con Tests Locales |
|---------|-------------------|-------------------|
| **Tiempo de feedback** | 20 minutos | 5 minutos |
| **Costo de fallo** | Push → Wait → Fail → Fix → Repeat | Test → Fix → Test → Push |
| **Iteraciones/hora** | 3 | 12 |
| **Confianza en push** | 20% | 95% |
| **Frustración** | Alta 😤 | Baja 😊 |

---

## 📋 Checklist Pre-Push

- [ ] Código funciona localmente
- [ ] `.\scripts\test-local.ps1` pasa
- [ ] Commit con mensaje descriptivo
- [ ] Push a GitHub
- [ ] GitHub Actions confirma (20 min)
- [ ] Merge a main

**Tiempo total**: 25 min (vs 40+ min con múltiples re-pushes)

---

## 💡 Tips

1. **Corre tests antes de cada push** - ahorra tiempo
2. **Usa `-SkipE2E` para cambios pequeños** - feedback en 2 min
3. **Usa `-KeepRunning` para debugging** - inspecciona el estado
4. **Lee los logs** - tienen el stack trace completo
5. **Playwright UI mode es tu amigo** - ves exactamente qué falla

---

## 🆘 Problemas Comunes

### Tests E2E no encuentran el dashboard

```powershell
# Verificar que Docker levantó
docker compose -f docker-compose.dev.yml ps

# Ver logs
docker compose -f docker-compose.dev.yml logs dashboard
```

### pytest no encuentra módulos

```powershell
cd mcp_server
pip install -e ".[dev]"
```

### Playwright dice "browser not found"

```powershell
cd e2e
npx playwright install
```

---

**¿Preguntas?** Ver `QUICKSTART.md` o `docs/LOCAL_DEV_GUIDE.md`

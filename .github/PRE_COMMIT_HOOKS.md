# Pre-Commit Hooks - Execution Market

## 🎯 Propósito

Este proyecto usa Git hooks para **prevenir errores de CI** ejecutando verificaciones automáticas antes de cada commit.

## ✨ Qué Hace

El pre-commit hook ejecuta automáticamente:

### Python (mcp_server/)
1. **`ruff format`** - Formatea código automáticamente (PEP 8)
2. **`ruff check`** - Verifica linting (imports no usados, variables, etc.)

### TypeScript (dashboard/)
1. **`eslint`** - Verifica reglas de estilo
2. **`tsc --noEmit`** - Verifica tipos de TypeScript

## 📦 Instalación

El hook ya está instalado en `.git/hooks/pre-commit`. Si lo eliminaste o clonaste el repo de nuevo:

```bash
# Copiar el hook desde el template (si existe)
cp .github/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# O ejecutar el script de setup
./scripts/setup-hooks.sh
```

## 🚀 Uso

El hook se ejecuta **automáticamente** cada vez que haces `git commit`. No necesitas hacer nada especial.

### Flujo Normal

```bash
git add .
git commit -m "feat: add new feature"
```

**Output esperado:**
```
🔍 Running pre-commit checks...
📝 Python files to check:
mcp_server/api/routes.py
🔧 Running ruff format...
🔍 Running ruff check...
📝 TypeScript files to check:
dashboard/src/components/NewComponent.tsx
🔍 Running ESLint...
🔍 Running TypeScript check...
✅ All pre-commit checks passed
[main abc1234] feat: add new feature
 2 files changed, 50 insertions(+)
```

### Si Hay Errores

```bash
git commit -m "broken code"
```

**Output con error:**
```
🔍 Running pre-commit checks...
📝 Python files to check:
mcp_server/api/routes.py
🔧 Running ruff format...
🔍 Running ruff check...
❌ Ruff check failed for api/routes.py
❌ Pre-commit checks failed with 1 error(s)
💡 Tip: Fix the errors above and try again
```

El commit **NO se ejecuta** hasta que arregles los errores.

## 🔧 Requisitos

### Python
- **ruff** instalado: `pip install ruff`
- Si no está instalado, el hook muestra warning pero permite el commit (CI podría fallar)

### TypeScript
- **node_modules** en `dashboard/`: `cd dashboard && npm install`
- Si no existe, el hook muestra warning pero permite el commit

## ⚙️ Configuración

### Desactivar Temporalmente

Si necesitas hacer un commit SIN verificaciones (NO recomendado):

```bash
git commit --no-verify -m "emergency fix"
```

### Personalizar el Hook

Edita `.git/hooks/pre-commit` para ajustar el comportamiento:

```bash
# Ejemplo: Cambiar a solo warnings en vez de errores
# Línea 95, cambiar:
ERRORS=$((ERRORS + 1))
# Por:
echo -e "${YELLOW}⚠️  Warning: issues found but allowing commit${NC}"
```

## 📋 Checklist para Nuevos Desarrolladores

1. ✅ Clonar el repo
2. ✅ `cd mcp_server && pip install ruff`
3. ✅ `cd dashboard && npm install`
4. ✅ Verificar que el hook existe: `ls -la .git/hooks/pre-commit`
5. ✅ Probar: `git commit --allow-empty -m "test"`

## 🐛 Troubleshooting

### "ruff not found"

```bash
cd mcp_server
pip install ruff
# O
python -m pip install ruff
```

### "npx: command not found"

```bash
cd dashboard
npm install
```

### "Permission denied: .git/hooks/pre-commit"

```bash
chmod +x .git/hooks/pre-commit
```

### Hook no se ejecuta

```bash
# Verificar que existe
ls -la .git/hooks/pre-commit

# Verificar permisos
chmod +x .git/hooks/pre-commit

# Probar manualmente
.git/hooks/pre-commit
```

## 🎓 Recursos

- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [ESLint Documentation](https://eslint.org/)
- [TypeScript Compiler Options](https://www.typescriptlang.org/tsconfig)

## 📝 Notas

- El hook **re-formatea automáticamente** archivos Python con ruff
- Los archivos re-formateados se **re-stagean automáticamente**
- TypeScript/ESLint **NO auto-formatean** (solo verifican)
- Warnings de ESLint (react-refresh) **NO bloquean** el commit
- Solo **errores críticos** bloquean el commit

## 🚨 Emergencias

Si el hook está causando problemas y necesitas desactivarlo temporalmente:

```bash
# Opción 1: Commit sin verificación
git commit --no-verify -m "message"

# Opción 2: Renombrar el hook (desactiva permanentemente)
mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled

# Opción 3: Eliminar el hook
rm .git/hooks/pre-commit
```

**IMPORTANTE:** Recuerda reactivarlo después:

```bash
mv .git/hooks/pre-commit.disabled .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```
# Test pre-commit hook

# Claude Code Custom Commands

Comandos rápidos para desarrollo con Execution Market.

## Comandos Disponibles

### 🧪 Testing

```bash
# Correr TODOS los tests (backend + frontend + E2E)
/test

# Correr solo tests rápidos (sin E2E) - ~2 min
/test-quick
```

### 🚀 Desarrollo Local

```bash
# Iniciar stack de desarrollo (Docker)
/dev-start

# Ver logs en tiempo real
/dev-logs

# Detener stack
/dev-stop
```

## Uso

Simplemente escribe el comando en el chat de Claude Code:

```
/test
```

O usa el equivalente PowerShell directamente:

```powershell
.\scripts\test-local.ps1
```

## Scripts Manuales

Si los comandos `/` no funcionan, ejecuta directamente:

```powershell
# PowerShell
.\scripts\test-local.ps1
.\scripts\test-local.ps1 -SkipE2E

# Bash
bash scripts/test-local.sh
bash .claude/commands/test.sh
```

## Configuración

Los scripts están en `.claude/commands/` y son simples wrappers a los scripts principales en `scripts/`.

Para crear nuevos comandos, agrega un archivo `.sh` en este directorio con el formato:

```bash
#!/bin/bash
# Quick command: /nombre-comando
# Descripción del comando
tu-comando-aqui
```

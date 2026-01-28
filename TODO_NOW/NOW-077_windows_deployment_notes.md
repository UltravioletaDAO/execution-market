# NOW-077: Windows Deployment Notes

## Status: REFERENCE
## Priority: P0 - Critical for Windows users

## Docker Commands en Windows

En Windows con Git Bash, los comandos de Docker a veces no retornan output.
Usar `cmd //c` wrapper:

```bash
# MAL - puede no mostrar output
docker build -t myimage .

# BIEN - siempre muestra output
cmd //c "docker build -t myimage ."
```

## Paths en Windows

```bash
# CORRECTO - Windows paths
Z:\ultravioleta\dao\control-plane
cd /d Z:\ultravioleta\dao\control-plane

# INCORRECTO - Linux paths (fallan en Windows)
/mnt/z/ultravioleta/dao/control-plane
```

## Python Command

```bash
# Windows (Git Bash, CMD, PowerShell)
python script.py
python -m pytest

# WSL/Linux/Mac
python3 script.py
python3 -m pytest
```

## Docker Build con Paths Windows

```bash
# Cambiar directorio y build en un comando
cmd //c "cd /d Z:\path\to\project && docker build -t image:tag ."
```

## ECR Login en Windows

```bash
# El pipe funciona diferente en Windows
aws ecr get-login-password --region us-east-2 | \
  cmd //c "docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com"
```

## Timeouts

Docker builds pueden ser lentos en Windows. Usar timeouts largos:
- npm install: ~4 minutos
- Full build: ~5-10 minutos

## Docker Desktop

Asegurar que Docker Desktop está corriendo antes de cualquier operación:

```bash
# Verificar Docker está corriendo
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "Docker NOT running"
```

## WSL vs Native Windows

- **Native Windows (recomendado para este proyecto)**: Usa `cmd //c` para Docker
- **WSL**: Usa comandos normales de Linux, pero paths son diferentes

## Troubleshooting

### "Cannot connect to Docker daemon"
1. Abrir Docker Desktop
2. Esperar a que inicie completamente
3. Verificar con `docker ps`

### Build no muestra output
Usar `cmd //c "docker build ... 2>&1"`

### Permission denied
Ejecutar terminal como Administrador si es necesario

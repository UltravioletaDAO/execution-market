# NOW-070: Create ECR Repositories

## Status: REQUIRED
## Priority: P0 - Blocker for deployment

## Problem
Los repositorios ECR deben crearse en **us-east-2** (misma región que el Terraform backend y la infraestructura). Si se crean en us-east-1, el push fallará.

## Commands

```bash
# Crear repositorios en us-east-2 (NO us-east-1)
aws ecr create-repository --repository-name chamba-mcp-server --region us-east-2
aws ecr create-repository --repository-name chamba-dashboard --region us-east-2
```

## Verificar

```bash
# Listar repos para confirmar
aws ecr describe-repositories --region us-east-2 --query 'repositories[*].repositoryUri'
```

## Output Esperado

```
518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-mcp-server
518898403364.dkr.ecr.us-east-2.amazonaws.com/chamba-dashboard
```

## Errores Comunes

**Error**: `The repository with name 'X' does not exist in the registry`
**Causa**: Repos creados en región incorrecta
**Fix**: Crear en us-east-2, no us-east-1

## Dependencias
- AWS CLI configurado
- Credenciales con permisos ECR

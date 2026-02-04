# NOW-005: GitHub Actions CI/CD

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-004
- **Archivos a crear**: `.github/workflows/deploy.yml`
- **Tiempo estimado**: 1-2 horas

## Descripción
Crear pipeline de CI/CD con GitHub Actions para deploy automático a AWS ECS.

## Contexto Técnico
- **Trigger**: Push a `main` branch
- **Steps**: Test → Build → Push ECR → Deploy ECS
- **Environments**: staging, production

## Código de Referencia

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
  ECS_CLUSTER: chamba-production

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd mcp_server
          pip install -r requirements.txt
          pip install pytest

      - name: Run tests
        run: |
          cd mcp_server
          pytest tests/ -v

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      mcp-image: ${{ steps.build-mcp.outputs.image }}
      dashboard-image: ${{ steps.build-dashboard.outputs.image }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push MCP Server
        id: build-mcp
        run: |
          IMAGE_TAG="${{ env.ECR_REGISTRY }}/chamba-mcp:${{ github.sha }}"
          docker build --no-cache -t $IMAGE_TAG mcp_server/
          docker push $IMAGE_TAG
          echo "image=$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Build and push Dashboard
        id: build-dashboard
        run: |
          IMAGE_TAG="${{ env.ECR_REGISTRY }}/chamba-dashboard:${{ github.sha }}"
          docker build --no-cache -t $IMAGE_TAG dashboard/
          docker push $IMAGE_TAG
          echo "image=$IMAGE_TAG" >> $GITHUB_OUTPUT

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy MCP Server to ECS
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service mcp-server \
            --force-new-deployment

      - name: Deploy Dashboard to ECS
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service dashboard \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services mcp-server dashboard

      - name: Health check
        run: |
          sleep 30
          curl -f https://api.execution.market/health || exit 1
          curl -f https://app.execution.market/ || exit 1
```

## GitHub Secrets Requeridos

```
AWS_ACCOUNT_ID=123456789012
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

## Criterios de Éxito
- [ ] Workflow file creado
- [ ] Secrets configurados en GitHub
- [ ] Push a main triggerea el pipeline
- [ ] Tests pasan
- [ ] Images se pushean a ECR
- [ ] ECS services se actualizan
- [ ] Health checks pasan post-deploy

## Workflow Stages
```
[Push to main]
      ↓
   [Test]
      ↓
[Build & Push to ECR]
      ↓
[Deploy to ECS]
      ↓
[Health Check]
      ↓
   [Done]
```

## Comandos de Verificación
```bash
# Ver workflows
gh workflow list

# Trigger manual
gh workflow run deploy.yml -f environment=staging

# Ver status
gh run list --workflow=deploy.yml

# Ver logs
gh run view <run-id> --log
```

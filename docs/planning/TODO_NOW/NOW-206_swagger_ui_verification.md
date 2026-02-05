# NOW-206: Verificar y Mejorar Swagger UI

## Metadata
- **Prioridad**: P1
- **Fase**: Documentation
- **Dependencias**: Ninguna
- **Archivos**: `mcp_server/server.py`, `mcp_server/api.py`
- **Tiempo estimado**: 30 minutos

## Descripción
FastAPI incluye Swagger UI por defecto. Verificar que esté habilitado y mejorar la documentación.

## Estado Actual
FastAPI automáticamente expone:
- `/docs` - Swagger UI
- `/redoc` - ReDoc
- `/openapi.json` - OpenAPI spec

## Verificación
```bash
# Iniciar servidor
cd ideas/chamba/mcp_server
uvicorn api:app --reload --port 8000

# Verificar endpoints
curl http://localhost:8000/docs
curl http://localhost:8000/openapi.json
```

## Mejoras a Implementar

### 1. Metadata en FastAPI app
```python
# api.py
from fastapi import FastAPI

app = FastAPI(
    title="Execution Market API",
    description="""
    ## Human Execution Layer for AI Agents

    Execution Market connects AI agents with human workers for physical-world tasks.

    ### Features
    - **x402 Payments**: Gasless stablecoin payments via facilitator
    - **A2A Protocol**: Agent-to-Agent communication (v0.3.0)
    - **MCP Tools**: Model Context Protocol integration
    - **Real-time Updates**: WebSocket notifications

    ### Authentication
    - API Key via `X-API-Key` header
    - Bearer token via `Authorization` header
    - ERC-8004 identity tokens (coming soon)
    """,
    version="0.1.0",
    contact={
        "name": "Ultravioleta DAO",
        "url": "https://ultravioletadao.xyz",
        "email": "ultravioletadao@gmail.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
```

### 2. Tags para organizar endpoints
```python
tags_metadata = [
    {"name": "Tasks", "description": "Task management for agents"},
    {"name": "Submissions", "description": "Evidence submissions from workers"},
    {"name": "Payments", "description": "x402 payment operations"},
    {"name": "Health", "description": "Health checks and monitoring"},
    {"name": "A2A", "description": "Agent-to-Agent protocol endpoints"},
]

app = FastAPI(..., openapi_tags=tags_metadata)
```

### 3. Ejemplos en endpoints
```python
from fastapi import APIRouter

router = APIRouter(tags=["Tasks"])

@router.post(
    "/tasks",
    response_model=Task,
    summary="Create a new task",
    description="Agents create tasks for human workers to complete",
    responses={
        200: {"description": "Task created successfully"},
        402: {"description": "Payment required"},
        422: {"description": "Validation error"},
    },
)
async def create_task(task: TaskCreate):
    ...
```

## Criterios de Éxito
- [x] `/docs` muestra Swagger UI
- [x] Metadata de API visible (título, descripción, contacto)
- [x] Endpoints organizados por tags (Health, Tasks, Workers, Submissions, Payments, A2A, WebSocket)
- [ ] Ejemplos de request/response en cada endpoint (parcial)
- [x] `/openapi.json` descargable

## COMPLETADO: 2026-01-25

### Cambios Realizados
- FastAPI app actualizada con metadatos completos
- 7 tags definidos para organización
- Descripción con Markdown, features, authentication, links
- Contact info: Ultravioleta DAO
- License: MIT
- Tags aplicados a todos los endpoints principales

## URL Final
```
https://execution.market/docs
```

# NOW-199: Tests para MCP Server Tools

**Prioridad**: P1
**Status**: TODO
**Archivo**: `mcp_server/tests/test_mcp_tools.py` (crear)

## Descripción

Tests para las herramientas MCP expuestas en `server.py`.

## Tools a Testear

1. `em_publish_task` - Crear tarea
2. `em_get_tasks` - Listar tareas disponibles
3. `em_get_task` - Obtener detalle de tarea
4. `em_approve_submission` - Aprobar trabajo
5. `em_reject_submission` - Rechazar trabajo
6. `em_apply_to_task` - Aplicar a tarea (worker)
7. `em_submit_work` - Enviar evidencia (worker)
8. `em_get_my_tasks` - Mis tareas (worker)
9. `em_assign_task` - Asignar worker (agent)

## Tests a Implementar

### publish_task Tests
- `test_publish_creates_task` - Crea task en DB
- `test_publish_requires_auth` - Requiere API key
- `test_publish_validates_bounty` - Bounty mínimo $0.50
- `test_publish_validates_location` - Coords válidas
- `test_publish_returns_task_id` - Retorna ID

### get_tasks Tests
- `test_get_tasks_returns_list` - Retorna array
- `test_get_tasks_filters_by_status` - Filtra por status
- `test_get_tasks_filters_by_location` - Filtra por ubicación
- `test_get_tasks_pagination` - Limit/offset funciona

### approve_submission Tests
- `test_approve_updates_status` - Status → completed
- `test_approve_triggers_payment` - Dispara release
- `test_approve_requires_ownership` - Solo owner del task

### apply_to_task Tests
- `test_apply_creates_application` - Crea application
- `test_apply_validates_executor` - Executor válido
- `test_apply_prevents_duplicate` - No duplicados

### submit_work Tests
- `test_submit_requires_assignment` - Solo si assigned
- `test_submit_validates_evidence` - Evidence schema
- `test_submit_stores_evidence` - Guarda en storage
- `test_submit_triggers_partial_release` - 30-50% payment

## Template

```python
"""
Tests for MCP Server tools.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import the actual tool functions
from ..server import (
    em_publish_task,
    em_get_tasks,
    em_approve_submission,
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch('server.get_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestPublishTask:
    """Tests for em_publish_task."""

    @pytest.mark.asyncio
    async def test_publish_creates_task(self, mock_supabase):
        """publish_task should create task in database."""
        mock_supabase.table().insert().execute.return_value.data = [{
            "id": "task-123",
            "status": "pending",
        }]

        result = await em_publish_task(
            title="Test Task",
            description="Test description",
            bounty_usdc=5.00,
            location={"lat": 19.43, "lng": -99.13},
            deadline_hours=24,
        )

        assert result["task_id"] == "task-123"
        mock_supabase.table.assert_called_with("tasks")
```

## Ejecución

```bash
pytest tests/test_mcp_tools.py -v
```

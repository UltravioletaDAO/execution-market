# NOW-076: Test Suite Fixes

## Status: REQUIRED
## Priority: P1

## Resultado Actual
- **331 tests passing (92%)**
- **29 tests failing (8%)**

## Fix 1: Missing Tuple import

**Archivo**: `mcp_server/verification/checks/timestamp.py`

```diff
- from typing import Optional
+ from typing import Optional, Tuple
```

## Fix 2: Import paths en tests

Los tests usan `from mcp_server.X` pero dentro del container el módulo está en `/app/`.

**Archivo**: `mcp_server/tests/test_workers.py`

```diff
- from mcp_server.workers.probation import (
+ from workers.probation import (

- from mcp_server.workers.recovery import (
+ from workers.recovery import (

- from mcp_server.workers.premiums import (
+ from workers.premiums import (

- from mcp_server.workers.categories import (
+ from workers.categories import (
```

## Fix 3: test_reputation.py - API mismatch

**Problema**: Tests usan `task_value_usd` pero el código usa diferente parámetro.

**Archivo**: `mcp_server/tests/test_reputation.py`

Verificar la firma de `Rating.__init__()` en `reputation/bayesian.py` y actualizar tests para usar los parámetros correctos.

## Fix 4: test_seals.py - Timezone aware vs naive

**Problema**: Comparación de datetimes con y sin timezone.

**Fix**: Usar `datetime.now(timezone.utc)` en vez de `datetime.now()`.

```python
# Cambiar en tests:
from datetime import timezone
expires_at = datetime.now(timezone.utc) + timedelta(days=365)
```

## Fix 5: test_safety.py - Invalid hour values

**Problema**: Tests usan horas fuera de rango (0-23).

**Fix**: Revisar los valores de hora en los tests y corregir a valores válidos.

## Ejecutar Tests

```bash
# En Docker (recomendado)
docker run --rm chamba-mcp-server:latest python -m pytest tests/ -v --tb=short

# Localmente (si dependencias están OK)
cd mcp_server
python -m pytest tests/ -v --tb=short
```

## Tests por Módulo

| Módulo | Status | Notes |
|--------|--------|-------|
| test_consensus.py | 100% PASS | Validator consensus |
| test_fees.py | 100% PASS | Fee calculation |
| test_webhooks.py | 100% PASS | Webhook delivery |
| test_websocket.py | 100% PASS | WebSocket server |
| test_workers.py | 100% PASS | Worker experience |
| test_protection_fund.py | 100% PASS | Worker protection |
| test_gps.py | 100% PASS | GPS validation |
| test_timestamp.py | 100% PASS | Timestamp checks |
| test_recon.py | 100% PASS | Recon task type |
| test_fraud_detection.py | 97% PASS | 1 assertion fix needed |
| test_gps_antispoofing.py | 95% PASS | 1 threshold fix needed |
| test_reputation.py | 36% PASS | API mismatch |
| test_seals.py | 40% PASS | Timezone issues |
| test_safety.py | 44% PASS | Hour value issues |

## Prioridad de Fixes

1. **P0**: Imports (ya hechos)
2. **P1**: Timezone issues (test_seals.py)
3. **P2**: API mismatch (test_reputation.py)
4. **P3**: Test data fixes (test_safety.py)

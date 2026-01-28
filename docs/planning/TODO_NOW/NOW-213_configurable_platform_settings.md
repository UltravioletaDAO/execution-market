# NOW-213: Configuración Dinámica de Platform Settings

## Metadata
- **Prioridad**: P0 (CRÍTICO)
- **Fase**: Core Infrastructure
- **Dependencias**: Ninguna
- **Archivos**: `mcp_server/config/`, Supabase tables
- **Razón**: Poder ajustar fees, límites, y parámetros sin redeploy

## Problema Actual

Múltiples valores están hardcodeados:

```python
# Actualmente dispersos en el código:
PLATFORM_FEE_PCT = 0.08  # 8% - hardcoded
PARTIAL_RELEASE_PCT = 0.30  # 30% on submission
MIN_BOUNTY_USD = 0.25
MAX_BOUNTY_USD = 10000.0
APPROVAL_TIMEOUT_HOURS = 48
MAX_RESUBMISSIONS = 3
```

## Objetivo

Crear un sistema de configuración centralizado que:
1. Se pueda modificar desde Admin Dashboard (NOW-214)
2. Se cachee en memoria para performance
3. Tenga defaults sensatos
4. Sea auditable (log de cambios)

## Schema de Configuración

### Tabla: `platform_config`

```sql
CREATE TABLE platform_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id)
);

-- Índice para búsqueda rápida
CREATE INDEX idx_platform_config_key ON platform_config(key);
CREATE INDEX idx_platform_config_category ON platform_config(category);
```

### Configuraciones Iniciales

```sql
INSERT INTO platform_config (key, value, description, category, is_public) VALUES
-- Fees
('fees.platform_fee_pct', '0.08', 'Platform fee as decimal (0.08 = 8%)', 'fees', false),
('fees.partial_release_pct', '0.30', 'Partial release on submission (0.30 = 30%)', 'fees', false),
('fees.min_fee_usd', '0.01', 'Minimum platform fee in USD', 'fees', false),

-- Bounty Limits
('bounty.min_usd', '0.25', 'Minimum bounty in USD', 'limits', true),
('bounty.max_usd', '10000.00', 'Maximum bounty in USD', 'limits', true),

-- Timeouts
('timeout.approval_hours', '48', 'Hours for agent to approve after submission', 'timing', false),
('timeout.task_default_hours', '24', 'Default task deadline if not specified', 'timing', false),
('timeout.auto_release_on_timeout', 'true', 'Auto-release to worker on approval timeout', 'timing', false),

-- Limits
('limits.max_resubmissions', '3', 'Max times worker can resubmit', 'limits', false),
('limits.max_active_tasks_per_agent', '100', 'Max concurrent tasks per agent', 'limits', false),
('limits.max_applications_per_task', '50', 'Max workers that can apply to a task', 'limits', false),

-- Feature Flags
('feature.disputes_enabled', 'true', 'Enable dispute system', 'features', false),
('feature.reputation_enabled', 'true', 'Enable reputation scoring', 'features', false),
('feature.auto_matching_enabled', 'false', 'Enable automatic worker matching', 'features', false),

-- Networks
('x402.supported_networks', '["base", "ethereum", "polygon", "optimism", "arbitrum"]', 'Supported payment networks', 'payments', true),
('x402.supported_tokens', '["USDC", "USDT", "DAI"]', 'Supported payment tokens', 'payments', true),
('x402.preferred_network', '"base"', 'Default network for payments', 'payments', true);
```

## API Endpoints

### GET /api/v1/config (público, solo is_public=true)
```json
{
  "bounty": {
    "min_usd": 0.25,
    "max_usd": 10000.00
  },
  "x402": {
    "supported_networks": ["base", "ethereum", "polygon", "optimism", "arbitrum"],
    "supported_tokens": ["USDC", "USDT", "DAI"],
    "preferred_network": "base"
  }
}
```

### GET /api/v1/admin/config (requiere admin auth)
```json
{
  "fees": {
    "platform_fee_pct": 0.08,
    "partial_release_pct": 0.30,
    "min_fee_usd": 0.01
  },
  "limits": { ... },
  "timing": { ... },
  "features": { ... }
}
```

### PUT /api/v1/admin/config/{key}
```json
{
  "value": 0.10,
  "reason": "Increasing fee to 10% for sustainability"
}
```

## Implementación Python

```python
# mcp_server/config/platform_config.py

from functools import lru_cache
from decimal import Decimal
import json

class PlatformConfig:
    """Centralized platform configuration with caching."""

    _cache: dict = {}
    _cache_ttl: int = 300  # 5 minutes

    @classmethod
    async def get(cls, key: str, default=None):
        """Get config value with caching."""
        if key in cls._cache:
            return cls._cache[key]

        result = await supabase.table("platform_config").select("value").eq("key", key).single()
        if result.data:
            value = json.loads(result.data["value"])
            cls._cache[key] = value
            return value
        return default

    @classmethod
    async def get_fee_pct(cls) -> Decimal:
        """Get current platform fee percentage."""
        return Decimal(str(await cls.get("fees.platform_fee_pct", 0.08)))

    @classmethod
    async def get_partial_release_pct(cls) -> Decimal:
        """Get partial release percentage on submission."""
        return Decimal(str(await cls.get("fees.partial_release_pct", 0.30)))

    @classmethod
    async def get_min_bounty(cls) -> Decimal:
        """Get minimum bounty in USD."""
        return Decimal(str(await cls.get("bounty.min_usd", 0.25)))

    @classmethod
    def invalidate_cache(cls, key: str = None):
        """Invalidate cache for key or all keys."""
        if key:
            cls._cache.pop(key, None)
        else:
            cls._cache.clear()
```

## Uso en Código

```python
# Antes (hardcoded):
platform_fee = bounty * Decimal("0.08")

# Después (configurable):
from config.platform_config import PlatformConfig

fee_pct = await PlatformConfig.get_fee_pct()
platform_fee = bounty * fee_pct
```

## Audit Log

```sql
CREATE TABLE config_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,
    changed_by UUID REFERENCES auth.users(id),
    reason TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Acceptance Criteria

- [x] Tabla platform_config creada con defaults (`007_platform_config.sql`)
- [x] Clase PlatformConfig con caching implementada (`config/platform_config.py`)
- [x] Hardcoded values migrados a usar PlatformConfig (`escrow.py`, `routes.py`)
- [x] API endpoints para leer/escribir config (`/api/v1/config`, `/api/v1/admin/config`)
- [x] Audit log de cambios (`config_audit_log` table + trigger)
- [x] Tests para config system (`tests/test_platform_config.py`)
- [x] Documentación de todas las settings (in migration comments)

## Implementación (2026-01-27)

### Files Created
- `supabase/migrations/007_platform_config.sql` - DB schema + defaults
- `mcp_server/config/__init__.py` - Module init
- `mcp_server/config/platform_config.py` - Config class with caching
- `mcp_server/api/admin.py` - Admin API routes
- `mcp_server/tests/test_platform_config.py` - Tests

### Files Updated
- `mcp_server/integrations/x402/escrow.py` - Use config helpers
- `mcp_server/api/routes.py` - Use async config, add /config endpoint
- `mcp_server/main.py` - Register admin router

## Lugares a Actualizar (Parcialmente Completado)

1. [x] `escrow.py` - platform fee calculation (now uses helper functions)
2. [x] `routes.py` - min/max bounty validation from config
3. [ ] `task_validator.py` - (TODO: verify uses config)
4. [ ] `submit_work.py` - resubmission limits (TODO: verify uses config)
5. [ ] `timeout_handler.py` - timeout hours (TODO: verify uses config)

Note: Main entry points updated. Additional files can be migrated incrementally.

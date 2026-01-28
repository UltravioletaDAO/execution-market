# NOW-210: Verificar Esquemas de Base de Datos Supabase

## Metadata
- **Prioridad**: P1
- **Fase**: Documentation
- **Dependencias**: Ninguna
- **Archivos**: `supabase/migrations/`
- **Tiempo estimado**: 30 minutos

## Descripción
Documentar los esquemas de base de datos que se crearán cuando se ejecuten las migraciones.

## Archivos de Migración

```
supabase/migrations/
├── 001_initial_schema.sql      # Tablas base
├── 002_escrow_and_payments.sql # Escrow y pagos x402
├── 003_reputation_system.sql   # Sistema de reputación Bayesiano
├── 004_disputes.sql            # Sistema de disputas
└── 005_rpc_functions.sql       # Funciones RPC
```

## Esquema Principal (001_initial_schema.sql)

### Tabla: executors
```sql
CREATE TABLE executors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    wallet_address VARCHAR(42) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    reputation_score DECIMAL(5,2) DEFAULT 50.00,
    tasks_completed INTEGER DEFAULT 0,
    tasks_disputed INTEGER DEFAULT 0,
    total_earned_usdc DECIMAL(12,2) DEFAULT 0,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: tasks
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    instructions TEXT,
    bounty_usdc DECIMAL(10,2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    -- Ubicación
    location_lat DECIMAL(10,7),
    location_lng DECIMAL(10,7),
    location_radius_meters INTEGER,
    location_hint VARCHAR(200),
    -- Asignación
    assigned_to UUID REFERENCES executors(id),
    -- Evidencia requerida
    evidence_types JSONB DEFAULT '[]',
    -- Tiempos
    deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Estados posibles: draft, published, assigned, in_progress, submitted, completed, cancelled, disputed
```

### Tabla: applications
```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    executor_id UUID REFERENCES executors(id),
    message TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Estados: pending, accepted, rejected, withdrawn
```

### Tabla: submissions
```sql
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    executor_id UUID REFERENCES executors(id),
    evidence_urls JSONB NOT NULL DEFAULT '[]',
    notes TEXT,
    gps_latitude DECIMAL(10,7),
    gps_longitude DECIMAL(10,7),
    gps_accuracy_meters DECIMAL(10,2),
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending',
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ
);

-- Estados: pending, approved, rejected, revision_requested
```

## Esquema de Pagos (002_escrow_and_payments.sql)

### Tabla: escrows
```sql
CREATE TABLE escrows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    agent_address VARCHAR(42) NOT NULL,
    worker_address VARCHAR(42),
    amount_usdc DECIMAL(10,2) NOT NULL,
    platform_fee_usdc DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    -- Transacciones
    deposit_tx_hash VARCHAR(66),
    release_tx_hash VARCHAR(66),
    refund_tx_hash VARCHAR(66),
    network VARCHAR(20) DEFAULT 'ethereum',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Estados: pending, funded, partial_released, released, refunded, disputed
```

### Tabla: payments
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escrow_id UUID REFERENCES escrows(id),
    from_address VARCHAR(42) NOT NULL,
    to_address VARCHAR(42) NOT NULL,
    amount_usdc DECIMAL(10,2) NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    tx_hash VARCHAR(66),
    network VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tipos: escrow_deposit, worker_payment, platform_fee, refund
```

## Esquema de Reputación (003_reputation_system.sql)

### Tabla: reputation_log
```sql
CREATE TABLE reputation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    executor_id UUID REFERENCES executors(id),
    task_id UUID REFERENCES tasks(id),
    old_score DECIMAL(5,2),
    new_score DECIMAL(5,2),
    change_reason VARCHAR(50),
    alpha_change DECIMAL(5,2),
    beta_change DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: badges
```sql
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    executor_id UUID REFERENCES executors(id),
    badge_type VARCHAR(50) NOT NULL,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(executor_id, badge_type)
);
```

## Esquema de Disputas (004_disputes.sql)

### Tabla: disputes
```sql
CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    submission_id UUID REFERENCES submissions(id),
    escrow_id UUID REFERENCES escrows(id),
    initiator_type VARCHAR(10) NOT NULL, -- 'worker' or 'agent'
    initiator_id VARCHAR(100) NOT NULL,
    reason VARCHAR(50) NOT NULL,
    description TEXT,
    evidence_urls JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'open',
    resolution VARCHAR(20),
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Estados: open, under_review, resolved, escalated, withdrawn
-- Resoluciones: full_worker, full_agent, split, dismissed
```

## Funciones RPC (005_rpc_functions.sql)

```sql
-- Buscar tareas disponibles
CREATE FUNCTION get_available_tasks(
    p_category VARCHAR DEFAULT NULL,
    p_lat DECIMAL DEFAULT NULL,
    p_lng DECIMAL DEFAULT NULL,
    p_radius_km DECIMAL DEFAULT 10
)

-- Calcular reputación con decaimiento
CREATE FUNCTION calculate_decayed_reputation(
    p_executor_id UUID
)

-- Asignar tarea atómicamente
CREATE FUNCTION assign_task_atomic(
    p_task_id UUID,
    p_executor_id UUID
)
```

## Criterios de Éxito
- [x] Documentación completa de todas las tablas
- [x] Relaciones entre tablas claras
- [x] Estados posibles documentados
- [x] Migraciones listas para ejecutar

## COMPLETADO: 2026-01-25

### Migraciones Verificadas
Todas las migraciones en `supabase/migrations/` están completas y documentadas:

| Archivo | Líneas | Contenido |
|---------|--------|-----------|
| 001_initial_schema.sql | 697 | ENUMs, tablas core, RLS, storage bucket |
| 002_escrow_and_payments.sql | ~150 | Escrows, payments, transacciones |
| 003_reputation_system.sql | ~100 | reputation_log, badges, decay |
| 004_disputes.sql | ~80 | disputes, resoluciones |
| 005_rpc_functions.sql | ~120 | get_available_tasks, assign_task_atomic |

### Seed Data
`supabase/seed.sql` (368 líneas) incluye:
- 5 executors de prueba con diferentes scores
- 12 tareas bilingües (ES/EN) de diferentes categorías
- 1 submission de ejemplo

### Schema Diagram
```
executors ←──┐
    ↑        │
    │        │
tasks ───────┤
    ↓        │
applications │
    ↓        │
submissions ─┤
    ↓        │
escrows ─────┤
    ↓        │
payments ────┘
    ↓
disputes
    ↓
reputation_log
```

### Próximo Paso
Ejecutar migraciones una vez que se cree el proyecto Supabase (ver NOW-203).

## Verificación Post-Migración
```sql
-- Verificar que todas las tablas existen
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';

-- Debe mostrar:
-- executors, tasks, applications, submissions,
-- escrows, payments, reputation_log, badges, disputes
```

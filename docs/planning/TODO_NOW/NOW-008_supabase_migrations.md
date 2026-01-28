# NOW-008: Aplicar migrations a Supabase production

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: Ninguna
- **Archivos existentes**: `supabase/migrations/001-004.sql`
- **Tiempo estimado**: 30 min

## Descripción
Aplicar las 4 migrations existentes a la base de datos Supabase de producción.

## Contexto Técnico
- **Database**: PostgreSQL 15 (Supabase)
- **Extensions**: PostGIS, pgcrypto
- **Migrations**: 4 archivos SQL listos

## Migrations Existentes

### 001 - Core Schema
```sql
-- Tablas principales
CREATE TABLE executors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address TEXT UNIQUE,
  email TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  task_type TEXT NOT NULL,
  bounty_usdc DECIMAL(18, 6) NOT NULL,
  location GEOGRAPHY(POINT, 4326),
  radius_meters INTEGER DEFAULT 500,
  evidence_required JSONB,
  status TEXT DEFAULT 'open',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

CREATE TABLE submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES tasks(id),
  executor_id UUID REFERENCES executors(id),
  evidence JSONB NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ
);
```

### 002 - Payments
```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID REFERENCES submissions(id),
  amount_usdc DECIMAL(18, 6) NOT NULL,
  tx_hash TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE escrow (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES tasks(id),
  amount_usdc DECIMAL(18, 6) NOT NULL,
  deposit_tx_hash TEXT,
  release_tx_hash TEXT,
  status TEXT DEFAULT 'locked',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 003 - Reputation
```sql
CREATE TABLE ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rater_id TEXT NOT NULL,
  ratee_id UUID REFERENCES executors(id),
  task_id UUID REFERENCES tasks(id),
  score INTEGER CHECK (score >= 1 AND score <= 100),
  task_value_usdc DECIMAL(18, 6),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ratings_ratee ON ratings(ratee_id);
CREATE INDEX idx_ratings_created ON ratings(created_at DESC);
```

### 004 - RLS Policies
```sql
-- Enable RLS
ALTER TABLE executors ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

-- Public read for tasks
CREATE POLICY "Tasks are viewable by everyone"
  ON tasks FOR SELECT
  USING (true);

-- Only authenticated can create submissions
CREATE POLICY "Authenticated users can create submissions"
  ON submissions FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');
```

## Comandos de Aplicación

```bash
# Opción 1: Usando Supabase CLI
supabase db push

# Opción 2: Manual via psql
psql $DATABASE_URL -f supabase/migrations/001_core_schema.sql
psql $DATABASE_URL -f supabase/migrations/002_payments.sql
psql $DATABASE_URL -f supabase/migrations/003_reputation.sql
psql $DATABASE_URL -f supabase/migrations/004_rls_policies.sql

# Opción 3: Via Supabase Dashboard
# SQL Editor → Paste each migration → Run
```

## Criterios de Éxito
- [ ] Todas las tablas creadas (executors, tasks, submissions, payments, escrow, ratings)
- [ ] Índices creados
- [ ] PostGIS extension habilitado
- [ ] RLS policies activas
- [ ] No errores en migrations

## Comandos de Verificación
```bash
# Verificar tablas
psql $DATABASE_URL -c "\dt"

# Verificar columnas
psql $DATABASE_URL -c "\d tasks"

# Verificar RLS
psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# Verificar PostGIS
psql $DATABASE_URL -c "SELECT PostGIS_Version();"

# Test insert
psql $DATABASE_URL -c "INSERT INTO tasks (agent_id, title, task_type, bounty_usdc) VALUES ('test-agent', 'Test Task', 'verification', 5.00) RETURNING id;"
```

## Rollback (si es necesario)
```sql
-- CUIDADO: Esto borra todo
DROP TABLE IF EXISTS ratings CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS escrow CASCADE;
DROP TABLE IF EXISTS submissions CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS executors CASCADE;
```

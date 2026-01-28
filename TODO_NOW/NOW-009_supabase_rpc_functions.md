# NOW-009: Crear RPC functions en Supabase

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-008
- **Archivos a crear**: `supabase/migrations/005_rpc_functions.sql`
- **Tiempo estimado**: 1 hora

## Descripción
Crear funciones RPC en PostgreSQL para operaciones complejas que no se pueden hacer con queries simples.

## Contexto Técnico
- **Funciones necesarias**:
  - `get_or_create_executor` - Crear executor si no existe
  - `link_wallet_to_session` - Vincular wallet a sesión auth
  - `calculate_bayesian_score` - Calcular reputación
  - `get_tasks_near_location` - Buscar tareas cercanas

## Código de Referencia

### 005_rpc_functions.sql
```sql
-- ===========================================
-- get_or_create_executor
-- ===========================================
CREATE OR REPLACE FUNCTION get_or_create_executor(
  p_wallet_address TEXT DEFAULT NULL,
  p_email TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_executor_id UUID;
BEGIN
  -- Try to find existing executor
  IF p_wallet_address IS NOT NULL THEN
    SELECT id INTO v_executor_id
    FROM executors
    WHERE wallet_address = p_wallet_address;
  ELSIF p_email IS NOT NULL THEN
    SELECT id INTO v_executor_id
    FROM executors
    WHERE email = p_email;
  END IF;

  -- Create if not exists
  IF v_executor_id IS NULL THEN
    INSERT INTO executors (wallet_address, email)
    VALUES (p_wallet_address, p_email)
    RETURNING id INTO v_executor_id;
  END IF;

  RETURN v_executor_id;
END;
$$;

-- ===========================================
-- link_wallet_to_session
-- ===========================================
CREATE OR REPLACE FUNCTION link_wallet_to_session(
  p_executor_id UUID,
  p_wallet_address TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE executors
  SET
    wallet_address = p_wallet_address,
    updated_at = NOW()
  WHERE id = p_executor_id
    AND (wallet_address IS NULL OR wallet_address = p_wallet_address);

  RETURN FOUND;
END;
$$;

-- ===========================================
-- calculate_bayesian_score
-- C = confidence parameter (15-20)
-- m = prior mean (50)
-- ===========================================
CREATE OR REPLACE FUNCTION calculate_bayesian_score(
  p_executor_id UUID,
  p_c DECIMAL DEFAULT 15,
  p_m DECIMAL DEFAULT 50,
  p_decay_rate DECIMAL DEFAULT 0.9
)
RETURNS DECIMAL
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_weighted_sum DECIMAL := 0;
  v_weight_total DECIMAL := 0;
  v_score DECIMAL;
  r RECORD;
BEGIN
  -- Calculate weighted sum with time decay
  FOR r IN
    SELECT
      score,
      task_value_usdc,
      created_at,
      EXTRACT(EPOCH FROM (NOW() - created_at)) / (30 * 24 * 3600) AS months_old
    FROM ratings
    WHERE ratee_id = p_executor_id
  LOOP
    DECLARE
      weight DECIMAL;
      decay DECIMAL;
    BEGIN
      -- Weight = log(task_value + 1)
      weight := LN(COALESCE(r.task_value_usdc, 1) + 1);

      -- Decay = 0.9^months_old
      decay := POWER(p_decay_rate, r.months_old);

      -- Apply weight and decay
      v_weighted_sum := v_weighted_sum + (r.score * weight * decay);
      v_weight_total := v_weight_total + (weight * decay);
    END;
  END LOOP;

  -- Bayesian average formula
  -- Score = (C * m + sum(ratings * weight)) / (C + sum(weights))
  IF v_weight_total > 0 THEN
    v_score := (p_c * p_m + v_weighted_sum) / (p_c + v_weight_total);
  ELSE
    v_score := p_m; -- Return prior mean if no ratings
  END IF;

  RETURN ROUND(v_score, 2);
END;
$$;

-- ===========================================
-- get_tasks_near_location
-- Uses PostGIS for geographic queries
-- ===========================================
CREATE OR REPLACE FUNCTION get_tasks_near_location(
  p_lat DOUBLE PRECISION,
  p_lng DOUBLE PRECISION,
  p_radius_meters INTEGER DEFAULT 5000,
  p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  description TEXT,
  task_type TEXT,
  bounty_usdc DECIMAL,
  distance_meters DOUBLE PRECISION,
  status TEXT,
  expires_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.id,
    t.title,
    t.description,
    t.task_type,
    t.bounty_usdc,
    ST_Distance(
      t.location::geography,
      ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography
    ) AS distance_meters,
    t.status,
    t.expires_at
  FROM tasks t
  WHERE t.status = 'open'
    AND (t.expires_at IS NULL OR t.expires_at > NOW())
    AND ST_DWithin(
      t.location::geography,
      ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
      p_radius_meters
    )
  ORDER BY distance_meters ASC
  LIMIT p_limit;
END;
$$;

-- ===========================================
-- Grants for anon and authenticated roles
-- ===========================================
GRANT EXECUTE ON FUNCTION get_or_create_executor TO authenticated;
GRANT EXECUTE ON FUNCTION link_wallet_to_session TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_bayesian_score TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_tasks_near_location TO anon, authenticated;
```

## Criterios de Éxito
- [ ] Todas las funciones creadas sin errores
- [ ] `get_or_create_executor` crea y retorna executor
- [ ] `link_wallet_to_session` actualiza wallet
- [ ] `calculate_bayesian_score` retorna score correcto
- [ ] `get_tasks_near_location` retorna tareas cercanas
- [ ] Permisos correctos para anon/authenticated

## Comandos de Verificación
```bash
# Aplicar migration
psql $DATABASE_URL -f supabase/migrations/005_rpc_functions.sql

# Test get_or_create_executor
psql $DATABASE_URL -c "SELECT get_or_create_executor('0x1234...', NULL);"

# Test calculate_bayesian_score (después de tener ratings)
psql $DATABASE_URL -c "SELECT calculate_bayesian_score('uuid-here');"

# Test get_tasks_near_location (Miami)
psql $DATABASE_URL -c "SELECT * FROM get_tasks_near_location(25.7617, -80.1918, 10000);"

# List functions
psql $DATABASE_URL -c "\df public.*"
```

## Uso desde Supabase Client
```typescript
// JavaScript/TypeScript
const { data, error } = await supabase
  .rpc('get_or_create_executor', {
    p_wallet_address: '0x1234...'
  });

const { data: tasks } = await supabase
  .rpc('get_tasks_near_location', {
    p_lat: 25.7617,
    p_lng: -80.1918,
    p_radius_meters: 5000
  });
```

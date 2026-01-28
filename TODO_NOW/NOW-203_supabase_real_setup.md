# NOW-203: Configurar Supabase Real (no mock)

## Metadata
- **Prioridad**: P0 (CRÍTICO)
- **Fase**: Production Integration
- **Dependencias**: Ninguna
- **Archivos a modificar**: `.env`, `mcp_server/supabase_client.py`
- **Tiempo estimado**: 1-2 horas

## Descripción
Configurar proyecto Supabase real y ejecutar las migraciones SQL que ya existen.

## Contexto Técnico
- **Migraciones**: `supabase/migrations/` (5 archivos SQL ya creados)
- **Dashboard Supabase**: https://supabase.com/dashboard

## Pasos

### 1. Crear proyecto en Supabase (si no existe)
```
1. Ir a https://supabase.com/dashboard
2. New Project → "chamba-production"
3. Región: us-east-1 (o más cercana)
4. Copiar:
   - Project URL
   - anon/public key
   - service_role key
```

### 2. Ejecutar migraciones
```bash
# Opción A: Via Supabase CLI
cd ideas/chamba
supabase link --project-ref <project-id>
supabase db push

# Opción B: Via SQL Editor en dashboard
# Copiar contenido de cada archivo en orden:
# 1. 001_initial_schema.sql
# 2. 002_escrow_and_payments.sql
# 3. 003_reputation_system.sql
# 4. 004_disputes.sql
# 5. 005_rpc_functions.sql
```

### 3. Configurar Storage Bucket
```sql
-- En SQL Editor de Supabase
INSERT INTO storage.buckets (id, name, public)
VALUES ('evidence', 'evidence', true);

-- Política para subir evidencia
CREATE POLICY "Anyone can upload evidence"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'evidence');

-- Política para ver evidencia
CREATE POLICY "Anyone can view evidence"
ON storage.objects FOR SELECT
USING (bucket_id = 'evidence');
```

### 4. Actualizar .env
```bash
# .env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_KEY=eyJhbG...  # Solo para backend
```

### 5. Verificar conexión
```python
# test_supabase_connection.py
from supabase import create_client
import os

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_ANON_KEY"]
client = create_client(url, key)

# Test query
result = client.table("tasks").select("*").limit(1).execute()
print(f"Connection OK: {result}")
```

## Tablas Esperadas
Después de ejecutar migraciones:
- `executors` - Workers y agents
- `tasks` - Tareas publicadas
- `applications` - Aplicaciones a tareas
- `submissions` - Envíos de evidencia
- `escrows` - Estado de escrow
- `payments` - Historial de pagos
- `disputes` - Disputas
- `reputation_log` - Historial de reputación

## Criterios de Éxito
- [ ] Proyecto Supabase creado (ACCIÓN REQUERIDA: Usuario debe crear en dashboard)
- [x] Migraciones SQL completas y listas para ejecutar
- [x] Storage bucket configurado en migrations
- [ ] .env configurado con credenciales reales (ACCIÓN REQUERIDA)
- [ ] Test de conexión exitoso
- [ ] Dashboard muestra tablas listas para datos

## ESTADO: 2026-01-25

### Migraciones Verificadas
Las migraciones en `supabase/migrations/` están completas:
```
001_initial_schema.sql    - 697 líneas, incluye:
  - 7 ENUMs (task_category, task_status, evidence_type, etc.)
  - 5 tablas core (executors, tasks, task_applications, submissions, user_wallets)
  - RLS policies para todas las tablas
  - Storage bucket "chamba-evidence" con políticas
  - Triggers para updated_at, stats, tier updates

002_escrow_and_payments.sql
003_reputation_system.sql
004_disputes.sql
005_rpc_functions.sql
```

### Seed Data Disponible
`supabase/seed.sql` incluye datos de prueba bilingües (ES/EN):
- 5 executors de prueba
- 12 tareas de diferentes categorías
- 1 submission de ejemplo

### BLOQUEADO: Requiere Acción del Usuario
```
1. Crear proyecto en Supabase Dashboard
2. Copiar credenciales a .env
3. Ejecutar: supabase db push
```

## Datos de Prueba (Opcional)
```sql
-- Insertar executor de prueba
INSERT INTO executors (id, user_id, wallet_address, reputation_score)
VALUES (
  'exec_test_001',
  'user_test_001',
  '0x1234567890123456789012345678901234567890',
  50.0
);

-- Insertar tarea de prueba
INSERT INTO tasks (id, agent_id, title, description, bounty_usdc, status, category)
VALUES (
  'task_test_001',
  'agent_test_001',
  'Test Task',
  'This is a test task',
  5.00,
  'published',
  'physical_presence'
);
```

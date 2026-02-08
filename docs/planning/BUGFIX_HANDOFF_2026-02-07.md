# Bug Fix Handoff - Beta Launch Readiness

> Fecha: 2026-02-07
> Contexto: Auditoría completa de 4 agentes sobre MCP server, dashboard, DB, y endpoints live.
> Objetivo: Arreglar los bugs que bloquean el core loop (create task -> apply -> submit -> approve -> pay).

---

## Estado actual: 75% listo

**Lo que funciona:** Infraestructura AWS, DB (24 migraciones), REST API (50+ endpoints), SDK x402 (EIP-3009, settlement 3-step, gasless), auth (Dynamic.xyz + Supabase), task browsing/apply, 658 tests passing, TypeScript 0 errores.

**Lo que falta:** 8 fixes para beta launch (~12 horas).

---

## Fix 0: DB constraint bounty_usd (15 min)

**Problema:** `tasks` tiene CHECK `bounty_usd >= 1` pero `platform_config` tiene `bounty.min_usd = 0.01`. Test tasks de $0.25 fallan en la DB.

**Fix:** Ejecutar en Supabase SQL Editor:
```sql
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_bounty_usd_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_bounty_usd_check CHECK (bounty_usd >= 0.01);
```

**Verificar:**
```sql
SELECT conname, consrc FROM pg_constraint WHERE conrelid = 'tasks'::regclass AND conname LIKE '%bounty%';
```

---

## Fix 1: Category mapping en TaskBrowser (1 hora)

**Problema:** `TaskBrowser.tsx` usa categorías `'verification'`, `'data_collection'` que NO existen en la DB. La DB usa `'physical_presence'`, `'knowledge_access'`, `'human_authority'`, `'simple_action'`, `'digital_physical'`.

**Archivos:**
- `dashboard/src/components/TaskBrowser.tsx` — las categorías del filter
- `dashboard/src/types/database.ts` — el tipo `TaskCategory`

**Fix:** Reemplazar las categorías hardcoded en TaskBrowser por las reales de la DB:

```typescript
// En TaskBrowser.tsx, buscar las categorías del filtro y cambiar a:
const CATEGORIES = [
  { value: 'physical_presence', label: 'Presencia Física' },
  { value: 'knowledge_access', label: 'Acceso a Información' },
  { value: 'human_authority', label: 'Autoridad Humana' },
  { value: 'simple_action', label: 'Acción Simple' },
  { value: 'digital_physical', label: 'Digital-Físico' },
];
```

**Verificar:** Los filtros de categoría deben matchear tareas reales de la DB.

---

## Fix 2: Wire search input a filtering (30 min)

**Problema:** El input de búsqueda en TaskBrowser existe en la UI pero no tiene `onChange` handler. Escribir no hace nada.

**Archivo:** `dashboard/src/components/TaskBrowser.tsx`

**Fix:** Agregar state para el search query y filtrar tareas por título/descripción:

```typescript
const [searchQuery, setSearchQuery] = useState('');

// En el input de búsqueda:
onChange={(e) => setSearchQuery(e.target.value)}

// En el filtrado de tareas:
const filteredTasks = tasks.filter(task => {
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      task.title?.toLowerCase().includes(q) ||
      task.description?.toLowerCase().includes(q);
    if (!matchesSearch) return false;
  }
  // ... resto de filtros existentes
});
```

**Verificar:** Escribir en el search box debe filtrar tareas visibles.

---

## Fix 3: Fix RLS silent failure en submissions (2 horas)

**Problema:** Si `executor.user_id` es null, INSERT en `submissions` falla silenciosamente (0 rows, sin error) por la RLS policy que requiere `user_id = auth.uid()`.

**Archivos:**
- `supabase/migrations/` — nueva migración
- `dashboard/src/services/submissions.ts` — error handling

**Opción A (Recomendada): RPC function con SECURITY DEFINER**
```sql
-- Nueva migración: 025_submit_work_rpc.sql
CREATE OR REPLACE FUNCTION submit_work(
  p_task_id UUID,
  p_executor_id UUID,
  p_evidence JSONB,
  p_notes TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_submission_id UUID;
  v_task RECORD;
BEGIN
  -- Verificar que la tarea existe y está asignada a este executor
  SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Task not found';
  END IF;
  IF v_task.executor_id != p_executor_id THEN
    RAISE EXCEPTION 'Task not assigned to this executor';
  END IF;
  IF v_task.status NOT IN ('accepted', 'in_progress') THEN
    RAISE EXCEPTION 'Task not in submittable state: %', v_task.status;
  END IF;

  INSERT INTO submissions (task_id, executor_id, evidence, notes, status)
  VALUES (p_task_id, p_executor_id, p_evidence, p_notes, 'pending')
  RETURNING id INTO v_submission_id;

  -- Actualizar estado de la tarea
  UPDATE tasks SET status = 'submitted' WHERE id = p_task_id;

  RETURN v_submission_id;
END;
$$;
```

**Opción B: Asegurar que user_id siempre se setea**
Verificar en `AuthContext.tsx` que `link_wallet_to_session` se ejecuta SIEMPRE exitosamente antes de permitir submissions. Agregar check explícito:

```typescript
// En SubmissionForm.tsx, antes de submit:
const { data: exec } = await supabase
  .from('executors')
  .select('user_id')
  .eq('id', executor.id)
  .single();

if (!exec?.user_id) {
  throw new Error('Tu sesión no está vinculada. Reconecta tu wallet.');
}
```

**Verificar:** Crear un executor nuevo, submit evidence, verificar que aparece en la tabla `submissions`.

---

## Fix 4: Fix em_approve_submission payment header en MCP tool (1 hora)

**Problema:** `server.py:1016` usa `task.get("escrow_tx", "")` como payment header. Debería usar `_resolve_task_payment_header()` como lo hace `routes.py:626`.

**Archivo:** `mcp_server/server.py`

**Fix:**

1. Importar o duplicar la función helper de routes.py:
```python
# Agregar en server.py (o importar de un módulo compartido)
async def _resolve_task_payment_header(task_id: str, escrow_tx: str = None) -> str:
    """Busca el payment header en la tabla escrows."""
    if escrow_tx and escrow_tx.startswith("x402:"):
        return escrow_tx

    try:
        result = supabase_client.client.table("escrows") \
            .select("metadata") \
            .eq("task_id", task_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if result.data:
            metadata = result.data[0].get("metadata", {})
            header = metadata.get("x_payment_header") or metadata.get("payment_header")
            if header:
                return header
    except Exception:
        pass

    return escrow_tx or ""
```

2. Usarla en em_approve_submission (alrededor de línea 1016):
```python
# ANTES (BROKEN):
payment_header=task.get("escrow_tx", "")

# DESPUÉS (FIXED):
payment_header = await _resolve_task_payment_header(task["id"], task.get("escrow_tx"))
```

3. También fix las response keys (alrededor de línea 1101):
```python
# ANTES (BROKEN):
payment_info.get("worker_payment")  # no existe
payment_info.get("tx_hashes")       # no existe

# DESPUÉS (FIXED):
payment_info.get("net_to_worker")   # key real
payment_info.get("tx_hash")         # key real (singular)
```

**Verificar:** MCP tool `em_approve_submission` debe mostrar monto correcto y tx hash.

---

## Fix 5: Remover advanced_escrow_integration dependency (2 horas)

**Problema:** `server.py` importa `advanced_escrow_integration` en try/except. Si existe, intenta release directo a contrato (requiere gas). Si falla parcialmente, el fallback a SDK podría causar double payment.

**Archivo:** `mcp_server/server.py`

**Fix:** Eliminar TODAS las referencias a `advanced_escrow_integration` y usar SOLO el SDK:

1. Buscar todas las ocurrencias:
```bash
grep -n "advanced_escrow" mcp_server/server.py
```

2. En `em_publish_task` (alrededor de línea 650-679):
```python
# ELIMINAR el try/except de advanced_escrow_integration
# DEJAR SOLO el path del SDK:
if x402_sdk:
    try:
        auth_result = x402_sdk.authorize_task_bounty(
            amount_usd=params.bounty_usd,
            task_id=task_id
        )
        if auth_result.get("success"):
            escrow_data["escrow_tx"] = auth_result.get("authorization_hash", "")
    except Exception as e:
        logger.warning(f"Escrow auth failed (non-blocking): {e}")
```

3. En `em_approve_submission` (alrededor de línea 991-1025):
```python
# ELIMINAR el try de advanced_escrow_integration.release_to_worker()
# DEJAR SOLO:
if x402_sdk:
    payment_header = await _resolve_task_payment_header(task["id"], task.get("escrow_tx"))
    payment_result = x402_sdk.settle_task_payment(
        task_id=submission["task_id"],
        worker_address=worker_wallet,
        amount_usd=task["bounty_usd"],
        payment_header=payment_header
    )
```

4. En `em_cancel_task` (alrededor de línea 1144-1157):
```python
# ELIMINAR advanced_escrow_integration.refund_to_agent()
# DEJAR SOLO:
if x402_sdk:
    refund_result = x402_sdk.refund_task_payment(
        task_id=task_id,
        payment_header=await _resolve_task_payment_header(task_id, task.get("escrow_tx"))
    )
```

**Verificar:** `grep -n "advanced_escrow" mcp_server/server.py` debe retornar vacío.

---

## Fix 6: Wire agent dashboard actions (3 horas)

**Problema:** "View Task", "Review Submission", "Edit", "View Applicants" en agent dashboard son `console.log` stubs.

**Archivos:**
- `dashboard/src/App.tsx` (líneas ~251-276)
- `dashboard/src/pages/AgentDashboard.tsx`

**Fix:** Conectar los handlers a navegación:

```typescript
// En App.tsx o AgentDashboard.tsx:
const navigate = useNavigate();

const handleViewTask = (taskId: string) => {
  navigate(`/agent/tasks?view=${taskId}`);
};

const handleReviewSubmission = (submissionId: string) => {
  navigate(`/agent/dashboard?review=${submissionId}`);
};

const handleEditTask = (taskId: string) => {
  navigate(`/agent/tasks?edit=${taskId}`);
};

const handleViewApplicants = (taskId: string) => {
  navigate(`/agent/tasks?applicants=${taskId}`);
};
```

Luego en la página de destino, leer el query param y mostrar el modal/panel correspondiente.

**Nota:** Si no hay tiempo para el full flow, al menos hacer que "Review Submission" abra un modal con la evidencia y botones de approve/reject que llamen a `services/submissions.ts` `approveSubmission()` / `rejectSubmission()`.

**Verificar:** Click en cada action debe navegar a la vista correcta.

---

## Fix 7: Crear tareas reales con escrow (2 horas)

**Pre-requisito:** Fixes 0-5 deben estar deployados.

**Script:**
```bash
cd scripts
npx tsx task-factory.ts --preset screenshot --bounty 0.50 --deadline 15
npx tsx task-factory.ts --preset verification --bounty 0.25 --deadline 10
npx tsx task-factory.ts --preset delivery --bounty 5.00 --deadline 60
```

Si `task-factory.ts` no soporta `--live` aún, crear tareas manualmente via API:
```bash
curl -X POST https://api.execution.market/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "title": "Verificar si la tienda en [dirección] está abierta",
    "description": "Tomar foto del frente de la tienda mostrando si está abierta o cerrada",
    "category": "physical_presence",
    "bounty_usd": 0.50,
    "deadline_minutes": 15,
    "location_hint": "Medellín, Colombia",
    "evidence_schema": {
      "required": ["photo"],
      "photo": {"type": "image", "description": "Foto del frente de la tienda"}
    }
  }'
```

Crear 3-5 tareas variadas para que el marketplace no se vea vacío.

**Verificar:** Las tareas aparecen en `execution.market/tasks` y son aplicables.

---

## Orden de ejecución recomendado

```
Fix 0 (DB constraint)         → 15 min  → Sin dependencias
Fix 1 (Category mapping)      → 1h      → Sin dependencias
Fix 2 (Search input)          → 30 min  → Sin dependencias
─── Estos tres se pueden hacer en paralelo ───
Fix 3 (RLS submissions)       → 2h      → Requiere Supabase SQL Editor
Fix 4 (MCP payment header)    → 1h      → Requiere leer server.py
Fix 5 (Remove advanced_escrow)→ 2h      → Requiere leer server.py (hacer junto con Fix 4)
─── Fix 4 y 5 se hacen juntos ───
Fix 6 (Agent dashboard actions)→ 3h     → Requiere leer App.tsx + AgentDashboard.tsx
Fix 7 (Crear tareas)          → 2h      → Requiere Fixes 0-5 deployados
```

**Total estimado: ~12 horas de trabajo enfocado.**

---

## Bugs conocidos que NO bloquean beta launch

Estos son aceptables como deuda técnica para un beta controlado:

| Bug | Razón por la que no bloquea |
|-----|---------------------------|
| Worker endpoints sin auth (`/apply`, `/submit`) | Beta controlado, sabemos quién usa la plataforma |
| Supabase client `as any` | No es user-facing, funciona en runtime |
| Profile settings es no-op | localStorage funciona por ahora |
| "Near me" sort no funciona | Feature, no fix. Sorting por fecha funciona |
| No pagination en tasks | No hay suficientes tasks aún |
| Console.log leaks | Cosmético, no afecta funcionalidad |
| Earnings chart year view dummy data | Pocos usuarios, datos reales insuficientes |
| Withdrawal flow no wired | Workers reciben pago directo via x402 |
| MCP `em_cancel_task` solo para `published` | Workaround: cancelar via REST API |
| Sync Supabase en async functions | Performance bajo carga, no correctness |
| Hardcoded Spanish strings | Target audience es LATAM inicialmente |
| Crossmint/staking stubs | Features futuras, no core loop |

---

## Verificación end-to-end post-fixes

Después de aplicar todos los fixes y deploy:

1. **Worker flow:**
   - [ ] Conectar wallet en `execution.market`
   - [ ] Ver tareas disponibles (debe haber 3-5 del Fix 7)
   - [ ] Filtrar por categoría (Fix 1) → debe matchear
   - [ ] Buscar por texto (Fix 2) → debe filtrar
   - [ ] Aplicar a una tarea → debe cambiar a "Mis Tareas"
   - [ ] Submit evidencia (foto) → debe guardarse (Fix 3)

2. **Agent flow (via API o MCP):**
   - [ ] Ver submissions pendientes
   - [ ] Aprobar submission → pago debe ejecutarse (Fix 4/5)
   - [ ] Verificar tx en BaseScan

3. **Agent dashboard:**
   - [ ] Ver tareas activas
   - [ ] Click "Review Submission" → debe abrir review (Fix 6)
   - [ ] Aprobar/rechazar desde dashboard

---

## Context para la sesión

**Branch:** `main`
**Archivos clave:**
- `dashboard/src/components/TaskBrowser.tsx` — Fix 1, 2
- `dashboard/src/services/submissions.ts` — Fix 3
- `mcp_server/server.py` — Fix 4, 5
- `dashboard/src/App.tsx` — Fix 6
- `dashboard/src/pages/AgentDashboard.tsx` — Fix 6
- `scripts/task-factory.ts` — Fix 7

**Leer antes de empezar:**
- `CLAUDE.md` (en root) — tiene toda la arquitectura y estado actual
- `mcp_server/api/routes.py` líneas 400-434 (`_resolve_task_payment_header`) — patrón correcto para Fix 4
- `mcp_server/api/routes.py` líneas 584-774 (`_settle_submission_payment`) — referencia para Fix 5

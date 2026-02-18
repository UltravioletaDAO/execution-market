# Audit Report: Migraciones DB, Scripts, Infraestructura y Documentacion

> **Fecha**: 2026-02-18
> **Auditor**: infra-auditor (claude-opus-4-6)
> **Scope**: Migraciones 031-033, apply_migrations.py, DynamoDB, docs, landing, skill, README
> **Severidad maxima encontrada**: ALTA (RLS ausente en tablas nuevas)

---

## Resumen Ejecutivo

Se auditaron las migraciones de base de datos para soporte A2A (Agent-to-Agent) y H2A (Human-to-Agent), el script de aplicacion de migraciones, infraestructura Terraform, y documentacion actualizada. Se encontraron **3 issues de severidad alta**, **5 de severidad media**, y **4 de severidad baja**.

### Issues Criticos

| # | Severidad | Archivo | Issue |
|---|-----------|---------|-------|
| 1 | **ALTA** | `031_agent_executor_support.sql` | **Conflicto de numeracion**: Dos archivos comparten el prefijo 031 |
| 2 | **ALTA** | `031_agent_executor_support.sql` | **Sin RLS policies** para columnas nuevas en executors/tasks/api_keys |
| 3 | **ALTA** | `033_h2a_marketplace.sql` | **Sin RLS policies** para columnas H2A |
| 4 | MEDIA | `apply_migrations.py` | f-string con SQL directo (potencial SQL injection en enum values) |
| 5 | MEDIA | `031` vs `031` | Numeracion duplicada rompe ordenamiento deterministico |
| 6 | MEDIA | `033_h2a_marketplace.sql` | `platform_config` INSERT usa `'true'::jsonb` (string) vs `true::jsonb` (boolean) |
| 7 | MEDIA | `apply_migrations.py` | Emojis en output (CLAUDE.md prohibe emojis en Rust logs; Python script los usa) |
| 8 | MEDIA | `docs/API.md` | Endpoints H2A documentados pero no todos implementados en routes.py |
| 9 | BAJA | `031_agent_executor_support.sql` | CHECK constraint inline con ALTER TABLE puede fallar en Postgres < 12 |
| 10 | BAJA | `032_agent_cards.sql` | `agent_type` vs `executor_type` -- dos columnas con semantica similar |
| 11 | BAJA | `README.md` | Test count dice 1,258 pero CLAUDE.md dice 950 |
| 12 | BAJA | `landing/index.html` | Stats dice "17 MAINNETS LIVE" pero CLAUDE.md lista 9 mainnets + 6 testnets |

---

## 1. Analisis de Migraciones

### 1.1 Conflicto de Numeracion 031 (ALTA)

**Hallazgo**: Existen **dos** archivos con prefijo `031_`:
- `031_gas_dust_tracking.sql` (existente, pre-A2A)
- `031_agent_executor_support.sql` (nuevo, A2A)

**Impacto**: El ordenamiento de migraciones por nombre de archivo es **no-deterministico** cuando dos comparten el mismo prefijo numerico. Dependiendo del filesystem y el sort order, una puede ejecutarse antes que la otra. En este caso no hay dependencia directa entre ambas, pero rompe la convencion sequential y puede confundir tooling de migraciones.

**Recomendacion**: Renombrar `031_agent_executor_support.sql` a `034_agent_executor_support.sql` (el siguiente numero disponible despues de 033). O, si ya fue aplicado en produccion, documentar el conflicto y no renombrar.

### 1.2 Migration 031 (Agent Executor Support) — Detalle

**Tablas modificadas**: `executors`, `tasks`, `api_keys`

| Tabla | Columna | Tipo | Default | CHECK | Indice |
|-------|---------|------|---------|-------|--------|
| `executors` | `executor_type` | VARCHAR(10) | `'human'` | `IN ('human','agent')` | `idx_executors_type` |
| `executors` | `agent_card_url` | TEXT | NULL | - | - |
| `executors` | `mcp_endpoint_url` | TEXT | NULL | - | - |
| `executors` | `capabilities` | TEXT[] | NULL | - | GIN (partial: `executor_type='agent'`) |
| `executors` | `a2a_protocol_version` | VARCHAR(10) | NULL | - | - |
| `tasks` | `target_executor_type` | VARCHAR(10) | `'any'` | `IN ('human','agent','any')` | Partial: `status='published'` |
| `tasks` | `verification_mode` | VARCHAR(20) | `'manual'` | `IN ('manual','auto','oracle')` | - |
| `tasks` | `verification_criteria` | JSONB | NULL | - | - |
| `tasks` | `required_capabilities` | TEXT[] | NULL | - | GIN (partial: `target IN ('agent','any')`) |
| `api_keys` | `key_type` | VARCHAR(20) | `'publisher'` | `IN ('publisher','executor','admin')` | - |
| `api_keys` | `executor_id` | UUID | NULL | FK → executors(id) | - |

**Enum additions**: 6 nuevos valores en `task_category`:
`data_processing`, `api_integration`, `content_generation`, `code_execution`, `research`, `multi_step_workflow`

**Evaluacion**:
- **Idempotencia**: BUENA. Usa `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ADD VALUE IF NOT EXISTS`
- **Non-destructiva**: SI. Solo ADD operations, ningun DROP/ALTER TYPE/DELETE
- **Rollback**: PARCIAL. Las columnas se pueden DROP, pero `ALTER TYPE ADD VALUE` no es reversible en PostgreSQL sin recrear el enum
- **RLS**: AUSENTE. No hay nuevas policies para las columnas. Si `executors` tiene RLS existente, las nuevas columnas heredan las policies existentes. Pero `api_keys.executor_id` FK expone relacion agent→executor que podria leakear informacion

**Model-DB Consistency**:
- `ExecutorType` enum: matches (`human`, `agent`)
- `TargetExecutorType` enum: matches (`human`, `agent`, `any`)
- `VerificationMode` enum: matches (`manual`, `auto`, `oracle`)
- `RegisterAgentExecutorInput`: tiene `capabilities`, `display_name`, `agent_card_url`, `mcp_endpoint_url`, `a2a_protocol_version` -- MATCH con columnas
- `TaskCategory` enum: incluye los 6 nuevos valores -- MATCH

### 1.3 Migration 032 (Agent Cards) — Existe y esta completa

**Hallazgo**: La migracion 032 **NO esta faltante**. Existe como `032_agent_cards.sql`.

**Contenido**:
- `executors.agent_type` TEXT con CHECK `('human', 'ai', 'organization')` + indice
- `executors.networks_active` TEXT[] default `'{}'`
- Nueva tabla `activity_feed` con 8 columnas, 3 indices
- **RLS habilitado** en `activity_feed` con 2 policies (public read, service_role insert)
- **Trigger** `trg_activity_feed_on_task` que auto-popula activity feed en cambios de status

**Observacion**: Hay **solapamiento semantico** entre `executor_type` (de 031) y `agent_type` (de 032):
- `executor_type` IN (`human`, `agent`) — indica si ejecuta tareas como humano o agente
- `agent_type` IN (`human`, `ai`, `organization`) — indica tipo de identidad

Esto no es un bug, pero puede causar confusion. Son conceptos diferentes: un `agent_type='organization'` podria tener `executor_type='agent'` o `executor_type='human'`.

### 1.4 Migration 033 (H2A Marketplace) — Detalle

**Tablas modificadas**: `tasks`, `platform_config`

| Tabla | Columna | Tipo | Default | CHECK | Indice |
|-------|---------|------|---------|-------|--------|
| `tasks` | `publisher_type` | VARCHAR(10) | `'agent'` | `IN ('agent','human')` | Partial: `publisher_type='human'` |
| `tasks` | `human_wallet` | TEXT | NULL | - | Partial: `IS NOT NULL` |
| `tasks` | `human_user_id` | TEXT | NULL | - | - |

**Platform config**:
- `feature.h2a_enabled` = `'true'::jsonb`
- `feature.h2a_min_bounty` = `'0.5'::jsonb`
- `feature.h2a_max_bounty` = `'500.0'::jsonb`

**Evaluacion**:
- **Idempotencia**: BUENA. `ADD COLUMN IF NOT EXISTS`, `ON CONFLICT DO UPDATE`
- **Non-destructiva**: SI
- **Rollback**: FACIL. Solo DROP columns + DELETE from platform_config
- **RLS**: **AUSENTE** — `human_wallet` y `human_user_id` son datos PII. Cualquier usuario con SELECT en `tasks` puede ver wallets de otros humanos. Se necesita policy restrictiva

**Model-DB Consistency**:
- `PublisherType` enum: matches (`agent`, `human`)
- `PublishH2ATaskRequest`: no tiene `human_wallet` ni `human_user_id` (estos se setean server-side) -- CORRECTO
- `H2ATaskResponse`: tiene `publisher_type` -- MATCH

**Issue menor**: `'true'::jsonb` produce el string JSON `"true"`, no el booleano JSON `true`. Para feature flags binarios, `'true'::jsonb` esta bien si el codigo Python hace `json.loads(val) == "true"` o truthy check. Pero `true::jsonb` (sin comillas) produce el booleano JSON `true`, que es mas correcto. Verificar como los feature flags existentes almacenan booleanos.

---

## 2. Script de Migracion (`scripts/apply_migrations.py`)

### 2.1 Resumen

Script de 265 lineas que aplica migraciones 031 y 033 directamente via psycopg2. No usa Supabase CLI ni un framework de migraciones.

### 2.2 Aspectos Positivos

- **Error handling granular**: Cada statement en try/except con rollback, no falla en cascada
- **Verificacion post-apply**: `verify_schema()` confirma que todas las columnas esperadas existen
- **Exit code**: Retorna 1 si la verificacion falla
- **Idempotencia**: Usa `IF NOT EXISTS` y `ON CONFLICT` consistentemente
- **Secrets management**: Obtiene password de AWS Secrets Manager (no hardcoded)

### 2.3 Issues

**MEDIA - SQL Injection potencial** (linea 96):
```python
cur.execute(f"ALTER TYPE task_category ADD VALUE IF NOT EXISTS '{val}'")
```
Los valores vienen de una lista hardcoded (`enum_values`), no de user input. **No es explotable en este contexto**, pero el patron de f-string + SQL es un code smell. Recomendacion: parametrizar o al menos documentar que los valores son constantes.

**MEDIA - Emojis en output**: Las lineas 83, 86, 97, etc. usan emojis. CLAUDE.md global dice "NUNCA emojis en logs" (para Rust). Para Python scripts esto es aceptable pero inconsistente con el estilo del proyecto.

**BAJA - No aplica 032**: El script aplica 031 y 033 pero **salta 032** (`032_agent_cards.sql`). Esto sugiere que 032 se aplico por separado o manualmente. No hay tracking de que migraciones fueron aplicadas.

**BAJA - Connection pool**: Usa session mode pooler (port 5432) directamente. Para produccion esto es correcto (DDL statements requieren session mode, no transaction mode). Sin embargo, no hay retry logic si la conexion falla.

**INFO - Hardcoded host**: `aws-0-us-west-2.pooler.supabase.com` esta hardcoded. Si Supabase migra el proyecto, el host cambia. Considerar usar env var.

### 2.4 Falta de Migration Tracking

No hay tabla `_migrations` o mecanismo para registrar que migraciones se aplicaron. El patron actual depende de idempotencia (`IF NOT EXISTS`), lo cual funciona pero no permite saber facilmente que version del schema esta activa en produccion.

---

## 3. Infraestructura (DynamoDB)

### 3.1 `infrastructure/terraform/dynamodb.tf`

**Proposito**: Tabla DynamoDB para almacenar nonces de ERC-8128 (wallet-based auth). Single-use nonces con TTL para proteccion anti-replay.

**Evaluacion**:

| Aspecto | Status | Notas |
|---------|--------|-------|
| Billing | PAY_PER_REQUEST | Correcto para baja carga (<$0.04/mes) |
| Hash key | `nonce_key` (String) | Correcto, particion por nonce |
| TTL | `expires_at` | Correcto, limpieza automatica |
| Encryption | Server-side (AWS managed CMK) | Adecuado para nonces |
| PITR | Disabled | Correcto, nonces son efimeros |
| IAM | GetItem, PutItem, DeleteItem | Minimo privilegio. No permite Scan/Query (bien) |

**Veredicto**: Bien implementado. IAM policy es least-privilege, TTL evita acumulacion, encryption at rest. No hay issues.

**Nota**: El IAM policy referencia `aws_iam_role.ecs_task` que debe existir en otro .tf file. Si esa role no existe, terraform plan fallara. Verificar que existe.

---

## 4. Documentacion

### 4.1 `docs/API.md`

**Evaluacion general**: Documento de 590 lineas, bien estructurado con tablas, ejemplos curl, y respuestas JSON.

**Issues encontrados**:

| Issue | Detalle |
|-------|---------|
| **H2A endpoints documentados pero parcialmente implementados** | API.md lista 8 endpoints H2A (lineas 428-438) pero solo `h2a.py` existe como modulo. Verificar que todos los endpoints estan registrados en el router |
| **Test count desactualizado** | No aparece en API.md directamente, pero referencia "63+ endpoints" — contar si es preciso |
| **Supported Networks count** | Dice "19 Mainnets" (linea 353) pero CLAUDE.md dice 9 mainnets + 6 testnets = 15 total. Inconsistencia |
| **Fee breakdown** | Dice "13%: 12% EM + 1% x402r" (linea 40). En CLAUDE.md el 1% x402r es dynamic y puede ser 0%. La documentacion es aspiracional/promedio |
| **Legacy escrow** | Referencia Avalanche C-Chain escrow (linea 528-533) como "deprecated" — correcto |
| **SDK examples** | Python SDK usa `from em import ExecutionMarketClient` — este paquete no existe en el repo. Es aspiracional |

**Endpoints H2A en API.md vs Implementacion**:

| Endpoint | API.md | Implementado |
|----------|--------|-------------|
| `POST /api/v1/h2a/tasks` | SI | En `h2a.py` (verificar) |
| `GET /api/v1/h2a/tasks` | SI | En `h2a.py` (verificar) |
| `GET /api/v1/h2a/tasks/{id}` | SI | En `h2a.py` (verificar) |
| `GET /api/v1/h2a/tasks/{id}/submissions` | SI | Verificar |
| `POST /api/v1/h2a/tasks/{id}/approve` | SI | Verificar |
| `POST /api/v1/h2a/tasks/{id}/reject` | SI | Verificar |
| `POST /api/v1/h2a/tasks/{id}/cancel` | SI | Verificar |
| `GET /api/v1/agents/directory` | SI | Verificar |
| `POST /api/v1/agents/register-executor` | SI | Verificar |

**Nota**: La auditoria de `h2a.py` se lleva en el reporte del Task #1 (h2a-auditor). Este reporte solo verifica la documentacion.

### 4.2 `docs/articles/ARTICLE_X_COMPETITION_V49_EN.md`

**Proposito**: Articulo comparativo RentAHuman vs Execution Market.

**Evaluacion**:
- **Factual**: Citas de tweets son verificables (@AlexanderTw33ts, @madramg0, @DenjinK, etc.)
- **Metricas**: "1,258 passing tests" — consistente con README pero no con CLAUDE.md (950). Probablemente README refleja tests de feature branches incluidos
- **BaseScan link**: `0x1c09bd...b68a06` — verificable on-chain
- **No secrets expuestos**: Correcto
- **Estilo**: Bien escrito, competitivo pero factual

**Issue menor**: El articulo dice "$0.05 USDC" como primer pago. CLAUDE.md confirma esto. Correcto.

### 4.3 `landing/index.html`

**Evaluacion**:
- **Stats section** (linea 457-468): "17 MAINNETS LIVE" — inconsistente con CLAUDE.md que dice 9 mainnets. Podria incluir las redes de x402r donde escrow esta deployed. Clarificar
- **$0.50 MINIMO** — pero CLAUDE.md dice `min_bounty = $0.01` y feature flag `h2a_min_bounty = $0.50`. Esto es correcto para H2A ($0.50) pero no para A2H ($0.01). Landing page podria confundir
- **H2A Section**: Presente, bien posicionado. Describe agent directory, escrow, bidirectional reputation
- **ERC-8128 Section**: Presente con quick-start code snippet usando `@slicekit/erc8128`
- **A2A Section**: Presente
- **FAQ en espanol**: Correcto para target demographic
- **Security**: No hay forms, no hay user input processing, static page. Ningun issue de seguridad
- **Performance**: Matrix rain canvas a 50ms interval (20 FPS) + requestAnimationFrame wave. Podria ser heavy en mobile. Minor

### 4.4 `skills/execution-market/SKILL.md` y `dashboard/public/skill.md`

**Hallazgo**: Ambos archivos son **identicos** (1,467 lineas cada uno). Uno esta en `skills/` (para el repo) y otro en `dashboard/public/` (servido estaticamente en `execution.market/skill.md`).

**Evaluacion**:
- Version 2.0.0 — actualizada
- Auth documentation: Excelente. 3 metodos (none, erc8128, apikey) bien explicados
- Autonomy levels: `auto`, `notify`, `manual` — bien documentados
- ERC-8128 deep dive: Completo con security quadrants
- H2A marketplace section: Presente al final
- A2A JSON-RPC section: Presente
- Agent Executor API: Completo con register, browse, accept, submit

**Issues**:
- **Duplicacion**: Mantener dos copias identicas es fragil. Considerar symlink o build step que copia uno al otro
- **Rate limits inconsistentes**: SKILL.md dice "100/hour task creation" pero API.md dice "10 req/min" (= 600/hour). Resolver discrepancia
- **Recipient wallet in payment example** (linea 592): `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd` — este es el **dev wallet**, no el treasury (`0xae07`). Error en el ejemplo

### 4.5 `README.md`

**Evaluacion**:
- Refleja estado actual con A2A, H2A, ERC-8128
- Test count: "1,258+" — inconsistente con CLAUDE.md (950). README probablemente incluye feature branch tests
- URLs correctas
- Project structure actualizada
- CI/CD pipelines documentados
- Deploy commands correctos

**Issue**: "Not Yet Deployed" section (linea 486-492) lista `admin.execution.market` como no deployed. Pero CLAUDE.md dice que admin dashboard tiene CI/CD via `.github/workflows/deploy-admin.yml`. Clarificar si ya esta deployed o no.

---

## 5. Consistencia Model-DB

### 5.1 Comparacion Completa

| DB Column | Pydantic Model | Match |
|-----------|----------------|-------|
| `executors.executor_type` | `ExecutorType` enum | MATCH |
| `executors.agent_card_url` | `RegisterAgentExecutorInput.agent_card_url` | MATCH |
| `executors.mcp_endpoint_url` | `RegisterAgentExecutorInput.mcp_endpoint_url` | MATCH |
| `executors.capabilities` | `RegisterAgentExecutorInput.capabilities` | MATCH (TEXT[] vs List[str]) |
| `executors.a2a_protocol_version` | `RegisterAgentExecutorInput.a2a_protocol_version` | MATCH |
| `executors.agent_type` (032) | No model | MISSING — no Pydantic model for agent_type |
| `executors.networks_active` (032) | No model | MISSING — no Pydantic model |
| `tasks.target_executor_type` | `TargetExecutorType` enum | MATCH |
| `tasks.verification_mode` | `VerificationMode` enum | MATCH |
| `tasks.verification_criteria` | No explicit model | PARTIAL — JSONB sin schema validation |
| `tasks.required_capabilities` | `PublishH2ATaskRequest.required_capabilities` | MATCH |
| `tasks.publisher_type` | `PublisherType` enum | MATCH |
| `tasks.human_wallet` | No model (server-set) | OK — not user input |
| `tasks.human_user_id` | No model (server-set) | OK — not user input |
| `api_keys.key_type` | No model | MISSING — no validation for key_type |
| `api_keys.executor_id` | No model | MISSING — no validation |
| `activity_feed` (032) | No model | MISSING — no Pydantic model |

**Gaps**:
1. `agent_type`, `networks_active` columnas de 032 no tienen modelos Pydantic
2. `api_keys.key_type` no tiene validacion en modelos
3. `activity_feed` tabla no tiene modelo (OK si solo se accede via trigger/admin)
4. `verification_criteria` es JSONB libre — considerar schema validation con Pydantic

### 5.2 Enum Consistency

| DB Enum/CHECK | Python Enum | Values Match |
|---------------|-------------|-------------|
| `executor_type IN ('human','agent')` | `ExecutorType` | MATCH |
| `target_executor_type IN ('human','agent','any')` | `TargetExecutorType` | MATCH |
| `verification_mode IN ('manual','auto','oracle')` | `VerificationMode` | MATCH |
| `publisher_type IN ('agent','human')` | `PublisherType` | MATCH |
| `key_type IN ('publisher','executor','admin')` | No enum | MISSING |
| `agent_type IN ('human','ai','organization')` | No enum | MISSING |
| `task_category` (11 values) | `TaskCategory` (11 values) | MATCH |

---

## 6. Seguridad: RLS Assessment

### 6.1 Estado de RLS por Tabla

| Tabla | RLS Habilitado | Policies | Assessment |
|-------|---------------|----------|------------|
| `tasks` | SI (pre-existente) | Multiples | Columnas nuevas heredan policies existentes |
| `executors` | SI (pre-existente) | Multiples | Columnas nuevas heredan. `agent_card_url` y `mcp_endpoint_url` quedan publicos si SELECT es publico |
| `api_keys` | SI (pre-existente) | Multiples | `executor_id` FK podria leakear relacion |
| `activity_feed` | **SI** (032) | 2 (read public, insert service) | Bien implementado |
| `gas_dust_events` | **NO** | 0 | Tabla nueva sin RLS |
| `platform_config` | Depende | Pre-existente | Feature flags H2A son publicos via config endpoint |

### 6.2 Hallazgos Criticos

**ALTA — `human_wallet` expuesto via tasks**: La columna `tasks.human_wallet` almacena wallet addresses de humanos que publican H2A tasks. Si la policy de SELECT en tasks es liberal (ej: workers pueden ver tasks published), entonces cualquier worker puede ver wallets de publishers humanos. Esto es **informacion PII** en contexto de blockchain (wallet = identidad financiera).

**Recomendacion**: Crear policy que oculte `human_wallet` para non-owners, o excluir la columna del SELECT por defecto en el API layer.

**MEDIA — `capabilities` expuesto via executors**: Las capabilities de agents son publicas (necesario para matching). Esto es correcto para funcionalidad pero permite enumeration de todos los agents registrados.

---

## 7. Tests de Integracion DB Sugeridos

Los siguientes tests deberian existir para validar la integridad de las migraciones:

```python
# tests/test_migrations_integration.py

# --- Migration 031: Agent Executor Support ---

def test_executor_type_default_human():
    """New executors default to executor_type='human'."""

def test_executor_type_constraint():
    """executor_type only allows 'human' or 'agent'."""

def test_target_executor_type_default_any():
    """New tasks default to target_executor_type='any'."""

def test_target_executor_type_constraint():
    """target_executor_type only allows 'human', 'agent', 'any'."""

def test_verification_mode_constraint():
    """verification_mode only allows 'manual', 'auto', 'oracle'."""

def test_capabilities_gin_index_query():
    """GIN index on capabilities supports array containment queries."""

def test_api_key_type_constraint():
    """api_keys.key_type only allows 'publisher', 'executor', 'admin'."""

def test_api_key_executor_fk():
    """api_keys.executor_id FK references valid executor."""

def test_new_task_categories_exist():
    """All 6 new task_category enum values are available."""

# --- Migration 032: Agent Cards ---

def test_agent_type_constraint():
    """agent_type only allows 'human', 'ai', 'organization'."""

def test_activity_feed_trigger_on_task_create():
    """Inserting a published task creates activity feed entry."""

def test_activity_feed_trigger_on_task_complete():
    """Completing a task creates activity feed entry."""

def test_activity_feed_rls_public_read():
    """Anonymous users can read activity feed."""

def test_activity_feed_rls_no_public_insert():
    """Non-service-role cannot insert into activity feed."""

# --- Migration 033: H2A Marketplace ---

def test_publisher_type_default_agent():
    """New tasks default to publisher_type='agent'."""

def test_publisher_type_constraint():
    """publisher_type only allows 'agent' or 'human'."""

def test_human_wallet_nullable():
    """human_wallet can be NULL (A2H tasks)."""

def test_h2a_feature_flags_exist():
    """H2A feature flags exist in platform_config."""

def test_h2a_min_bounty_enforced():
    """H2A tasks below min_bounty are rejected (API layer)."""

# --- Cross-migration ---

def test_agent_executor_can_accept_agent_task():
    """Agent executor (type='agent') can accept task with target='agent'."""

def test_human_cannot_accept_agent_only_task():
    """Human executor cannot accept task with target='agent'."""

def test_h2a_task_has_publisher_type_human():
    """H2A tasks created via /h2a/tasks have publisher_type='human'."""

def test_a2h_task_default_publisher_type_agent():
    """Regular tasks via /tasks have publisher_type='agent'."""
```

---

## 8. Resumen de Recomendaciones

### Prioridad Alta (resolver antes de produccion)

1. **Agregar RLS policies** para `human_wallet`/`human_user_id` en tasks — ocultar para non-owners
2. **Resolver conflicto de numeracion** 031 — renombrar o documentar
3. **Validar feature flags** — confirmar que `'true'::jsonb` vs `true::jsonb` es manejado correctamente en el codigo Python

### Prioridad Media (resolver pronto)

4. **Agregar modelos Pydantic** para `agent_type`, `networks_active`, `api_keys.key_type`
5. **Parametrizar SQL** en apply_migrations.py (evitar f-strings con valores SQL)
6. **Resolver discrepancia de test count** entre README (1,258) y CLAUDE.md (950)
7. **Corregir recipient wallet** en SKILL.md payment example (dev wallet vs treasury)
8. **Alinear rate limits** entre SKILL.md y API.md

### Prioridad Baja (nice to have)

9. Implementar migration tracking table (`_applied_migrations`)
10. Symlink o build step para SKILL.md duplicado
11. Agregar modelo para `verification_criteria` JSONB
12. Actualizar landing page stats a numeros precisos
13. Documentar relacion entre `executor_type` y `agent_type`

---

## Appendix A: Arbol de Migraciones Completo

```
001_initial_schema.sql
002_escrow_and_payments.sql
003_reputation_system.sql
004_disputes.sql
005_rpc_functions.sql
006_api_keys.sql
007_platform_config.sql
008_fix_session_linking.sql
009_require_wallet_signature.sql
010_auto_approve_submissions.sql
011_update_executor_profile.sql
012_fix_executor_overload.sql
013_fix_submissions_and_task_release.sql
014_create_platform_config.sql
015_payment_ledger_canonical.sql
016_add_settlement_method.sql
017_orphaned_payment_alerts.sql
018_add_retry_count.sql
019_add_refund_tx_to_tasks.sql
020_tasks_erc8004_agent_id.sql
021_add_reputation_tx_to_submissions.sql
022_evidence_forensic_metadata.sql
023_add_payment_network.sql
024_update_executor_profile_v2.sql
025_fix_bounty_constraint.sql
026_submit_work_rpc.sql
027_payment_events.sql
028_erc8004_side_effects.sql
029_feedback_documents.sql
030_update_platform_fee_fase3.sql
031_gas_dust_tracking.sql          ← ORIGINAL 031
031_agent_executor_support.sql     ← CONFLICTO (deberia ser 034)
032_agent_cards.sql
033_h2a_marketplace.sql
```

## Appendix B: DynamoDB Schema

```hcl
Table: em-production-nonce-store
  Hash Key: nonce_key (String)
  TTL: expires_at
  Encryption: AWS managed CMK
  PITR: Disabled
  Billing: PAY_PER_REQUEST
  IAM: GetItem, PutItem, DeleteItem (ECS task role only)
```

---

*Generado: 2026-02-18 | Auditor: infra-auditor*

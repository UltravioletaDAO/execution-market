# EXECUTION MARKET - TODO MASTER CONSOLIDADO v4.0.0

> **Generado**: 2026-01-25
> **Versión**: 4.0.0 (GAP ANALYSIS V2 - 8 SUBAGENT SYNTHESIS)
> **Fuentes**: TODO.md (0-50), TODO-1.md (51-100), TODO-2.md (101-157), SPEC.md, PLAN.md, PROGRESS.md, migrations/, dashboard/src/, ARTICLE_X_COMPETITION_V35.md, grok-erc8004-overall-brainstorming.txt (777 líneas), gemini-v32-analisis.txt (307 líneas), mcp_server/server.py (real code), .internal/REPUTATION_SECRET_SAUCE.md
> **Total Items**: 294 (264 anteriores + 30 nuevos de GAP ANALYSIS V2)
> **Gap Analysis**: `.internal/GAP_ANALYSIS_REPORT_V2_20260125.md`
> **Gaps Totales Identificados**: ~180+ elementos de 8 análisis paralelos

---

## LEYENDA

- `[x]` = Implementado (verificado en código)
- `[ ]` = Pendiente
- `[~]` = Parcialmente implementado
- **P0** = Blocker (sin esto no hay MVP)
- **P1** = Crítico (primera semana post-MVP)
- **P2** = Importante (primer mes)
- **P3** = Nice-to-have (backlog)

---

## ESTADO ACTUAL DE IMPLEMENTACIÓN

### Ya Implementado (verificado en código)
- [x] Database schema con PostGIS y RLS (001-004 migrations)
- [x] React Dashboard (TaskCard, TaskList, TaskDetail, SubmissionForm, AuthModal, LanguageSwitcher)
- [x] MCP Server con 6 tools (em_publish_task, em_get_tasks, etc.)
- [x] Auth UI con Supabase
- [x] ERC-8004 registration en Sepolia (Agent ID 469)
- [x] x402r contract addresses configuradas
- [x] Enums de task_type, task_status, submission_status, dispute_status
- [x] Triggers para updated_at, executor_stats, expire_tasks
- [x] RLS policies para executors, tasks, submissions

### Pendiente Crítico (P0)
- [ ] Wallet abstraction (Crossmint/Magic)
- [ ] Off-ramp Colombia (Nequi)
- [ ] x402r integration (merchant registration)
- [ ] Task schema JSON validation
- [ ] Evidence upload flow
- [ ] **NUEVO: Bayesian reputation layer**
- [ ] **NUEVO: Partial payout flow**
- [ ] **NUEVO: Agent bond mechanism**

---

# FASE 0: FUNDAMENTOS
> **Objetivo**: Infraestructura base que habilita todo lo demás
> **Timeline**: Semana 1-2

## 0.1 Wallet Abstraction (P0) [Items #1-3]

### [ ] #1 - Integrar Crossmint para email-based wallets
**Status**: NOT STARTED
**Descripción**: Usuarios sin crypto experience pueden crear cuenta con email
**Archivos**: `dashboard/src/lib/crossmint.ts` (crear)
**Dependencias**: Crossmint API key
```typescript
// Flujo esperado
const wallet = await crossmint.createWallet({ email: user.email });
const address = wallet.address; // 0x...
```

### [ ] #2 - Alternativa Magic.link como fallback
**Status**: NOT STARTED
**Descripción**: Backup si Crossmint falla o para otras regiones
**Archivos**: `dashboard/src/lib/magic.ts` (crear)

### [ ] #3 - Wallet selector unificado
**Status**: NOT STARTED
**Descripción**: UI que permite elegir: email wallet, MetaMask, WalletConnect
**Archivos**: `dashboard/src/components/WalletSelector.tsx` (crear)

## 0.2 Off-ramp Colombia (P0) [Items #4-6]

### [ ] #4 - Integración Nequi API
**Status**: NOT STARTED
**Descripción**: Conversión USDC → COP directa a Nequi
**Archivos**: `mcp-server/src/integrations/nequi.py` (crear)
**API Docs**: https://developers.nequi.com/

### [ ] #5 - KYC simplificado para off-ramp
**Status**: NOT STARTED
**Descripción**: Solo cédula + selfie para montos < $500 USD/mes
**Dependencias**: Veriff o Onfido integration

### [ ] #6 - Fallback Binance P2P
**Status**: NOT STARTED
**Descripción**: Para usuarios que prefieran o donde Nequi no funcione
**Notas**: Guía manual con deep link a Binance

## 0.3 Task Schema JSON (P0) [Items #7-9]

### [x] #7 - Enums de task_type definidos
**Status**: DONE (001_initial_schema.sql)
**Tipos**: physical_presence, knowledge_access, human_authority, simple_action, digital_physical

### [ ] #8 - JSON Schema para evidence por tipo
**Status**: NOT STARTED
**Descripción**: Cada task_type tiene schema de evidencia diferente
**Archivos**: `mcp-server/src/schemas/evidence/` (crear directorio)
```json
// physical_presence.json
{
  "required": ["photo_url", "gps_coords", "timestamp"],
  "properties": {
    "photo_url": { "type": "string", "format": "uri" },
    "gps_coords": { "$ref": "#/definitions/geopoint" },
    "timestamp": { "type": "string", "format": "date-time" }
  }
}
```

### [ ] #9 - Validación de evidence en submission
**Status**: NOT STARTED
**Descripción**: Rechazar submissions que no cumplan schema
**Archivos**: `mcp-server/src/tools/submit_work.py`

## 0.4 MCP Server Enhancements (P0) [Items #10-12]

### [x] #10 - Tools básicos implementados (AGENT-SIDE)
**Status**: DONE
**Tools reales en código** (verificado 2026-01-24):
1. `em_publish_task` - Publicar tarea
2. `em_get_tasks` - Listar tareas (filtros)
3. `em_get_task` - Detalles de una tarea
4. `em_check_submission` - Ver submissions
5. `em_approve_submission` - Aprobar/rechazar
6. `em_cancel_task` - Cancelar tarea

**NOTA**: Tools para WORKERS (apply, submit_work, get_my_tasks) aún NO implementados - ver items nuevos abajo

### [ ] #11 - Tool: em_apply_to_task (WORKER)
**Status**: NOT STARTED
**Descripción**: Worker aplica a una tarea disponible
**Archivos**: `mcp_server/server.py` (agregar tool)
**Flow**:
1. Worker ve tarea disponible
2. Envía application con mensaje opcional
3. Task pasa a status "has_applications"
4. Agent puede asignar

### [ ] #11b - Tool: em_submit_work (WORKER)
**Status**: NOT STARTED
**Descripción**: Worker envía evidence de trabajo completado
**Archivos**: `mcp_server/server.py` (agregar tool)
**Params**:
- task_id
- executor_id
- evidence (JSON matching task schema)
**Flow**:
1. Worker sube evidence
2. Trigger partial payout (si configurado)
3. Notifica agent para review

### [ ] #11c - Tool: em_get_my_tasks (WORKER)
**Status**: NOT STARTED
**Descripción**: Worker ve sus tareas asignadas/completadas
**Archivos**: `mcp_server/server.py` (agregar tool)
**Filters**: status (assigned, in_progress, completed, disputed)

### [ ] #11d - Tool: em_withdraw_earnings (WORKER)
**Status**: NOT STARTED
**Descripción**: Worker retira earnings a wallet/off-ramp
**Archivos**: `mcp_server/server.py` (agregar tool)
**Dependencias**: #4 (Nequi), wallet abstraction

### [ ] #12 - Tool: em_assign_task (AGENT)
**Status**: NOT STARTED
**Descripción**: Agent asigna un aplicante a su tarea
**Archivos**: `mcp_server/server.py` (agregar tool)

---

# FASE 1: MVP CORE
> **Objetivo**: Flujo completo de una tarea de principio a fin
> **Timeline**: Semana 3-4

## 1.1 Task Flow Básico (P0) [Items #13-20]

### [x] #13 - Crear tarea desde dashboard
**Status**: DONE (TaskList.tsx, TaskDetail.tsx)

### [x] #14 - Listar tareas disponibles
**Status**: DONE (TaskList.tsx con filtros)

### [x] #15 - Aplicar a tarea
**Status**: DONE (task_applications table + MCP tool)

### [ ] #16 - Asignar aplicante a tarea
**Status**: NOT STARTED
**Descripción**: Agente selecciona al mejor aplicante
**Archivos**: `mcp-server/src/tools/assign_task.py` (crear)

### [x] #17 - Enviar submission
**Status**: DONE (SubmissionForm.tsx + MCP tool)

### [ ] #18 - Upload de evidencia a storage
**Status**: NOT STARTED
**Descripción**: Subir fotos/archivos a Supabase Storage
**Archivos**: `dashboard/src/lib/storage.ts` (crear)

### [ ] #19 - Verificación automática tier 1
**Status**: NOT STARTED
**Descripción**: Auto-checks (GPS match, timestamp válido, foto no duplicada)
**Archivos**: `mcp-server/src/verification/auto_check.py` (crear)

### [ ] #20 - Pago automático post-verificación
**Status**: NOT STARTED
**Descripción**: Si pasa auto-check, trigger x402 payment
**Dependencias**: x402 integration (#21)

## 1.2 x402 Básico (P0) [Items #21-25]

### [~] #21 - x402 contract addresses configuradas
**Status**: PARTIAL (addresses en config, no integration code)
**Archivos**: `.env` con X402_CONTRACT_ADDRESS

### [ ] #22 - Escrow deposit al crear tarea
**Status**: NOT STARTED
**Descripción**: Agente deposita bounty en escrow al publicar
**Archivos**: `mcp-server/src/integrations/x402/escrow.py` (crear)
```python
async def deposit_escrow(task_id: str, amount: Decimal, token: str = "USDC"):
    # 1. Approve token spend
    # 2. Call ChambaEscrow.deposit(task_id, amount)
    pass
```

### [ ] #23 - Release escrow al completar
**Status**: NOT STARTED
**Descripción**: Llamar release cuando submission aprobada
**Archivos**: `mcp-server/src/integrations/x402/escrow.py`

### [ ] #24 - Refund escrow si tarea expira
**Status**: NOT STARTED
**Descripción**: Auto-refund a agente si nadie completa
**Archivos**: `mcp-server/src/jobs/expire_tasks.py` (crear)

### [ ] #25 - Fee collection (6-8%)
**Status**: NOT STARTED
**Descripción**: Platform fee se cobra al release
**Notas**: Configurable por task_type y volumen

## 1.3 Dashboard MVP (P1) [Items #26-32]

### [x] #26 - Auth modal con Supabase
**Status**: DONE (AuthModal.tsx)

### [x] #27 - Language switcher ES/EN
**Status**: DONE (LanguageSwitcher.tsx)

### [ ] #28 - Vista de mis earnings
**Status**: NOT STARTED
**Descripción**: Panel mostrando ganancias totales, pendientes, historial
**Archivos**: `dashboard/src/components/EarningsPanel.tsx` (crear)

### [ ] #29 - Vista de mis tareas (como worker)
**Status**: NOT STARTED
**Descripción**: Tareas asignadas, en progreso, completadas
**Archivos**: `dashboard/src/pages/MyTasks.tsx` (crear)

### [ ] #30 - Notificaciones in-app
**Status**: NOT STARTED
**Descripción**: Alertas de nuevas tareas, aprobaciones, pagos
**Archivos**: `dashboard/src/components/NotificationBell.tsx` (crear)

### [ ] #31 - Mobile-responsive layout
**Status**: NOT STARTED
**Descripción**: Dashboard funciona bien en móvil
**Archivos**: Tailwind responsive classes en todos los componentes

### [ ] #32 - PWA manifest
**Status**: NOT STARTED
**Descripción**: Instalable como app en móvil
**Archivos**: `dashboard/public/manifest.json` (crear)

## 1.4 Verification Tier 1-2 (P1) [Items #33-38]

### [ ] #33 - Auto-check: GPS validation
**Status**: NOT STARTED
**Descripción**: Verificar que coords de foto están dentro de radio de tarea
**Archivos**: `mcp-server/src/verification/checks/gps.py` (crear)
```python
def check_gps(submission: dict, task: dict) -> bool:
    distance = haversine(submission.gps, task.location)
    return distance <= task.radius_meters
```

### [ ] #34 - Auto-check: Timestamp validation
**Status**: NOT STARTED
**Descripción**: Foto tomada dentro de ventana de tiempo válida
**Archivos**: `mcp-server/src/verification/checks/timestamp.py` (crear)

### [ ] #35 - Auto-check: Duplicate detection
**Status**: NOT STARTED
**Descripción**: Hash perceptual para detectar fotos repetidas
**Archivos**: `mcp-server/src/verification/checks/duplicate.py` (crear)
**Dependencias**: imagehash library

### [ ] #36 - AI Review: Image analysis
**Status**: NOT STARTED
**Descripción**: Claude Vision verifica contenido de foto
**Archivos**: `mcp-server/src/verification/ai_review.py` (crear)
```python
async def ai_review_image(image_url: str, task_description: str) -> VerificationResult:
    response = await anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": image_url}},
                {"type": "text", "text": f"Does this image show: {task_description}?"}
            ]
        }]
    )
    return parse_verification(response)
```

### [ ] #37 - Verificación tier routing
**Status**: NOT STARTED
**Descripción**: Auto-route a tier correcto según confianza
**Reglas**:
- Score >= 0.95 → Auto-approve (Tier 1)
- Score >= 0.70 → AI Review (Tier 2)
- Score >= 0.50 → Agent Review (Tier 3)
- Score < 0.50 → Human Arbitration (Tier 4)

### [ ] #38 - Verification audit log
**Status**: NOT STARTED
**Descripción**: Registrar cada verificación para disputas
**Archivos**: Tabla `verification_log` en migrations

---

# FASE 2: PAGOS AVANZADOS
> **Objetivo**: x402r refunds, streaming, dynamic bounties, PROTECCIONES WORKER
> **Timeline**: Semana 5-8

## 2.1 x402r Refunds (P1) [Items #39-45]

### [ ] #39 - Registrar como merchant en x402r
**Status**: NOT STARTED
**Descripción**: Execution Market = merchant que puede emitir refunds
**Archivos**: Script de setup one-time
**Contract**: X402R en Base Sepolia

### [ ] #40 - Refund automático por timeout
**Status**: NOT STARTED
**Descripción**: Si worker no entrega en deadline, refund a agent
**Archivos**: `mcp-server/src/jobs/process_timeouts.py` (crear)

### [ ] #41 - Refund parcial por trabajo incompleto
**Status**: NOT STARTED
**Descripción**: 50% refund si trabajo parcialmente válido
**Archivos**: `mcp-server/src/integrations/x402/refund.py` (crear)

### [ ] #42 - Proof of attempt (GROK SOLUTION)
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Worker recibe 10-20% por intento válido aunque tarea falle
**Formula**: `attempt_payout = bounty * attempt_percent` (10-20%)
**Archivos**:
- `mcp-server/src/verification/proof_of_attempt.py` (crear)
- Columna `is_proof_of_attempt: boolean` en submissions
**Ejemplo**: Tarea $10, attempt_bonus: 15% → $1.50 por intento documentado
**Razón**: Incentiva intentos en tareas difíciles, reduce fear of failure
**Validación**: Requiere evidencia de obstáculo (foto, descripción, timestamp)

### [ ] #43 - Refund dispute flow
**Status**: NOT STARTED
**Descripción**: Worker puede disputar refund
**Archivos**: Extensión de disputes table

### [ ] #44 - Refund analytics dashboard
**Status**: NOT STARTED
**Descripción**: Ver tasa de refunds por agent, task_type, worker
**Archivos**: `dashboard/src/pages/Analytics.tsx` (crear)

### [ ] #45 - Agent bond for refund abuse (GROK SOLUTION)
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Agents depositan bounty + 10-20% extra como bond
**Formula**: `total_deposit = bounty * (1 + bond_percent)` donde bond_percent = 0.10-0.20
**Slashing**: Bond se pierde si arbitration dice unfair rejection
**Archivos**:
- Columna `agent_bond_usd: decimal` en tasks
- `mcp-server/src/integrations/x402/agent_bond.py` (crear)
**Razón**: Makes respawn expensive, equilibra poder agent-worker

## 2.2 Partial Payouts (P1 - NUEVO DE GROK) [Items #46-50]

### [ ] #46 - Partial payout on submission (GROK SOLUTION)
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: 30-50% del bounty se paga al subir proof, resto tras approve
**Formula**:
```python
partial_percent = 0.30  # configurable 30-50%
on_submission = bounty * partial_percent
on_approval = bounty * (1 - partial_percent) - platform_fee
```
**Archivos**:
- Columna `partial_payout_percent: decimal` en tasks (default 0.30)
- `mcp-server/src/payments/partial_release.py` (crear)
**Razón**: Worker no pierde 100% si agent rechaza injustamente
**Config**: Agent puede configurar % por tarea

### [ ] #47 - Partial payout trigger en submission
**Status**: NOT STARTED
**Descripción**: Automáticamente liberar partial al subir evidence
**Archivos**: `mcp-server/src/tools/submit_work.py` (modificar)
**Flow**:
1. Worker sube evidence
2. System valida schema básico
3. Si válido, release partial_payout
4. Rest queda en escrow pending approval

### [ ] #48 - Escrow split accounting
**Status**: NOT STARTED
**Descripción**: Track qué parte del escrow fue released vs pending
**Archivos**:
- Columnas `partial_released: boolean`, `partial_amount: decimal` en submissions
- Vista `escrow_status` con breakdown

### [ ] #49 - Partial payout UI en dashboard
**Status**: NOT STARTED
**Descripción**: Worker ve cuánto recibió parcial, cuánto pending
**Archivos**: `dashboard/src/components/PayoutStatus.tsx` (crear)

### [ ] #50 - Partial rollback en rejection válida
**Status**: NOT STARTED
**Descripción**: Si rejection es válida (arbitration), partial se descuenta de futuras earnings
**Notas**: Controversia - considerar alternativas (no rollback, solo rep hit)

## 2.3 Payment Channels (P1) [Items #51-55]

### [ ] #51 - Multi-token support
**Status**: NOT STARTED
**Descripción**: Además de USDC: EURC, DAI, native tokens
**Archivos**: `mcp-server/src/integrations/x402/tokens.py` (crear)

### [ ] #52 - Token preference por worker
**Status**: NOT STARTED
**Descripción**: Worker elige en qué token quiere cobrar
**Archivos**: Columna `preferred_token` en executors table

### [ ] #53 - Auto-swap si token no disponible
**Status**: NOT STARTED
**Descripción**: Si agent paga en USDC pero worker quiere DAI, swap
**Dependencias**: Uniswap/1inch integration

### [ ] #54 - Batch payments
**Status**: NOT STARTED
**Descripción**: Pagar múltiples workers en una transacción
**Notas**: Ahorra gas, útil para tareas masivas

### [ ] #55 - Payment receipt NFT (opcional)
**Status**: NOT STARTED
**Descripción**: Mint recibo como proof de trabajo pagado
**Notas**: Útil para tax reporting

## 2.4 Superfluid Streaming (P2) [Items #56-62]

### [ ] #56 - Superfluid SDK integration
**Status**: NOT STARTED
**Descripción**: Setup Superfluid para pagos por segundo
**Archivos**: `mcp-server/src/integrations/superfluid/` (crear)
**Docs**: https://docs.superfluid.finance/

### [ ] #57 - Stream creation para long tasks
**Status**: NOT STARTED
**Descripción**: Tareas >1hr pagan por segundo de trabajo
**Ejemplo**: $10/hr task = $0.00277/segundo

### [ ] #58 - Stream pause/resume
**Status**: NOT STARTED
**Descripción**: Pausar stream si worker toma break
**Archivos**: `mcp-server/src/integrations/superfluid/stream.py`

### [ ] #59 - Stream monitoring dashboard
**Status**: NOT STARTED
**Descripción**: Ver streams activos en tiempo real
**Archivos**: `dashboard/src/components/StreamMonitor.tsx` (crear)

### [ ] #60 - Live verification + streaming
**Status**: NOT STARTED
**Descripción**: Verificación continua durante stream
**Notas**: Cada X minutos, check que trabajo continúa
**Ejemplo**: Stream + webcam verification cada 5 min

### [ ] #61 - Stream auto-close on completion
**Status**: NOT STARTED
**Descripción**: Detectar fin de tarea y cerrar stream
**Archivos**: `mcp-server/src/integrations/superfluid/auto_close.py`

### [ ] #62 - Stream dispute flow
**Status**: NOT STARTED
**Descripción**: Disputar stream payments
**Archivos**: Extensión de disputes para streams

## 2.5 Dynamic Bounty (P2) [Items #63-68]

### [ ] #63 - Bounty escalation config
**Status**: NOT STARTED
**Descripción**: Configurar cómo escala el precio si nadie toma
**Schema**:
```json
{
  "initial_bounty": 5.00,
  "escalation_rate": 0.10,
  "escalation_interval_hours": 24,
  "max_bounty": 25.00,
  "max_escalations": 5
}
```

### [ ] #64 - Bounty escalation job
**Status**: NOT STARTED
**Descripción**: Job que sube bounties automáticamente
**Archivos**: `mcp-server/src/jobs/escalate_bounties.py` (crear)

### [ ] #65 - Bounty history tracking
**Status**: NOT STARTED
**Descripción**: Log de cambios de precio por tarea
**Archivos**: Tabla `bounty_history` en migrations

### [ ] #66 - Urgency multiplier
**Status**: NOT STARTED
**Descripción**: Tareas urgentes pagan más desde el inicio
**Notas**: 1.5x para < 2hr deadline, 2x para < 30min

### [ ] #67 - Location premium
**Status**: NOT STARTED
**Descripción**: Zonas difíciles pagan más automáticamente
**Notas**: Rural > Urban, dangerous zones > safe

### [ ] #68 - Surge pricing durante picos
**Status**: NOT STARTED
**Descripción**: Más demanda = precios más altos
**Archivos**: `mcp-server/src/pricing/surge.py` (crear)

---

# FASE 3: REPUTACIÓN
> **Objetivo**: ERC-8004 + BAYESIAN LAYER (GROK SOLUTION) + bidireccional
> **Timeline**: Semana 9-12

## 3.1 ERC-8004 Core (P1) [Items #69-77]

### [x] #69 - Agent registrado en ERC-8004
**Status**: DONE (Agent ID 469 en Sepolia)

### [ ] #70 - Worker registration en ERC-8004
**Status**: NOT STARTED
**Descripción**: Cada worker obtiene ID en registry
**Archivos**: `mcp-server/src/integrations/erc8004/register.py` (crear)

### [ ] #71 - Raw reputation score storage
**Status**: NOT STARTED
**Descripción**: Almacenar ratings individuales on-chain (raw data)
**Notas**: ERC-8004 solo guarda raw, aggregation es off-chain
**Schema**: (rater, ratee, score, task_id, task_value, timestamp)

### [ ] #72 - Reputation events emission
**Status**: NOT STARTED
**Descripción**: Emit events para indexing
**Events**: `ReputationUpdated(executor_id, rater, score, task_value)`

### [ ] #73 - Skill-specific reputation
**Status**: NOT STARTED
**Descripción**: Score separado por tipo de tarea
**Archivos**: Tabla `reputation_by_skill` en migrations

### [ ] #74 - Reputation display en dashboard
**Status**: NOT STARTED
**Descripción**: Ver score propio y de otros workers
**Archivos**: `dashboard/src/components/ReputationBadge.tsx` (crear)

### [ ] #75 - Minimum reputation requirements
**Status**: NOT STARTED
**Descripción**: Algunas tareas requieren mínimo score
**Ejemplo**: task.min_reputation = 70

### [ ] #76 - Reputation-based task matching
**Status**: NOT STARTED
**Descripción**: Priorizar workers con mejor score
**Archivos**: `mcp-server/src/matching/reputation.py` (crear)

### [ ] #77 - Cross-platform reputation import
**Status**: NOT STARTED
**Descripción**: Importar reputation de TaskRabbit, Fiverr, etc.
**Notas**: Verificación manual inicial, luego automatizada

## 3.2 BAYESIAN AGGREGATION LAYER (P1 - GROK SOLUTION) [Items #78-87]

> **CRITICAL**: Esta sección implementa el "secret sauce" de REPUTATION_SECRET_SAUCE.md
> **INTERNO**: El Bayesian formula NO se publica en el artículo

### [ ] #78 - Bayesian Average calculation (CORE)
**Status**: NOT STARTED
**Prioridad**: P0-P1
**Descripción**: Implementar la fórmula Bayesian para scores
**Formula**:
```python
def calculate_bayesian_score(executor_id: str) -> float:
    """
    Bayesian Score = (C × m + Σ(ratings × weight)) / (C + Σ weights)

    C = minimum tasks to stabilize (15-20)
    m = prior (neutral starting point, 50/100)
    weight = log(task_value_usd + 1) * decay_factor
    decay_factor = 0.9^(months_old)
    """
    C = 15  # Configurable
    m = 50  # Neutral prior

    ratings = get_ratings_for_executor(executor_id)
    if not ratings:
        return m

    weighted_sum = 0
    total_weight = 0

    for rating in ratings:
        value_weight = math.log(rating.task_value_usd + 1)
        decay_factor = 0.9 ** rating.months_old
        final_weight = value_weight * decay_factor

        weighted_sum += rating.score * final_weight
        total_weight += final_weight

    bayesian_score = (C * m + weighted_sum) / (C + total_weight)
    return round(bayesian_score, 2)
```
**Archivos**:
- `mcp-server/src/reputation/bayesian.py` (crear)
- Subgraph query para ratings

### [ ] #79 - Task-value weighting
**Status**: NOT STARTED
**Descripción**: Peso logarítmico por valor de tarea
**Formula**: `weight = log(bounty_usd + 1)`
**Ejemplos**:
- Tarea $0.50 → weight ≈ 0.4
- Tarea $5.00 → weight ≈ 1.8
- Tarea $50.00 → weight ≈ 3.9
- Tarea $150.00 → weight ≈ 5.0
**Razón**: $150 notarización pesa más que 50 verifs de $0.50

### [ ] #80 - Reputation decay over time
**Status**: NOT STARTED
**Descripción**: Ratings antiguas pierden peso
**Formula**: `decay = 0.9^(months_old)`
**Ejemplos**:
- 1 mes → 0.9 (90% weight)
- 6 meses → 0.53 (53% weight)
- 12 meses → 0.28 (28% weight)
**Razón**: Permite "segunda oportunidad" - errores viejos importan menos
**Archivos**: Columna `created_at` en ratings para calcular age

### [ ] #81 - Bayesian parameters configurable
**Status**: NOT STARTED
**Descripción**: Permitir ajustar C, m, decay rate por entorno
**Config**:
```yaml
reputation:
  bayesian:
    C: 15          # minimum tasks
    m: 50          # prior (0-100)
    decay_rate: 0.9
    weight_function: "log"  # or "linear", "sqrt"
```
**Archivos**: `config/reputation.yaml` (crear)

### [ ] #82 - Subgraph para Bayesian indexing
**Status**: NOT STARTED
**Descripción**: Indexar ratings on-chain para cálculo off-chain
**Archivos**: `subgraph/schema.graphql`, `subgraph/mappings/`
**Query**:
```graphql
query ExecutorRatings($executorId: ID!) {
  ratings(where: { ratee: $executorId }) {
    rater
    score
    taskValue
    timestamp
  }
}
```

### [ ] #83 - Bayesian score caching
**Status**: NOT STARTED
**Descripción**: Cache scores para performance (recalcular cada N minutos)
**Archivos**: Redis cache o PostgreSQL materialized view
**TTL**: 5-15 minutos

### [ ] #84 - Bayesian API endpoint
**Status**: NOT STARTED
**Descripción**: Exponer scores via REST/GraphQL
**Endpoints**:
- `GET /api/reputation/{executor_id}` → bayesian_score
- `GET /api/reputation/{executor_id}/breakdown` → detailed components
**Archivos**: `mcp-server/src/api/reputation.py` (crear)

### [ ] #85 - Bidirectional Bayesian (agents too)
**Status**: NOT STARTED
**Descripción**: Agents también reciben Bayesian scores de workers
**Razón**: Abusar de refunds/rejections les duele en rep
**Archivos**: Extender #78 para agent_id como ratee

### [ ] #86 - Sybil resistance via Bayesian
**Status**: NOT STARTED
**Descripción**: Documentar cómo Bayesian resiste Sybil
**Notas**: Para inflar score necesitas muchas tareas PAGADAS de alto valor
- Costoso en aggregate
- Prior "jala" hacia neutral
- Decay reduce value de bulk attacks
**Archivos**: `docs/sybil-resistance.md`

### [ ] #87 - Bayesian score display en UI
**Status**: NOT STARTED
**Descripción**: Mostrar score calculado en dashboard
**Archivos**:
- `dashboard/src/components/BayesianScore.tsx` (crear)
- Integrar con ReputationBadge

## 3.3 Context Tags and Appeals (P2 - GROK SOLUTION) [Items #88-93]

### [ ] #88 - Context tags para ratings
**Status**: NOT STARTED
**Descripción**: Tags obligatorios explicando rating bajo
**Tags predefinidos**:
- `delayed-traffic`: Retraso por tráfico
- `weather-issue`: Problema climático
- `access-denied`: No se pudo acceder
- `tech-failure`: Falla técnica
- `communication-gap`: Mal entendido
**Archivos**: Columna `context_tags: text[]` en ratings

### [ ] #89 - Rating appeal mechanism
**Status**: NOT STARTED
**Descripción**: Worker puede apelar rating injusta
**Flow**:
1. Worker solicita appeal con evidencia
2. Arbitration (2-of-3) revisa
3. Si gana, rating se anula o reduce weight
**Archivos**: Tabla `rating_appeals` en migrations

### [ ] #90 - Appeal fee and refund
**Status**: NOT STARTED
**Descripción**: Pequeño bond para apelar, refunded si gana
**Amount**: $0.50-$1.00 USDC
**Razón**: Evita spam appeals

### [ ] #91 - Appeal resolution by arbitrators
**Status**: NOT STARTED
**Descripción**: Pool de arbitrators pagados por appeals
**Payment**: 50% del appeal fee va a arbitrators
**Archivos**: `mcp-server/src/disputes/appeal_resolution.py`

### [ ] #92 - Context-aware reputation filtering
**Status**: NOT STARTED
**Descripción**: Agents pueden filtrar ratings por context
**Ejemplo**: "Ignorar ratings con tag weather-issue"
**Archivos**: Query filters en Bayesian calculation

### [ ] #93 - Appeal history visible
**Status**: NOT STARTED
**Descripción**: Ver historial de appeals en perfil
**Archivos**: `dashboard/src/pages/AppealHistory.tsx` (crear)

## 3.4 Seals System (P2) [Items #94-100]

### [ ] #94 - SealRegistry contract
**Status**: NOT STARTED
**Descripción**: ERC-8004 extension para seals verificables
**Tipos**: SKILL, WORK, BEHAVIOR

### [ ] #95 - SKILL seals
**Status**: NOT STARTED
**Descripción**: Certificaciones de habilidades
**Ejemplo**: "Verificado: Fotografía profesional"

### [ ] #96 - WORK seals
**Status**: NOT STARTED
**Descripción**: Completó X tareas de tipo Y
**Ejemplo**: "100+ deliveries completados"

### [ ] #97 - BEHAVIOR seals
**Status**: NOT STARTED
**Descripción**: Patrones de comportamiento positivo
**Ejemplo**: "Responde en <5 minutos"

### [ ] #98 - Seal display en perfil
**Status**: NOT STARTED
**Descripción**: Mostrar seals ganados
**Archivos**: `dashboard/src/components/SealsBadges.tsx` (crear)

### [ ] #99 - Seal requirements config
**Status**: NOT STARTED
**Descripción**: Definir qué se necesita para cada seal
**Archivos**: `mcp-server/src/seals/requirements.yaml` (crear)

### [ ] #100 - Seal expiration
**Status**: NOT STARTED
**Descripción**: Algunos seals expiran si no hay actividad
**Notas**: SKILL seals expiran en 1 año sin uso

---

# FASE 4: VERIFICACIÓN AVANZADA
> **Objetivo**: Hardware attestation, AI review avanzado, arbitration
> **Timeline**: Semana 13-16

## 4.1 Hardware Attestation (P1) [Items #101-108]

### [ ] #101 - Secure Enclave photo signing (iOS)
**Status**: NOT STARTED
**Descripción**: Fotos firmadas con chip de seguridad del iPhone
**API**: Secure Enclave via CryptoKit
**Docs**: https://developer.apple.com/documentation/security/certificate_key_and_trust_services/keys/protecting_keys_with_the_secure_enclave
**Flow**:
1. Generate key pair in Secure Enclave (never leaves device)
2. Sign photo hash + GPS + timestamp
3. Include signature in evidence submission
4. Backend verifies signature against known public key

### [ ] #102 - StrongBox attestation (Android)
**Status**: NOT STARTED
**Descripción**: Equivalent Android usando StrongBox/TEE
**API**: Android Keystore with StrongBox
**Flow**: Similar a iOS pero con Android APIs
**Fallback**: TEE si device no tiene StrongBox

### [ ] #103 - Device attestation API
**Status**: NOT STARTED
**Descripción**: Verificar que device es real, no emulador
**iOS**: App Attest (DeviceCheck framework)
**Android**: Play Integrity API
**Archivos**: `mcp-server/src/verification/device_attestation.py`

### [ ] #104 - Photo metadata preservation
**Status**: NOT STARTED
**Descripción**: No strip EXIF, necesario para verificación
**Notas**: GPS, timestamp, device model en metadata
**Archivos**: Upload flow preserva metadata

### [ ] #105 - Attestation verification backend
**Status**: NOT STARTED
**Descripción**: Verificar firmas de hardware en server
**Archivos**: `mcp-server/src/verification/attestation.py` (crear)
```python
def verify_hardware_attestation(
    photo_hash: bytes,
    signature: bytes,
    public_key: bytes,
    device_attestation: dict
) -> AttestationResult:
    # 1. Verify device attestation (not emulator)
    # 2. Verify signature matches photo hash
    # 3. Check public key is from known Secure Enclave
    pass
```

### [ ] #106 - Device fingerprinting anti-fraud
**Status**: NOT STARTED
**Descripción**: Detectar si mismo device usado por múltiples workers
**Notas**: Anti-fraud para device farming
**Archivos**: Tabla `device_fingerprints` con hashed identifiers

### [ ] #107 - Attestation requirement por task_type
**Status**: NOT STARTED
**Descripción**: Tareas de alto valor requieren attestation
**Reglas**:
- Tareas >$50 → hardware attestation required
- Tareas >$20 → recommended, +5% bounty bonus
- Tareas <$20 → optional

### [ ] #108 - Attestation fallback options
**Status**: NOT STARTED
**Descripción**: Qué hacer si device no soporta attestation
**Options**:
- Lower verification tier (AI review obligatorio)
- Limite a tareas de bajo valor
- KYC alternative

## 4.2 AI Review Avanzado (P2) [Items #109-116]

### [ ] #109 - Multi-model verification
**Status**: NOT STARTED
**Descripción**: Claude + GPT-4V para consensus
**Notas**: Ambos deben aprobar para auto-approve

### [ ] #110 - Specialized prompts por task_type
**Status**: NOT STARTED
**Descripción**: Prompts optimizados para cada tipo de tarea
**Archivos**: `mcp-server/src/verification/prompts/` (crear directorio)

### [ ] #111 - Confidence calibration
**Status**: NOT STARTED
**Descripción**: Calibrar thresholds basado en datos reales
**Notas**: A/B testing de confidence levels

### [ ] #112 - Verification explanation
**Status**: NOT STARTED
**Descripción**: AI explica por qué aprobó/rechazó
**Notas**: Útil para disputas y aprendizaje

### [ ] #113 - Feedback loop training
**Status**: NOT STARTED
**Descripción**: Usar disputas resueltas para mejorar AI
**Notas**: Fine-tuning eventual o prompt improvement

### [ ] #114 - OCR for text verification
**Status**: NOT STARTED
**Descripción**: Leer texto en fotos (recibos, documentos)
**Archivos**: `mcp-server/src/verification/ocr.py` (crear)

### [ ] #115 - Video frame analysis
**Status**: NOT STARTED
**Descripción**: Verificar videos extrayendo frames clave
**Notas**: Para tareas que requieren video evidence

### [ ] #116 - Audio verification
**Status**: NOT STARTED
**Descripción**: Transcribir y verificar audio evidence
**Dependencias**: Whisper o AbraCadabra integration

## 4.3 Safe Pool Arbitration (P2) [Items #117-124]

### [ ] #117 - Persistent Safe Pool setup
**Status**: NOT STARTED
**Descripción**: Gnosis Safe con 3+ validators permanentes
**Notas**: 2-of-3 threshold para decisiones

### [ ] #118 - Validator selection criteria
**Status**: NOT STARTED
**Descripción**: Quién puede ser validator
**Requisitos**: >100 tareas verificadas, rating >4.5, staked

### [ ] #119 - Validator staking
**Status**: NOT STARTED
**Descripción**: Validators deben stakear para participar
**Notas**: Stake perdido si decisiones revertidas frecuentemente

### [ ] #120 - Dispute routing to Safe Pool
**Status**: NOT STARTED
**Descripción**: Auto-route disputas Tier 4 al Safe
**Archivos**: `mcp-server/src/disputes/router.py` (crear)

### [ ] #121 - Validator voting interface
**Status**: NOT STARTED
**Descripción**: UI para validators revisar y votar
**Archivos**: `dashboard/src/pages/ValidatorDashboard.tsx` (crear)

### [ ] #122 - Vote deadline enforcement
**Status**: NOT STARTED
**Descripción**: Si validators no votan en X horas, default
**Notas**: Default a favor de worker si no hay quorum

### [ ] #123 - Validator compensation
**Status**: NOT STARTED
**Descripción**: Pago a validators por disputas resueltas
**Notas**: % del dispute amount como fee

### [ ] #124 - Appeal process
**Status**: NOT STARTED
**Descripción**: Apelar decisión del Safe Pool
**Notas**: Requiere más stake, revisión por más validators

## 4.4 ChainWitness Integration (P2) [Items #125-130]

### [ ] #125 - Evidence notarization
**Status**: NOT STARTED
**Descripción**: Hash de evidence guardado en ChainWitness
**Archivos**: `mcp-server/src/integrations/chainwitness/notarize.py` (crear)

### [ ] #126 - Timestamp proof
**Status**: NOT STARTED
**Descripción**: Probar que evidence existía en momento X
**Notas**: Útil para disputas sobre timing

### [ ] #127 - Evidence retrieval
**Status**: NOT STARTED
**Descripción**: Recuperar evidence original dado hash
**Archivos**: `mcp-server/src/integrations/chainwitness/retrieve.py`

### [ ] #128 - Verification result notarization
**Status**: NOT STARTED
**Descripción**: Resultado de verificación también en chain
**Notas**: Auditable, inmutable

### [ ] #129 - ChainWitness for disputes
**Status**: NOT STARTED
**Descripción**: Todas las pruebas de disputa notarizadas
**Notas**: Evita manipulación de evidencia

### [ ] #130 - Batch notarization
**Status**: NOT STARTED
**Descripción**: Notarizar múltiples evidences en una tx
**Notas**: Ahorra gas

---

# FASE 5: WORKER PROTECTION (NUEVO DE GROK)
> **Objetivo**: Mecanismos para proteger workers de abusos
> **Timeline**: Semana 9-12 (en paralelo con Fase 3)

## 5.1 Worker Protection Fund (P1 - GROK SOLUTION) [Items #131-136]

### [ ] #131 - Protection fund pool setup
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Pool que cubre workers en casos de unfair rejection
**Funding sources**:
- 0.5% de cada task fee
- 100% de agent bonds slashed
- Voluntary agent contributions
**Archivos**:
- Tabla `protection_fund` con balance y transactions
- `mcp-server/src/protection/fund.py` (crear)

### [ ] #132 - Fund claim process
**Status**: NOT STARTED
**Descripción**: Worker puede reclamar del fund post-arbitration
**Flow**:
1. Worker gana arbitration vs agent
2. Agent no paga (wallet vacía, desaparecido)
3. Worker claim al protection fund
4. Fund paga hasta 100% de bounty
**Limits**: Max $50/claim, $200/month/worker

### [ ] #133 - Fund balance monitoring
**Status**: NOT STARTED
**Descripción**: Dashboard de health del fund
**Archivos**: `dashboard/src/pages/ProtectionFund.tsx` (crear)
**Metrics**: Total balance, claims paid, burn rate, runway

### [ ] #134 - Auto-pause high-risk agents
**Status**: NOT STARTED
**Descripción**: Si fund is stressed, pause agents con high rejection rate
**Threshold**: >30% rejection rate + fund <$1000 → agent paused

### [ ] #135 - Fund governance
**Status**: NOT STARTED
**Descripción**: DAO votes on fund parameters
**Parameters**: Contribution %, max claims, pause thresholds

### [ ] #136 - Fund audit trail
**Status**: NOT STARTED
**Descripción**: Public log de todas las transacciones del fund
**Archivos**: Tabla `fund_transactions` con tipo, amount, reason

## 5.2 Min Net Payout Floor (P1 - GROK SOLUTION) [Items #137-140]

### [ ] #137 - Minimum payout configuration
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Garantizar mínimo neto post-fees por tarea
**Default**: $0.50 minimum net payout
**Formula**: `min_net = bounty - (bounty * fee_percent) >= $0.50`
**Archivos**: Config `min_net_payout_usd: decimal` en settings

### [ ] #138 - Task rejection if below minimum
**Status**: NOT STARTED
**Descripción**: Rechazar tasks que no cumplan minimum net
**Flow**: Al crear task, validar que net payout >= min
**UI**: Mostrar warning si bounty es muy bajo

### [ ] #139 - Minimum payout by task_type
**Status**: NOT STARTED
**Descripción**: Diferentes mínimos por tipo
**Ejemplos**:
- simple_action: $0.50
- physical_presence: $1.00
- digital_physical: $2.00
- human_authority: $5.00

### [ ] #140 - Minimum payout transparency
**Status**: NOT STARTED
**Descripción**: Worker siempre ve net payout antes de aceptar
**Archivos**: `dashboard/src/components/NetPayoutBadge.tsx` (crear)

## 5.3 Regional Payout Scaling (P2 - GROK SOLUTION) [Items #141-145]

### [ ] #141 - Cost-of-living oracle
**Status**: NOT STARTED
**Descripción**: Data source para ajustar pagos por región
**Sources**: Numbeo API, World Bank data
**Archivos**: `mcp-server/src/pricing/col_oracle.py` (crear)

### [ ] #142 - Regional multiplier calculation
**Status**: NOT STARTED
**Descripción**: Ajustar bounty sugerido por región
**Formula**: `adjusted_bounty = base_bounty * regional_multiplier`
**Ejemplos**:
- Miami: 1.3x (high cost)
- Bogotá: 0.8x (lower cost)
- Lagos: 0.6x (lowest cost)
**Notas**: Solo afecta UI suggestions, no hard limits

### [ ] #143 - Regional minimum wage floor
**Status**: NOT STARTED
**Descripción**: Implied hourly no puede ser menor que min wage local
**Flow**:
1. Agent crea task con time estimate
2. System calcula implied hourly rate
3. Si < local min wage, warning (not blocking)
**Archivos**: Tabla `regional_min_wages` con country/amount

### [ ] #144 - Regional analytics dashboard
**Status**: NOT STARTED
**Descripción**: Ver earnings y task stats por región
**Archivos**: `dashboard/src/pages/RegionalStats.tsx` (crear)

### [ ] #145 - Worker region verification
**Status**: NOT STARTED
**Descripción**: Verificar que worker está donde dice
**Methods**: IP geolocation, GPS en app, optional KYC

## 5.4 Task Bundling (P2 - GROK SOLUTION) [Items #146-150]

### [ ] #146 - Task bundle creation
**Status**: NOT STARTED
**Descripción**: Agents pueden crear bundles de 5-10 similar tasks
**Schema**:
```json
{
  "bundle_id": "uuid",
  "tasks": ["task_1", "task_2", ...],
  "zone": {"lat": ..., "lng": ..., "radius_km": 5},
  "total_bounty": 15.00,
  "per_task_min": 1.50
}
```
**Archivos**: Tabla `task_bundles` en migrations

### [ ] #147 - Bundle matching priority
**Status**: NOT STARTED
**Descripción**: Workers que toman bundles tienen prioridad
**Razón**: Consistent flow, reduce feast/famine
**Archivos**: `mcp-server/src/matching/bundles.py` (crear)

### [ ] #148 - Bundle completion bonus
**Status**: NOT STARTED
**Descripción**: Bonus por completar bundle entero
**Example**: 10 tasks × $1.50 = $15 + 10% bonus = $16.50
**Archivos**: Columna `bundle_bonus_percent` en bundles

### [ ] #149 - Bundle analytics
**Status**: NOT STARTED
**Descripción**: Track bundle completion rates
**Metrics**: % completed, avg time, worker satisfaction

### [ ] #150 - Bundle suggestions for agents
**Status**: NOT STARTED
**Descripción**: AI suggests bundling similar tasks
**Archivos**: `mcp-server/src/matching/bundle_suggest.py` (crear)

---

# FASE 6: ESCALA
> **Objetivo**: Enterprise, multi-chain, robot executors
> **Timeline**: Semana 17+

## 6.1 Enterprise Configuration (P2) [Items #151-160]

### [ ] #151 - Enterprise onboarding flow
**Status**: NOT STARTED
**Descripción**: Self-service signup para empresas
**Archivos**: `dashboard/src/pages/Enterprise.tsx` (crear)

### [ ] #152 - Custom branding
**Status**: NOT STARTED
**Descripción**: Logo, colores, dominio custom
**Notas**: White-label option

### [ ] #153 - SSO integration
**Status**: NOT STARTED
**Descripción**: Login con Google/Azure AD empresarial
**Dependencias**: Auth0 o similar

### [ ] #154 - Role-based access
**Status**: NOT STARTED
**Descripción**: Admin, manager, viewer roles
**Archivos**: Tabla `enterprise_roles` en migrations

### [ ] #155 - Budget management
**Status**: NOT STARTED
**Descripción**: Límites de gasto por equipo/proyecto
**Archivos**: `dashboard/src/components/BudgetManager.tsx` (crear)

### [ ] #156 - Approval workflows
**Status**: NOT STARTED
**Descripción**: Tareas >$X requieren aprobación de manager
**Archivos**: Tabla `approval_queue` en migrations

### [ ] #157 - Bulk task creation
**Status**: NOT STARTED
**Descripción**: Upload CSV con 1000+ tareas
**Archivos**: `dashboard/src/components/BulkUpload.tsx` (crear)

### [ ] #158 - API rate limits
**Status**: NOT STARTED
**Descripción**: Tiers de API access
**Notas**: Free: 100/day, Pro: 10k/day, Enterprise: unlimited

### [ ] #159 - SLA configuration
**Status**: NOT STARTED
**Descripción**: Garantías de respuesta y resolución
**Notas**: 99.9% uptime, <4hr response

### [ ] #160 - Dedicated support
**Status**: NOT STARTED
**Descripción**: Slack channel, priority support
**Notas**: Enterprise-only

## 6.2 Flexible Rewards (P2) [Items #161-166]

### [ ] #161 - Points-based rewards
**Status**: NOT STARTED
**Descripción**: Algunas tareas dan puntos, no dinero
**Notas**: Para gamification, loyalty programs

### [ ] #162 - Custom token rewards
**Status**: NOT STARTED
**Descripción**: Pagar en token del enterprise
**Notas**: Requiere whitelisting del token

### [ ] #163 - NFT rewards
**Status**: NOT STARTED
**Descripción**: Mint NFT como reward
**Notas**: Coleccionables, badges

### [ ] #164 - Experience points
**Status**: NOT STARTED
**Descripción**: XP que suma a niveles
**Notas**: Gamification layer

### [ ] #165 - Reward marketplace
**Status**: NOT STARTED
**Descripción**: Canjear puntos por items
**Archivos**: `dashboard/src/pages/Marketplace.tsx` (crear)

### [ ] #166 - Hybrid rewards
**Status**: NOT STARTED
**Descripción**: $5 + 100 XP + Badge por tarea
**Notas**: Combinaciones flexibles

## 6.3 Multi-Chain (P2) [Items #167-173]

### [ ] #167 - Base mainnet deployment
**Status**: NOT STARTED
**Descripción**: Deploy contracts en Base
**Archivos**: `contracts/deploy/base.ts` (crear)

### [ ] #168 - Ethereum mainnet (high value)
**Status**: NOT STARTED
**Descripción**: Para tareas enterprise >$1000
**Notas**: Más seguro, más caro

### [ ] #169 - Polygon for volume
**Status**: NOT STARTED
**Descripción**: Tareas de bajo valor, alto volumen
**Notas**: Gas casi gratis

### [ ] #170 - Arbitrum option
**Status**: NOT STARTED
**Descripción**: Alternativa L2 popular
**Notas**: Bridge automático si worker prefiere

### [ ] #171 - Chain selector en dashboard
**Status**: NOT STARTED
**Descripción**: Agent elige chain al crear tarea
**Archivos**: `dashboard/src/components/ChainSelector.tsx` (crear)

### [ ] #172 - Cross-chain reputation
**Status**: NOT STARTED
**Descripción**: Reputation portable entre chains
**Notas**: ERC-8004 sync

### [ ] #173 - Gas estimation por chain
**Status**: NOT STARTED
**Descripción**: Mostrar costo estimado de gas
**Archivos**: `mcp-server/src/utils/gas_estimator.py` (crear)

## 6.4 Robot Executors (P3) [Items #174-185]

### [ ] #174 - Robot Worker Registry
**Status**: NOT STARTED
**Descripción**: ERC-8004 extension para robots
**Schema**: robot_id, owner, capabilities, location

### [ ] #175 - Robot capability declaration
**Status**: NOT STARTED
**Descripción**: Qué puede hacer cada robot
**Ejemplo**: ["delivery", "photography", "inspection"]

### [ ] #176 - Robot task matching
**Status**: NOT STARTED
**Descripción**: Match tareas con robots capaces
**Archivos**: `mcp-server/src/matching/robot.py` (crear)

### [ ] #177 - Robot verification protocol
**Status**: NOT STARTED
**Descripción**: Cómo verificar trabajo de robot
**Notas**: Sensors, cameras, GPS tracking

### [ ] #178 - Robot operator dashboard
**Status**: NOT STARTED
**Descripción**: UI para dueños de robots
**Archivos**: `dashboard/src/pages/RobotOperator.tsx` (crear)

### [ ] #179 - Robot maintenance scheduling
**Status**: NOT STARTED
**Descripción**: Auto-disable robot para mantenimiento
**Notas**: Basado en horas de operación

### [ ] #180 - Robot insurance requirement
**Status**: NOT STARTED
**Descripción**: Robots deben tener seguro activo
**Notas**: Verificación periódica

### [ ] #181 - Robot farming economics
**Status**: NOT STARTED
**Descripción**: Modelo económico para robot farms
**Notas**: $20-30K hardware, 3-10 month ROI
**Métricas**: tasks/day, revenue/task, maintenance costs

### [ ] #182 - Robot-human handoff
**Status**: NOT STARTED
**Descripción**: Robot inicia, humano completa
**Ejemplo**: Robot lleva paquete, humano firma

### [ ] #183 - Robot telemetry storage
**Status**: NOT STARTED
**Descripción**: Guardar logs de operación
**Archivos**: Tabla `robot_telemetry` en migrations

### [ ] #184 - Robot fleet management
**Status**: NOT STARTED
**Descripción**: Gestionar múltiples robots
**Archivos**: `dashboard/src/pages/FleetManager.tsx` (crear)

### [ ] #185 - Robot failure handling
**Status**: NOT STARTED
**Descripción**: Qué pasa si robot falla mid-task
**Notas**: Auto-reassign a humano, partial payment

## 6.5 Describe.net Integration (P2) [Items #186-190]

### [ ] #186 - Describe.net connector
**Status**: NOT STARTED
**Descripción**: Publicar tareas en Describe.net marketplace
**Archivos**: `mcp-server/src/integrations/describe/connector.py` (crear)

### [ ] #187 - Bidirectional sync
**Status**: NOT STARTED
**Descripción**: Tareas y submissions sync en ambas direcciones
**Notas**: Describe workers pueden ver Execution Market tasks

### [ ] #188 - Describe reputation import
**Status**: NOT STARTED
**Descripción**: Importar reputation de Describe
**Notas**: Mapping a ERC-8004 score

### [ ] #189 - Unified worker pool
**Status**: NOT STARTED
**Descripción**: Workers de ambas plataformas en un pool
**Notas**: Más cobertura geográfica

### [ ] #190 - Revenue share model
**Status**: NOT STARTED
**Descripción**: Split de fees con Describe
**Notas**: 50/50 o basado en origin de task

---

# FASE 7: WORKER EMPOWERMENT (NUEVO DE GROK)
> **Objetivo**: Dar poder colectivo a workers
> **Timeline**: Semana 13+

## 7.1 Worker Guilds/DAOs (P2 - GROK SOLUTION) [Items #191-197]

### [ ] #191 - Guild creation
**Status**: NOT STARTED
**Descripción**: Workers pueden formar guilds (DAOs)
**Requirements**: Min 5 workers, combined Bayesian score >60
**Archivos**:
- Tabla `worker_guilds` con members, rules
- `mcp-server/src/guilds/create.py` (crear)

### [ ] #192 - Guild membership management
**Status**: NOT STARTED
**Descripción**: Invite, accept, remove members
**Archivos**: `dashboard/src/pages/GuildManagement.tsx` (crear)

### [ ] #193 - Collective agent blacklist
**Status**: NOT STARTED
**Descripción**: Guild votes to blacklist abusive agents
**Flow**:
1. Member proposes blacklist
2. 2/3 majority votes yes
3. Agent blacklisted for all guild members
**Effect**: Guild members won't see/accept tasks from blacklisted agents

### [ ] #194 - Guild minimum bounty negotiation
**Status**: NOT STARTED
**Descripción**: Guild sets min bounty for its members
**Example**: "Miami Verifiers Guild" requires min $2/task in Miami
**Notas**: Solo aplicable a guild members, not protocol-wide

### [ ] #195 - Guild reputation boost
**Status**: NOT STARTED
**Descripción**: Guild membership visible, adds trust
**Display**: "Member of Miami Verifiers Guild (4.8★)"

### [ ] #196 - Guild treasury
**Status**: NOT STARTED
**Descripción**: Shared fund for guild expenses
**Funding**: Optional % of member earnings
**Uses**: Legal support, tools, training

### [ ] #197 - Guild governance tokens
**Status**: NOT STARTED
**Descripción**: Voting power based on contribution
**Formula**: votes = sqrt(total_earnings_in_guild)
**Archivos**: Gnosis Safe or custom DAO contract

## 7.2 Worker Governance Rights (P2 - GROK SOLUTION) [Items #198-203]

### [ ] #198 - Protocol governance participation
**Status**: NOT STARTED
**Descripción**: Top workers vote on protocol changes
**Requirements**: Bayesian score >70, >50 tasks completed
**Archivos**: Governance token allocation

### [ ] #199 - Fee structure voting
**Status**: NOT STARTED
**Descripción**: Workers vote on platform fee changes
**Threshold**: 2/3 majority of eligible workers

### [ ] #200 - Minimum payout voting
**Status**: NOT STARTED
**Descripción**: Workers vote on min payout changes
**Notas**: Prevents race to bottom

### [ ] #201 - Dispute resolution rule changes
**Status**: NOT STARTED
**Descripción**: Workers vote on arbitration rules
**Examples**: Timeout durations, default outcomes

### [ ] #202 - Worker representative council
**Status**: NOT STARTED
**Descripción**: Elected workers represent in major decisions
**Term**: 6 months
**Selection**: Top 10 by Bayesian score who opt-in

### [ ] #203 - Worker feedback channel
**Status**: NOT STARTED
**Descripción**: Formal channel for worker input
**Archivos**: `dashboard/src/pages/WorkerFeedback.tsx` (crear)

---

# ITEMS ADICIONALES

## Agent-Worker Trust (P2) [Items #204-209]

### [ ] #204 - Agent staking/insurance
**Status**: NOT STARTED
**Descripción**: Agents deben stakear para proteger workers
**Notas**: Stake se usa si agent no paga

### [ ] #205 - Payment guarantee badge
**Status**: NOT STARTED
**Descripción**: Badge para agents con 100% payment rate
**Notas**: Visible en todas sus tareas

### [ ] #206 - Escrow auto-release timer
**Status**: NOT STARTED
**Descripción**: Si agent no revisa en 48hr, auto-approve
**Notas**: Protege worker de agents lentos

### [ ] #207 - Agent verification tiers
**Status**: NOT STARTED
**Descripción**: Verified, Pro, Enterprise agent levels
**Notas**: Más verificación = más trust

### [ ] #208 - Agent task history public
**Status**: NOT STARTED
**Descripción**: Workers ven historial de tareas del agent
**Notas**: Transparencia total

### [ ] #209 - Hybrid human-robot mandates (GROK)
**Status**: NOT STARTED
**Descripción**: 20-40% of tasks require human oversight
**Razón**: Prevents full robot takeover, keeps humans relevant
**Implementation**: Protocol flag `requires_human: boolean`

## Platform Competition (P3) [Items #210-216]

### [ ] #210 - Fee comparison calculator
**Status**: NOT STARTED
**Descripción**: Mostrar ahorro vs MTurk, TaskRabbit
**Notas**: 6-8% vs 20-23%

### [ ] #211 - Migration wizard from MTurk
**Status**: NOT STARTED
**Descripción**: Importar workers y tasks de MTurk
**Archivos**: `dashboard/src/pages/MigrationWizard.tsx` (crear)

### [ ] #212 - TaskRabbit skill mapping
**Status**: NOT STARTED
**Descripción**: Mapear categorías de TaskRabbit a Execution Market
**Notas**: Auto-suggest task_type

### [ ] #213 - Price benchmarking
**Status**: NOT STARTED
**Descripción**: Sugerir precio basado en competencia
**Notas**: "Tareas similares pagan $X"

### [ ] #214 - Success rate comparison
**Status**: NOT STARTED
**Descripción**: Mostrar completion rate vs competitors
**Notas**: "90% vs industry 65%"

### [ ] #215 - Speed comparison
**Status**: NOT STARTED
**Descripción**: Time-to-completion vs competitors
**Notas**: "2hr avg vs 12hr industry"

### [ ] #216 - Quality comparison
**Status**: NOT STARTED
**Descripción**: Dispute rate vs competitors
**Notas**: "3% disputes vs 15% industry"

## Advanced Analytics (P3) [Items #217-221]

### [ ] #217 - Task success predictor
**Status**: NOT STARTED
**Descripción**: ML model predice si task será completada
**Notas**: Basado en precio, location, time, etc.

### [ ] #218 - Optimal pricing suggester
**Status**: NOT STARTED
**Descripción**: Sugerir precio para maximizar completion
**Notas**: "Aumentar $2 sube completion 40%"

### [ ] #219 - Worker availability forecast
**Status**: NOT STARTED
**Descripción**: Predecir disponibilidad por zona/hora
**Notas**: "Mejor momento: 2-4pm"

### [ ] #220 - Fraud detection ML
**Status**: NOT STARTED
**Descripción**: Detectar patrones de fraude automáticamente
**Notas**: GPS spoofing, photo recycling, collusion

### [ ] #221 - Platform health metrics
**Status**: NOT STARTED
**Descripción**: Dashboard de métricas globales
**Notas**: GMV, active workers, task completion rate

---

# FASE 8: BOOTSTRAP & ADOPTION (NUEVO DE GROK)
> **Objetivo**: Resolver chicken-egg problem y establecer posicionamiento correcto
> **Timeline**: Paralelo con Fase 0-1

## 8.1 Chicken-Egg Solution (P0 - GROK SOLUTION) [Items #222-228]

### [ ] #222 - POAP/Crypto community bootstrap
**Status**: NOT STARTED
**Prioridad**: P0
**Descripción**: Usar POAP hunters y comunidades crypto como early adopters
**Razón**: Ya caminan por recompensas digitales (STEPN, Pokémon GO) → caminarán por dólares
**Archivos**: Marketing plan + partnership outreach
**Target communities**:
- POAP collectors
- STEPN/move-to-earn users
- Local crypto meetups (Medellín, Miami, Lagos)
- Telegram crypto groups

### [ ] #223 - Initial task injection by DAO
**Status**: NOT STARTED
**Prioridad**: P0
**Descripción**: Ultravioleta DAO publica tareas iniciales para garantizar volumen
**Budget**: Reserve $1,000-$5,000 for first month
**Task types**: Store verifications, price checks, sign photos
**Archivos**: `marketing/bootstrap_tasks.csv` (crear)

### [ ] #224 - Enterprise overflow to public pool
**Status**: NOT STARTED
**Descripción**: Enterprise clients pueden overflow sus tareas al pool público
**Beneficio**: Workers públicos se benefician del volumen enterprise
**Archivos**: Toggle en enterprise config

### [ ] #225 - Referral system for workers
**Status**: NOT STARTED
**Descripción**: Workers ganan bonus por referir nuevos workers
**Bonus**: $1-2 per referral que completa 5 tareas
**Archivos**: `mcp-server/src/referral/` (crear)

### [ ] #226 - Agent dev kit gratuito
**Status**: NOT STARTED
**Descripción**: Tools/templates gratis para integración MCP
**Archivos**: `sdk/agent-starter-kit/` (crear)
**Incluye**: Code templates, example integrations, docs

### [ ] #227 - Pilot programs con empresas
**Status**: NOT STARTED
**Descripción**: Programas piloto con logistics/retail firms
**Targets**: Empresas de delivery, verificación de inventario, market research
**Beneficio**: Volumen garantizado para bootstrap

### [ ] #228 - Miami/LATAM hub focus
**Status**: NOT STARTED
**Descripción**: Lanzamiento concentrado en hubs específicos
**Locations**: Miami (high-value), Medellín/Bogotá (arbitrage), Lagos (emerging)
**Razón**: Densidad > cobertura global inicial

## 8.2 Explicit Positioning (P1 - GROK SOLUTION) [Items #229-232]

### [ ] #229 - Side-hustle framing en docs
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Documentar explícitamente que Execution Market NO es:
- Reemplazo de trabajo full-time
- Ingreso principal
- Solución permanente al desempleo
**ES**:
- Extra income opcional ($5-15/día)
- Flexible (cuando quieras)
- Puente temporal durante disrupción AI (2-5 años)
**Archivos**: Landing page copy, onboarding flow, FAQ

### [ ] #230 - Transition messaging
**Status**: NOT STARTED
**Descripción**: Comunicar honestamente la transición robot
**Message**: "Humanos hoy → Hybrids mañana → Robots después, pero humanos siempre en niches de valor alto"
**Archivos**: Long-term vision docs, blog posts

### [ ] #231 - Income expectation calculator
**Status**: NOT STARTED
**Descripción**: Tool que muestra income realista por región/hora
**Archivos**: `dashboard/src/components/IncomeEstimator.tsx` (crear)
**Inputs**: Location, hours available, task types willing to do
**Output**: "$X-Y per week estimated" con disclaimer

### [ ] #232 - Comparison vs competitors
**Status**: NOT STARTED
**Descripción**: Table clara mostrando diferencias vs MTurk, TaskRabbit, Fiverr
**Metrics**: Fees, payout speed, minimums, verification fairness
**Archivos**: Landing page section

## 8.3 Worker Staking for High-Value (P2 - GROK SOLUTION) [Items #233-237]

### [ ] #233 - Worker stake requirement for high-value tasks
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Para tareas >$50, workers deben stakear para ser elegibles
**Formula**: `stake_required = bounty * 0.10-0.20`
**Razón**: Skin in the game, reduce theft risk
**Archivos**:
- Columna `requires_worker_stake: boolean` en tasks
- `mcp-server/src/staking/worker_stake.py` (crear)

### [ ] #234 - Worker stake lock/release flow
**Status**: NOT STARTED
**Descripción**: Stake se bloquea al aceptar, se libera al completar + approve
**Slashing**: Si worker roba o fraude comprobado, pierde stake
**Archivos**: `mcp-server/src/staking/lock_release.py`

### [ ] #235 - Stake-based task filtering
**Status**: NOT STARTED
**Descripción**: Workers con stake disponible ven tareas de alto valor
**UI**: Indicator de tareas "premium" que requieren stake
**Archivos**: Filter en task matching

### [ ] #236 - Reputation equivalence for stake
**Status**: NOT STARTED
**Descripción**: Workers con Bayesian score >80 pueden usar rep en lugar de stake
**Razón**: Trust ganado con historial = skin in the game
**Archivos**: Config `rep_threshold_for_stake_waiver: 80`

### [ ] #237 - Stake pool dashboard
**Status**: NOT STARTED
**Descripción**: Workers ven su stake disponible, locked, y slashing history
**Archivos**: `dashboard/src/pages/MyStake.tsx` (crear)

## 8.4 Fraud Mitigation Advanced (P1 - GEMINI CRITIQUE) [Items #238-244]

### [ ] #238 - GPS spoofing detection
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Detectar GPS spoofing más allá de hardware attestation
**Methods**:
- Network triangulation cross-check
- Movement pattern analysis (realistic walking speed)
- Historical location consistency
- Multiple sensors fusion (WiFi, cell towers)
**Archivos**: `mcp-server/src/verification/gps_antispoofing.py` (crear)

### [ ] #239 - GenAI photo detection
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Detectar fotos generadas por IA (Midjourney, Flux, DALL-E)
**Methods**:
- AI-generated content detection models
- Metadata analysis (EXIF consistency)
- Noise pattern analysis
- Compression artifact detection
**Archivos**: `mcp-server/src/verification/genai_detector.py` (crear)
**Dependencies**: OpenAI CLIP, custom classifier

### [ ] #240 - Goods liability insurance pool
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Pool separado del Worker Protection Fund para robo de bienes
**Funding**: 0.5% extra fee en tasks de delivery/pickup
**Coverage**: Hasta $500 por claim (valor del bien, no el bounty)
**Archivos**: Tabla `goods_insurance_pool`
**Diferencia vs Worker Protection Fund**: WPF protege a workers de unfair rejection. Goods Insurance protege a agents de robo real.

### [ ] #241 - Cognitive cost micro-bonuses
**Status**: NOT STARTED
**Descripción**: Bonuses automáticos por esfuerzo real
**Bonuses**:
- +$0.15 si travel >100m
- +$0.10 por task completada >500m de home location
- +$0.05 por bad weather (rain API)
**Archivos**: `mcp-server/src/pricing/effort_bonus.py` (crear)
**Data sources**: GPS distance, weather API

### [ ] #242 - Safety pre-investigation
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: AI evalúa riesgo de location antes de publicar task
**Checks**:
- Crime data by zone (public APIs)
- Time of day risk adjustment
- Private property indicators
- Reviews from past workers en esa zona
**Output**: Safety score 1-5, warning to worker
**Archivos**: `mcp-server/src/safety/pre_check.py` (crear)

### [ ] #243 - Hostile meatspace protocol
**Status**: NOT STARTED
**Descripción**: Procedimientos para lugares peligrosos/privados
**Protocol**:
1. Worker ve safety score antes de aceptar
2. Si guard/obstacle, Proof of Attempt paga base fee
3. Worker puede reportar location issues → affects future tasks
4. Severe safety report → automatic task deactivation
**Archivos**: `mcp-server/src/safety/hostile_protocol.py`

### [ ] #244 - Waiver acknowledgment on-chain
**Status**: NOT STARTED
**Descripción**: Worker firma waiver digital aceptando riesgos
**Notas**: Similar a términos de Amazon Flex
**Archivos**: Smart contract for waiver, UI checkbox
**Legal**: Worker acepta responsabilidad por riesgos físicos

## 8.5 Discovery/Auction Pricing (P2 - GROK SOLUTION) [Items #245-248]

### [ ] #245 - Time-based price discovery mechanism
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Bounty sube automáticamente si nadie toma la tarea
**Mechanism**:
```python
initial_bounty = $2
escalation_interval = 10  # minutes
escalation_percent = 0.15  # +15% cada intervalo
max_bounty = initial_bounty * 3

# En Bogotá: task taken at $2
# En SF: task taken at $5 after 20 min
```
**Razón**: El protocolo descubre el precio real del trabajo humano en tiempo real
**Archivos**: `mcp-server/src/pricing/discovery.py` (crear)

### [ ] #246 - Bid/offer system opcional
**Status**: NOT STARTED
**Descripción**: Workers pueden ofertar menos que el bounty actual
**Flow**: Agent ve ofertas, puede aceptar menor precio
**Razón**: Competencia sana baja precios donde hay densidad
**Archivos**: Tabla `task_bids`

### [ ] #247 - Price analytics por zona
**Status**: NOT STARTED
**Descripción**: Dashboard mostrando precios promedio por task type y zona
**Metrics**: Median time to accept, final price vs initial, regional differentials
**Archivos**: `dashboard/src/pages/PriceAnalytics.tsx` (crear)

### [ ] #248 - Agent price recommendations
**Status**: NOT STARTED
**Descripción**: AI sugiere precio inicial basado en histórico
**Message**: "Similar tasks in Miami taken at $X within Y minutes"
**Archivos**: `mcp-server/src/pricing/recommendations.py`

## 8.6 Dashboard Missing Components (P1) [Items #249-255]

### [ ] #249 - User profile page
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Página de perfil con datos del executor
**Incluye**: Bayesian score, task history, earnings, seals, settings
**Archivos**: `dashboard/src/pages/Profile.tsx` (crear)

### [ ] #250 - Push notifications integration
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Notificaciones push para nuevas tareas cerca
**Methods**: Firebase Cloud Messaging, OneSignal
**Archivos**: `dashboard/src/lib/notifications.ts` (crear)

### [ ] #251 - Location-based task filtering
**Status**: NOT STARTED
**Descripción**: Filtrar tareas por distancia actual del worker
**UI**: Slider "Show tasks within X km"
**Archivos**: `dashboard/src/components/LocationFilter.tsx` (crear)

### [ ] #252 - Dispute resolution UI
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Interface para ver y participar en disputas
**Features**: Evidence viewer, timeline, voting (for validators), appeal button
**Archivos**: `dashboard/src/pages/Disputes.tsx` (crear)

### [ ] #253 - Payment verification UI
**Status**: NOT STARTED
**Descripción**: Ver estado de pagos, tx hashes, escrow status
**Features**: Payment timeline, escrow breakdown, partial vs final
**Archivos**: `dashboard/src/components/PaymentStatus.tsx` (crear)

### [ ] #254 - Agent dashboard (separate view)
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Dashboard para agents (no workers) - ver sus tasks publicadas
**Features**: Task management, submission review, analytics
**Archivos**: `dashboard/src/pages/AgentDashboard.tsx` (crear)

### [ ] #255 - Admin/validator dashboard
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Dashboard para arbitrators y admins
**Features**: Queue de disputas, voting interface, stats
**Archivos**: `dashboard/src/pages/ValidatorPanel.tsx` (crear)

## 8.7 Hybrid Human-Robot Details (P2 - GROK SOLUTION) [Items #256-260]

### [ ] #256 - Human oversight mandate percentage
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: 20-40% de tasks físicas requieren human oversight
**Razón**: Prevents full robot takeover, keeps humans relevant
**Config**: `hybrid_human_percent: 0.30` (protocol-level)
**Archivos**: Task creation validation

### [ ] #257 - Human-robot handoff protocol
**Status**: NOT STARTED
**Descripción**: Robot inicia tarea, humano completa parte crítica
**Example**: Robot transporta paquete → humano firma/entrega → robot documenta
**Archivos**: `mcp-server/src/hybrid/handoff.py` (crear)

### [ ] #258 - Human premium bounty indicator
**Status**: NOT STARTED
**Descripción**: Agents pagan +20-50% por garantizar human executor
**Tag**: `human_required: true` en task
**Razón**: Valor diferencial de humanos vs robots
**Archivos**: UI badge "Human Premium Task"

### [ ] #259 - Robot-to-human escalation
**Status**: NOT STARTED
**Descripción**: Robot encuentra problema → task escala a humano cercano
**Example**: Robot no puede subir escaleras → humano toma over
**Archivos**: `mcp-server/src/hybrid/escalation.py`

### [ ] #260 - Human transition fund
**Status**: NOT STARTED
**Descripción**: 1-2% de robot earnings va a fund para upskilling humanos
**Uses**: Training, robot co-ownership financing, basic income supplement
**Archivos**: Tabla `human_transition_fund`

## 8.8 IRC/A2A Protocol (P1 - GAP ANALYSIS V2) [Items #261-264]

> **FUENTE**: SPEC.md gap analysis - protocolos de comunicación enteramente faltantes

### [ ] #261 - IRC x402-flow handshake protocol
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Protocolo handshake para pagos via IRC
**Flow**:
1. Agent publica task con payment hash
2. Worker claims con signed acceptance
3. x402 payment initiated via IRC channel
4. Confirmation message on completion
**Archivos**: `mcp-server/src/protocols/irc_x402.py` (crear)

### [ ] #262 - IRC channel naming convention
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Convención de nombres para canales IRC
**Format**: `#em-{task_type}-{region}-{timestamp}`
**Example**: `#em-verification-miami-20260125`
**Archivos**: Config en `config/irc.yaml`

### [ ] #263 - A2A MeshRelay connector
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Integration agent-to-agent via MeshRelay
**Features**:
- Task delegation entre agents
- Reputation sharing
- Payment forwarding
**Archivos**: `mcp-server/src/integrations/meshrelay/` (crear)

### [ ] #264 - Webhook notification payloads
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Schema estandarizado para webhooks de eventos
**Events**: task_created, task_assigned, submission_received, payment_completed, dispute_opened
**Format**: JSON con signature para verificación
**Archivos**: `mcp-server/src/webhooks/` (crear)

## 8.9 Fraud Prevention Advanced (P0-P1 - GAP ANALYSIS V2) [Items #265-270]

> **FUENTE**: Gemini V32 analysis - críticas de seguridad no cubiertas

### [ ] #265 - Gallery upload prohibition
**Status**: NOT STARTED
**Prioridad**: P0
**Descripción**: SOLO permitir fotos de cámara live, NO de galería
**Implementación**:
- Mobile: Check metadata para `source: camera`
- Verificar timestamp < 5 minutos
- Rechazar si EXIF indica galería
**Archivos**: `mcp-server/src/verification/checks/photo_source.py` (crear)
**Razón**: Previene reciclaje de fotos viejas

### [ ] #266 - Multi-device detection
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Detectar mismo worker usando múltiples dispositivos simultáneamente
**Methods**:
- Device fingerprinting
- Correlation de GPS patterns
- Session overlap detection
**Archivos**: `mcp-server/src/fraud/multi_device.py` (crear)
**Action**: Warning → Temporary ban si repetido

### [ ] #267 - Photo freshness verification
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Verificar que foto fue tomada HOY y hace máximo 5 minutos
**Checks**:
- EXIF timestamp vs server time
- GPS timestamp consistency
- Metadata coherence
**Config**: `photo_max_age_minutes: 5`
**Archivos**: `mcp-server/src/verification/checks/freshness.py` (crear)

### [ ] #268 - Evidence tampering detection
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Detectar fotos modificadas con software de edición
**Methods**:
- EXIF software tags (Photoshop, GIMP indicators)
- Compression artifact analysis
- Error Level Analysis (ELA)
- Metadata consistency checks
**Archivos**: `mcp-server/src/verification/checks/tampering.py` (crear)

### [ ] #269 - Wash trading detection
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Detectar colusión agent-worker para inflar scores
**Signals**:
- Same IP/device para agent y worker
- Patrones de approval instantáneo
- Bounties muy por encima del mercado
- Reputation reciprocity patterns
**Archivos**: `mcp-server/src/fraud/wash_trading.py` (crear)
**Action**: Freeze accounts + investigation

### [ ] #270 - Rate limits por IP/device
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Límites para prevenir farming masivo
**Limits**:
- Max 50 tasks/día/IP
- Max 20 tasks/día/device
- Max 100 submissions/día/worker
- Cooldown 30 seg entre submissions
**Archivos**: `mcp-server/src/middleware/rate_limits.py` (crear)

## 8.10 Network & Connectivity (P1 - GAP ANALYSIS V2) [Items #271-274]

> **FUENTE**: Gemini V32 - edge cases de conectividad no manejados

### [ ] #271 - Network connectivity handling
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Manejo de desconexión mid-task
**Scenarios**:
- Worker pierde conexión durante upload → retry queue
- Agent offline cuando worker submits → async notification
- Server outage → graceful degradation
**Grace period**: 30 minutos para reconexión
**Archivos**: `mcp-server/src/resilience/connectivity.py` (crear)

### [ ] #272 - Submission timeout handling
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Qué pasa si worker no sube evidence a tiempo
**Flow**:
1. Task asignada → timer inicia
2. Warning al 75% del tiempo
3. Timeout → task vuelve a pool
4. Worker pierde oportunidad (no penalidad primera vez)
**Config**: `submission_timeout_hours: 4` (default)
**Archivos**: `mcp-server/src/jobs/submission_timeout.py` (crear)

### [ ] #273 - Partial completion scenarios
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Tarea 70% completada, ¿cuánto se paga?
**Rules**:
- 0-30%: No pago, task reassigned
- 30-70%: Proof of Attempt applies (10-20%)
- 70-90%: Partial payout prorated
- 90%+: Full review para determinar
**Archivos**: `mcp-server/src/payments/partial_completion.py` (crear)
**UI**: Slider para agent indicar % completado

### [ ] #274 - Photo max age validation
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Rechazar fotos más viejas de 5 minutos
**Implementation**: Server-side EXIF check
**Error message**: "Photo must be taken within last 5 minutes"
**Config**: `photo_max_age_minutes: 5`
**Archivos**: Integrar con #267

## 8.11 Ecosystem Integration (P2 - GAP ANALYSIS V2) [Items #275-281]

> **FUENTE**: PLAN.md + Article V35 - integraciones del ecosistema Ultravioleta

### [ ] #275 - Lucid Agents partnership
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Integration con Lucid Agents para delegation
**Features**:
- Lucid agents pueden publicar tasks
- Shared reputation scoring
- Cross-platform task routing
**Archivos**: `mcp-server/src/integrations/lucid/` (crear)

### [ ] #276 - Colmena task routing
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Integration con Colmena para distributed task assignment
**Features**:
- Geographic task distribution
- Load balancing entre workers
- Failover automatico
**Archivos**: `mcp-server/src/integrations/colmena/` (crear)

### [ ] #277 - ChainWitness batch API
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Batch notarization para eficiencia de gas
**Batch size**: 10-50 evidences por tx
**Frequency**: Cada 15 minutos o cuando batch lleno
**Archivos**: Extender #125-130 con batch support

### [ ] #278 - Faro error tracking
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Integration con Faro para monitoring
**Track**:
- MCP tool errors
- Payment failures
- Verification timeouts
- Worker app crashes
**Archivos**: `mcp-server/src/integrations/faro/` (crear)

### [ ] #279 - Council AI review
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Usar Council para AI verification decisions
**Flow**: Disputed AI decisions → Council multi-model consensus
**Models**: Claude + GPT-4V + Gemini
**Threshold**: 2-of-3 agreement
**Archivos**: `mcp-server/src/integrations/council/` (crear)

### [ ] #280 - AbraCadabra transcription
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Transcripción de audio evidence
**Use cases**:
- Voice notes como evidence
- Audio verification tasks
- Accessibility support
**Archivos**: `mcp-server/src/integrations/abracadabra/` (crear)

### [ ] #281 - Telemesh notifications
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Real-time notifications via Telemesh
**Events**: New task nearby, submission approved, payment received
**Channels**: Push + Email + Telegram
**Archivos**: `mcp-server/src/integrations/telemesh/` (crear)

## 8.12 Compliance & Legal (P2-P3 - GAP ANALYSIS V2) [Items #282-285]

> **FUENTE**: Gemini V32 - gaps de compliance no abordados

### [ ] #282 - Tax reporting integration
**Status**: NOT STARTED
**Prioridad**: P3
**Descripción**: Generar reportes para declaración de impuestos
**Features**:
- Export de earnings por período
- Formato compatible con autoridades locales
- 1099-MISC style reports (US)
**Archivos**: `dashboard/src/pages/TaxReports.tsx` (crear)

### [ ] #283 - GDPR compliance
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Derecho al olvido vs blockchain immutability
**Solution**:
- PII en database (deletable)
- Solo hashes en blockchain
- Export de datos personales
- Deletion request flow
**Archivos**: `mcp-server/src/compliance/gdpr.py` (crear)

### [ ] #284 - Cross-border payment regulations
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Cumplimiento por jurisdicción
**Checks**:
- OFAC sanctions list
- Country-specific limits
- KYC tiers por monto
**Archivos**: `mcp-server/src/compliance/regulations.py` (crear)

### [ ] #285 - Evidence retention policy
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Cuánto tiempo guardar evidence
**Policy**:
- Photos: 90 días en hot storage
- Hashes: Permanente en blockchain
- Disputes: 2 años
- Completed tasks: 30 días full, luego compressed
**Archivos**: `mcp-server/src/jobs/evidence_cleanup.py` (crear)

## 8.13 Worker Experience (P1-P2 - GAP ANALYSIS V2) [Items #286-290]

> **FUENTE**: Grok brainstorming - mejoras de experiencia worker faltantes

### [ ] #286 - Probation tier for new workers
**Status**: NOT STARTED
**Prioridad**: P1
**Descripción**: Nuevos workers empiezan en tier provisional
**Rules**:
- Primeros 10 tasks: probation tier
- Max task value: $5 durante probation
- Extra verification required
- Graduation: 8/10 successful → full tier
**Archivos**: `mcp-server/src/reputation/probation.py` (crear)

### [ ] #287 - Reputation recovery path
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Cómo recuperar reputation después de ban temporal
**Path**:
1. 30-day cooling off
2. Re-verification (KYC + video)
3. Start at probation tier
4. Accelerated graduation si clean record
**Archivos**: `mcp-server/src/reputation/recovery.py` (crear)

### [ ] #288 - Worker mentorship program
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Workers experimentados guían a nuevos
**Features**:
- Mentor matching por skill/region
- Bonus para mentors por mentee success
- In-app messaging
**Archivos**: `dashboard/src/pages/Mentorship.tsx` (crear)

### [ ] #289 - Accessibility accommodations
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Tasks adaptadas para workers con discapacidades
**Features**:
- Voice-only verification tasks
- Extended time limits
- Simplified UI option
- Screen reader compatible
**Archivos**: Accessibility audit + modifications

### [ ] #290 - Night/weekend premiums
**Status**: NOT STARTED
**Prioridad**: P2
**Descripción**: Bonus automático por horarios difíciles
**Premiums**:
- Weekends: +15%
- Nights (10pm-6am): +25%
- Holidays: +50%
**Config**: `premiums.yaml` con reglas por región
**Archivos**: `mcp-server/src/pricing/time_premiums.py` (crear)

---

# VALORES OFICIALES UNIFICADOS (GAP ANALYSIS V2)

> **IMPORTANTE**: Estos valores son la FUENTE DE VERDAD después de reconciliar todas las discrepancias

| Parámetro | Valor Oficial | Notas |
|-----------|---------------|-------|
| Min net payout | **$0.50** | Después de fees |
| Platform fee | **6-8%** | Variable por task_type |
| C parameter (Bayesian) | **15-20** | Configurable |
| m prior (Bayesian) | **50** | Neutral |
| Decay rate | **0.9^months** | Configurable |
| Escalation rate | **15%** | Cada 2 horas |
| Streaming rate | **$18/hr** | Reference |
| Photo max age | **5 minutos** | Desde captura |
| Network timeout | **30 segundos** | Para retries |
| Task radius walk | **500m max** | Default |
| Insurance cap | **$500/incident** | Goods insurance |
| Robot human split | **70/30** | Default mandate |
| Probation tasks | **10** | Para new workers |

---

# RESUMEN POR PRIORIDAD

## P0 - BLOCKERS (Sin esto no hay MVP)
| # | Item | Fase |
|---|------|------|
| 1-3 | Wallet Abstraction | 0 |
| 4-6 | Off-ramp Colombia | 0 |
| 8-9 | JSON Schema validation | 0 |
| 11-12 | MCP tools adicionales | 0 |
| 16-20 | Task flow completo | 1 |
| 21-25 | x402 básico | 1 |
| **78** | **Bayesian Average calculation** | **3** |
| **222-223** | **Bootstrap: POAP + DAO tasks** | **8** |
| **265** | **Gallery upload prohibition** | **8.9** |

## P1 - CRÍTICO (Primera semana post-MVP)
| # | Item | Fase |
|---|------|------|
| 26-32 | Dashboard MVP | 1 |
| 33-38 | Verification tier 1-2 | 1 |
| 39-45 | x402r refunds + Agent bonds | 2 |
| **42** | **Proof of attempt** | **2** |
| **45** | **Agent bond mechanism** | **2** |
| **46-50** | **Partial payouts** | **2** |
| 51-55 | Payment channels | 2 |
| 69-77 | ERC-8004 core | 3 |
| **78-87** | **Bayesian aggregation layer** | **3** |
| 101-108 | Hardware attestation | 4 |
| **131-136** | **Worker protection fund** | **5** |
| **137-140** | **Min net payout floor** | **5** |
| **229-232** | **Side-hustle positioning** | **8** |
| **238-239** | **GPS spoofing + GenAI detection** | **8** |
| **249-253** | **Dashboard: Profile, Notifications, Disputes** | **8** |
| **261, 263-264** | **IRC x402-flow + A2A MeshRelay + Webhooks** | **8.8** |
| **266-270** | **Multi-device, Photo freshness, Tampering, Wash trading, Rate limits** | **8.9** |
| **271-274** | **Network handling, Timeouts, Partial completion** | **8.10** |
| **286** | **Probation tier for new workers** | **8.13** |

## P2 - IMPORTANTE (Primer mes)
| # | Item | Fase |
|---|------|------|
| 56-62 | Superfluid streaming | 2 |
| 63-68 | Dynamic bounty | 2 |
| **88-93** | **Context tags and appeals** | **3** |
| 94-100 | Seals system | 3 |
| 109-116 | AI review avanzado | 4 |
| 117-124 | Safe Pool arbitration | 4 |
| 125-130 | ChainWitness | 4 |
| **141-145** | **Regional payout scaling** | **5** |
| **146-150** | **Task bundling** | **5** |
| 151-160 | Enterprise | 6 |
| 161-166 | Flexible rewards | 6 |
| 167-173 | Multi-chain | 6 |
| 186-190 | Describe.net | 6 |
| **191-203** | **Worker guilds + governance** | **7** |
| 204-209 | Agent-worker trust | - |
| **224-228** | **Bootstrap advanced: Overflow, Referral, Pilots** | **8** |
| **233-237** | **Worker staking for high-value** | **8** |
| **240-244** | **Goods insurance, Effort bonus, Safety** | **8** |
| **245-248** | **Discovery/Auction pricing** | **8** |
| **254-260** | **Agent dashboard, Hybrid mandates** | **8** |
| **262** | **IRC channel naming** | **8.8** |
| **275-281** | **Ecosystem integration (Lucid, Colmena, ChainWitness, Faro, Council, AbraCadabra, Telemesh)** | **8.11** |
| **283-285** | **GDPR, Regulations, Evidence retention** | **8.12** |
| **287-290** | **Rep recovery, Mentorship, Accessibility, Night/weekend premiums** | **8.13** |

## P3 - NICE-TO-HAVE (Backlog)
| # | Item | Fase |
|---|------|------|
| 174-185 | Robot executors | 6 |
| 210-216 | Platform competition | - |
| 217-221 | Advanced analytics | - |
| **282** | **Tax reporting** | **8.12** |

---

# PROGRESO TRACKING

## Por Fase
| Fase | Total | Done | Progress |
|------|-------|------|----------|
| 0 | 12 | 1 | 8% |
| 1 | 26 | 5 | 19% |
| 2 | 30 | 0 | 0% |
| 3 | 36 | 1 | 3% |
| 4 | 30 | 0 | 0% |
| 5 (Worker Protection) | 20 | 0 | 0% |
| 6 | 40 | 0 | 0% |
| 7 (Worker Empowerment) | 13 | 0 | 0% |
| 8.1-8.7 (Bootstrap Original) | 39 | 0 | 0% |
| 8.8 IRC/A2A | 4 | 0 | 0% |
| 8.9 Fraud Prevention | 6 | 0 | 0% |
| 8.10 Network | 4 | 0 | 0% |
| 8.11 Ecosystem | 7 | 0 | 0% |
| 8.12 Compliance | 4 | 0 | 0% |
| 8.13 Worker Experience | 5 | 0 | 0% |
| Adicional | 34 | 0 | 0% |
| **TOTAL** | **294** | **7** | **2.4%** |

## Por Prioridad
| Prioridad | Total | Done | Progress |
|-----------|-------|------|----------|
| P0 | 30 | 2 | 7% |
| P1 | 98 | 5 | 5% |
| P2 | 130 | 0 | 0% |
| P3 | 36 | 0 | 0% |

---

# PRÓXIMOS PASOS RECOMENDADOS

## Esta Semana (P0 Focus)
1. [ ] Integrar Crossmint (#1) - Wallet abstraction
2. [ ] Crear JSON schemas para evidence (#8)
3. [ ] Implementar escrow deposit (#22)
4. [ ] **Implementar Bayesian Average calculation (#78)** - CRÍTICO

## Siguiente Semana
1. [ ] Nequi integration (#4) - Off-ramp
2. [ ] Evidence upload flow (#18)
3. [ ] Auto-check GPS (#33)
4. [ ] **Partial payout flow (#46-48)** - Protección worker

## Este Mes
1. [ ] x402r merchant registration (#39)
2. [ ] AI Review básico (#36)
3. [ ] Worker registration en ERC-8004 (#70)
4. [ ] **Agent bond mechanism (#45)** - Equilibra poder
5. [ ] **Worker protection fund (#131)** - Safety net

---

# CHANGELOG

## v4.0.0 (2026-01-25) - GAP ANALYSIS V2 (8 SUBAGENT SYNTHESIS)
- **NUEVO**: GAP_ANALYSIS_REPORT_V2_20260125.md con ~180+ gaps identificados
- **NUEVO**: 6 sub-fases adicionales en Fase 8 (8.8-8.13):
  - 8.8 IRC/A2A Protocol (#261-264) - Comunicación enteramente faltante
  - 8.9 Fraud Prevention Advanced (#265-270) - Gallery prohibition, multi-device, tampering
  - 8.10 Network & Connectivity (#271-274) - Timeout handling, partial completion
  - 8.11 Ecosystem Integration (#275-281) - Lucid, Colmena, ChainWitness, Faro, Council, AbraCadabra, Telemesh
  - 8.12 Compliance & Legal (#282-285) - GDPR, regulations, evidence retention
  - 8.13 Worker Experience (#286-290) - Probation tier, mentorship, accessibility
- **NUEVO**: Sección "VALORES OFICIALES UNIFICADOS" reconciliando todas las discrepancias
- **FUENTES ANALIZADAS** (8 subagentes paralelos):
  - Grok brainstorming (777 líneas) → 44 gaps
  - Gemini V32 (307 líneas) → 72 items, 34% no cubierto
  - SPEC.md → 55 gaps (IRC protocol enteramente faltante)
  - .internal folder → 15 discrepancias (C parameter range)
  - Article V35 → 50 diferencias de valores
  - PLAN.md → 25 faltantes + 3 mismatches críticos
  - Dashboard code → 9+ componentes faltantes, 45-55% real
  - Landing pages → 15+ discrepancias ($0.25 vs $0.50)
- **VALORES UNIFICADOS**:
  - Min payment: **$0.50** (no $0.25)
  - Platform fee: **6-8%** (no 2.5%)
  - C parameter: **15-20** (no 15 fijo)
  - Escalation: **15%/2hr** (reconciliado)
- Total items: 264 → 294 (+30 nuevos)

## v3.1.0 (2026-01-24) - MCP TOOLS VERIFICATION
- **CORREGIDO**: Item #10 - Lista de tools actualizada a los 6 que realmente existen en código
  - Antes listaba tools que no existen: em_apply_to_task, em_submit_work, etc.
  - Ahora lista los 6 reales: publish_task, get_tasks, get_task, check_submission, approve_submission, cancel_task
- **NUEVO**: Items #11, #11b, #11c, #11d - Worker tools pendientes de implementar
  - em_apply_to_task (WORKER)
  - em_submit_work (WORKER)
  - em_get_my_tasks (WORKER)
  - em_withdraw_earnings (WORKER)
- **NUEVO**: Item #12 actualizado a em_assign_task (AGENT)
- **NUEVO**: GAP_ANALYSIS_REPORT_20260124.md con 37 discrepancias identificadas
- Total items: 260 → 264 (+4 worker tools)

## v3.0.0 (2026-01-24) - COMPREHENSIVE GAP ANALYSIS
- **NUEVO**: Fase 8 - Bootstrap & Adoption (items #222-260)
  - 8.1 Chicken-Egg Solution (#222-228) - POAP hunters, DAO tasks, enterprise overflow
  - 8.2 Explicit Positioning (#229-232) - Side-hustle framing, transition messaging
  - 8.3 Worker Staking High-Value (#233-237) - Stake requirements para tasks >$50
  - 8.4 Fraud Mitigation Advanced (#238-244) - GPS spoofing, GenAI detection, Goods insurance
  - 8.5 Discovery/Auction Pricing (#245-248) - Time-based price discovery
  - 8.6 Dashboard Missing Components (#249-255) - Profile, Notifications, Disputes UI
  - 8.7 Hybrid Human-Robot Details (#256-260) - 20-40% human oversight mandate
- **FUENTES INCORPORADAS**:
  - grok-erc8004-overall-brainstorming.txt (777+ líneas)
  - gemini-v32-analisis.txt (307 líneas)
  - Dashboard analysis (75-80% complete, gaps identified)
  - .internal/REPUTATION_SECRET_SAUCE.md (Bayesian formula confirmada)
- Total items: 221 → 260 (+39 nuevos de gap analysis completo)

## v2.0.0 (2026-01-24)
- **NUEVO**: Fase 5 - Worker Protection (items #131-150)
- **NUEVO**: Fase 7 - Worker Empowerment (items #191-203)
- **NUEVO**: Sección 3.2 - Bayesian Aggregation Layer (items #78-87)
- **NUEVO**: Sección 3.3 - Context Tags and Appeals (items #88-93)
- **NUEVO**: Sección 2.2 - Partial Payouts (items #46-50)
- **ACTUALIZADO**: #42 Proof of attempt con fórmula completa
- **ACTUALIZADO**: #45 Agent bond con detalles de slashing
- **ACTUALIZADO**: #80 Reputation decay con fórmula 0.9^months
- **ACTUALIZADO**: Hardware attestation con detalles iOS/Android
- Total items: 180 → 221 (+41 nuevos de Grok feedback)

## v1.0.0 (2026-01-24)
- Versión inicial consolidando TODO.md, TODO-1.md, TODO-2.md
- 180 items en 5 fases

---

*Última actualización: 2026-01-25*
*Versión: 4.0.0*
*Generado por: Claude Code (8 subagentes paralelos)*
*Fuentes: Control-Plane Execution Market Analysis + Grok Brainstorming (777 líneas) + Gemini V32 (307 líneas) + SPEC.md + PLAN.md + Article V35 + Dashboard Review + MCP Server Code + Landing Pages + .internal folder*
*Gaps Identificados: ~180+ elementos → 30 nuevos items agregados (#261-290)*

# Plan: Golden Flows, Reputation Enforcement, y TX Visibility

> **Fecha**: 2026-02-14
> **Estado**: PLANIFICACION (no implementar todavia)
> **Prioridad**: Alta — completa la historia de trustless + transparencia

---

## 1. Todos los Golden Flows (E2E con plata real)

Cada flow es un script independiente en `scripts/` que corre contra produccion
con bounties de $0.10 y genera su propio reporte en `docs/reports/`.

### 1.1 Golden Flow: Happy Path (YA EXISTE)
- `scripts/e2e_golden_flow.py` — 7/7 PASS
- Create → Assign (escrow lock) → Submit → Approve (1-TX release) → Rate

### 1.2 Golden Flow: Agent Cancels After Assignment (REFUND)
- `scripts/e2e_refund_flow.py`
- Create task → Worker applies → Agent assigns (escrow locks $0.10) → Agent cancels
- **Verificar**: Refund TX on-chain, agente recupera fondos, escrow balance = 0
- **Reporte**: `docs/reports/REFUND_FLOW_REPORT.md`

### 1.3 Golden Flow: Agent Cancels Before Assignment (NO ESCROW)
- `scripts/e2e_cancel_before_assign_flow.py`
- Create task (balance check only) → Agent cancels
- **Verificar**: No TX on-chain (no escrow fue creado), task status = cancelled
- Flujo trivial pero importante: confirma que cancel sin escrow es limpio

### 1.4 Golden Flow: Submission Rejected (Major)
- `scripts/e2e_rejection_flow.py`
- Create → Assign → Submit → Agent REJECTS (severity: major)
- **Verificar**: Escrow sigue bloqueado (no se libera ni se reembolsa), negative reputation feedback on-chain, worker puede re-submit
- Pregunta abierta: despues de rejection, se queda asignado o vuelve a published?

### 1.5 Golden Flow: Task Expires
- `scripts/e2e_expiry_flow.py`
- Create task con deadline corto (5 min) → Nadie aplica → Task expira
- **Verificar**: En direct_release mode no hay escrow que reembolsar (escrow es en assignment)
- Verificar que task status = expired

### 1.6 Golden Flow: Reputation Gate
- `scripts/e2e_reputation_gate_flow.py`
- Create task con min_reputation=80 → Worker con score < 80 intenta aplicar → 403
- Worker con score >= 80 aplica → OK
- **Verificar**: El gate funciona, error message es claro
- Puede ser dry (sin escrow) ya que el bloqueo es antes del assignment

### 1.7 Golden Flow: Worker Checks Agent Reputation (NUEVO)
- Necesita endpoint o logica nueva (ver seccion 2)
- Worker consulta reputacion del agente antes de aplicar
- Si agente tiene bad rep, worker decide no aplicar

### Tabla resumen

| # | Flow | Escrow? | TXs esperadas | Costo |
|---|------|---------|---------------|-------|
| 1.1 | Happy path | Si | 4 (lock, release, 2 reputation) | $0.10 |
| 1.2 | Refund (post-assign) | Si | 2 (lock, refund) | $0.00 (refund) |
| 1.3 | Cancel (pre-assign) | No | 0 | $0.00 |
| 1.4 | Rejection | Si | 2+ (lock, neg reputation) | $0.10 (locked) |
| 1.5 | Expiry | No | 0 | $0.00 |
| 1.6 | Reputation gate | No | 0 | $0.00 |
| 1.7 | Worker checks agent | No | 0 | $0.00 |

**Costo total para correr TODOS los flows**: ~$0.20 (solo 1.1 y 1.2 mueven plata)

---

## 2. Reputation Bidireccional — Lo que falta

### 2.1 Lo que YA funciona
- Agente pone `min_reputation` al crear tarea
- Worker con score bajo es bloqueado al aplicar (403)
- Worker con score bajo es bloqueado al ser asignado (403)
- Agente califica worker despues de aprobar (on-chain)
- Worker califica agente despues de aprobar (on-chain, trustless)
- Rejection "major" envia feedback negativo on-chain

### 2.2 Lo que FALTA: Worker ve reputacion del agente

**Problema**: El worker no tiene forma facil de ver la reputacion del agente
antes de decidir si toma la tarea. Si un agente tiene reputacion mala
(no paga, pone tareas imposibles, etc.), el worker deberia poder verlo.

**Solucion propuesta** (minima):
1. **API**: `GET /api/v1/reputation/agent/{agent_wallet}` — retorna score, count, tier
   - Ya existe parcialmente: `GET /api/v1/reputation/info` retorna info del EM agent
   - Falta: endpoint generico para consultar cualquier agente por wallet
2. **Dashboard**: En la vista de tarea, mostrar score del agente junto al nombre
   - Tier badge (Bronce/Plata/Oro/Diamante) al lado del creador
3. **NO necesario ahora**: Bloqueo automatico (worker decide, no el sistema)

### 2.3 Tests de reputation que faltan

| Test | Que verifica |
|------|-------------|
| Worker con score 25 aplica a tarea con min_rep 50 → 403 | Gate funciona |
| Worker con score 75 aplica a tarea con min_rep 50 → OK | Gate permite |
| Worker con score 50 aplica a tarea con min_rep 50 → OK | Boundary exacto |
| Worker con score 49 aplica a tarea con min_rep 50 → 403 | Boundary -1 |
| Tarea sin min_rep (default 0) → cualquiera aplica | Default funciona |
| Score baja por rejection, luego intenta aplicar a tarea con min → blocked | Cascading effect |
| Worker consulta rep del agente antes de aplicar | Endpoint funciona |

---

## 3. TX Links en cada Tarea (Dashboard)

### 3.1 El problema
Hoy las transacciones se guardan en `payment_events`, `submissions.payment_tx`,
`tasks.escrow_tx`, `tasks.refund_tx` — pero el dashboard NO muestra estos links
en la vista de detalle de la tarea. El worker/agente no puede ver la evidencia
on-chain del pago.

### 3.2 Lo que YA tenemos
- **DB**: `payment_events` table con tx_hash, event_type, amount, status por task
- **DB**: `tasks.escrow_tx`, `tasks.refund_tx` columns
- **DB**: `submissions.payment_tx` column
- **DB**: `escrows` table con metadata (tiene tx hashes)
- **Dashboard**: `TxHashLink` componente listo (trunca hash, link a BaseScan, copy)
- **Dashboard**: `PaymentStatus`, `PaymentHistory` componentes existentes

### 3.3 Lo que FALTA

#### A. API endpoint para TX history de una tarea
```
GET /api/v1/tasks/{task_id}/transactions
```
Retorna lista ordenada cronologicamente:
```json
[
  {
    "event": "escrow_lock",
    "tx_hash": "0xba6f...",
    "amount_usdc": 0.10,
    "from": "0xD386...",
    "to": "0x48ad...",
    "timestamp": "2026-02-14T17:50:00Z",
    "explorer_url": "https://basescan.org/tx/0xba6f...",
    "status": "confirmed"
  },
  {
    "event": "escrow_release",
    "tx_hash": "0xa86b...",
    "amount_usdc": 0.10,
    "timestamp": "2026-02-14T17:51:00Z",
    "details": {
      "worker_net": 0.087,
      "operator_fee": 0.013
    }
  }
]
```
**Fuente de datos**: JOIN de `payment_events` + `tasks.escrow_tx` + `tasks.refund_tx` + `submissions.payment_tx`

#### B. Dashboard: Seccion "Transacciones" en TaskDetail
- Mostrar timeline de TXs con `TxHashLink` para cada una
- Labels en espanol: "Deposito Escrow", "Pago al Worker", "Fee Plataforma", "Reembolso"
- Iconos por tipo (lock, unlock, refund)
- Visible para todos (agente y worker)

#### C. Estados visuales por fase de la tarea

| Estado tarea | TXs visibles |
|-------------|-------------|
| published | Ninguna (balance check no es TX) |
| accepted (assigned) | Deposito Escrow (TX1) |
| submitted | Deposito Escrow |
| completed | Deposito + Pago Worker + Fee (TX1, TX2) |
| cancelled (con escrow) | Deposito + Reembolso (TX1, TX refund) |
| cancelled (sin escrow) | Ninguna |
| expired | Ninguna (o refund si habia escrow) |

### 3.4 Consolidar en tabla `task_transactions`

**Nueva tabla** (o usar `payment_events` que ya existe):

`payment_events` YA tiene todo lo que necesitamos:
- `task_id`, `event_type`, `tx_hash`, `amount_usdc`, `from_address`, `to_address`, `status`
- Solo falta verificar que TODOS los eventos se estan escribiendo correctamente

**Verificar que se loguean**:
- [ ] `escrow_lock` — al asignar worker (authorize_escrow_for_worker)
- [ ] `escrow_release` — al aprobar (release_direct_to_worker)
- [ ] `disburse_worker` — si aplica (platform_release mode)
- [ ] `disburse_fee` — si aplica
- [ ] `refund` — al cancelar (refund_trustless_escrow)
- [ ] `reputation_agent_rates_worker` — al calificar
- [ ] `reputation_worker_rates_agent` — al calificar

Si `payment_events` ya cubre escrow/release/refund, solo falta agregar
los eventos de reputacion (TX3, TX4 del Golden Flow) a la misma tabla.

---

## 4. Cleanup de Tareas de Test

### 4.1 Problema
Hay multiples tareas de test acumuladas en la DB de produccion.
Solo deberia quedar visible la ultima (Golden Flow 7/7 PASS).

### 4.2 Opciones

**Opcion A**: Soft-delete (cambiar status a `archived` o `test_completed`)
- No perder data historica
- Agregar filtro en API: `GET /tasks` excluye archived por default

**Opcion B**: Marcar como test
- Agregar `is_test: true` flag
- Dashboard filtra por default `is_test = false`

**Opcion C**: No tocar — dejar todas visibles
- Son pocas (~10-15 tareas de test)
- El worker las ve pero no pasa nada

**Recomendacion**: Opcion A (soft-delete con `archived`). Mantiene la data
para auditorias pero limpia la UI.

### 4.3 Tareas a mantener
- La ultima del Golden Flow 7/7 PASS (task_id: `7b4c0175-9ba6-4c93-84e9-36bebe0ec25a`)
- Todas las demas → `archived`

---

## 5. Scoring de Utilidad — TODOS los Features

Escala: 1-10 (10 = critico, 1 = innecesario)

### Tier 1: Critico (9-10) — Sin esto no estamos listos

| # | Feature | Score | Justificacion |
|---|---------|-------|---------------|
| A | TX links en dashboard por tarea | **10** | Transparencia = confianza. Sin esto el worker no puede verificar que le pagaron. Es lo basico de trustless. |
| B | API endpoint TXs por tarea | **10** | Prerrequisito de A. Sin API, el dashboard no puede mostrar nada. |
| C | Verificar payment_events logging completo | **9** | Si no estamos guardando todos los TX hashes, perdemos la evidencia on-chain. Auditable = no negociable. |
| D | Refund Flow E2E (agent cancels post-assign) | **9** | Segundo escenario mas probable despues del happy path. Plata real involucrada. Si el refund falla, el agente pierde fondos. |

### Tier 2: Importante (7-8) — Necesario para produccion real

| # | Feature | Score | Justificacion |
|---|---------|-------|---------------|
| E | Cancel before assign E2E | **8** | Verifica que cancel sin escrow es limpio. Trivial pero si falla es un bug visible. |
| F | Tests unitarios reputation gate | **8** | Ya funciona en codigo pero no hay tests de boundary (score=49 vs min=50). Regresion silenciosa posible. |
| G | Worker ve reputacion del agente | **7** | El worker merece saber si el agente es confiable. Pero en fase temprana con pocos agentes, menos urgente. |
| H | Rejection Flow E2E (major) | **7** | Importante para verificar que negative reputation funciona on-chain. Pero es un edge case menos frecuente. |

### Tier 3: Util (4-6) — Nice to have, no bloquea

| # | Feature | Score | Justificacion |
|---|---------|-------|---------------|
| I | Cleanup tareas de test | **6** | Housekeeping. Las tareas viejas no hacen dano pero ensucian la UI. |
| J | Reputation Gate E2E (plata real) | **5** | El gate es server-side (no on-chain), se puede probar con unit tests. E2E con plata real no agrega mucho. |
| K | Expiry Flow E2E | **5** | En direct_release no hay escrow que reembolsar si expira. Es un cambio de status en DB, trivial. |
| L | Worker checks agent rep E2E | **4** | Depende de G (endpoint nuevo). Es un GET request, no necesita plata real para probar. |

### Tier 4: Probablemente No Tiene Sentido (1-3)

| # | Feature | Score | Justificacion |
|---|---------|-------|---------------|
| M | Auto-cancelar si reputation baja post-asignacion | **2** | Overengineering. Una vez asignado, el escrow esta bloqueado. Cancelar automaticamente penaliza al worker por algo que paso DESPUES. El agente ya lo eligio. Ademas crea race conditions. |
| N | Limite de valor de tarea segun tier de reputation | **2** | Premature. Con bounties de $0.10-$1.00, no hay riesgo real. Cuando haya tareas de $100+, entonces si. Pero hoy agrega complejidad sin beneficio. |
| O | Limite de tareas concurrentes segun tier | **2** | Mismo argumento que N. En fase temprana con pocos workers, limitar concurrencia frena la adopcion. |
| P | Filtrar tareas por "soy elegible" en dashboard | **3** | Util para UX pero no critico. El worker intenta aplicar y si no puede, ve el error. Con pocos workers y pocas tareas, el filtro no ahorra mucho tiempo. |
| Q | Probation tier enforcement automatico | **1** | Mencionado en codigo dormant. Requiere definir reglas complejas de probation, review periods, appeal process. Demasiado para la fase actual. |

### Resumen visual

```
10 |  A B
 9 |  C D
 8 |  E F
 7 |  G H
 6 |  I
 5 |  J K
 4 |  L
 3 |  P
 2 |  M N O
 1 |  Q
   +----------
     Utilidad
```

### Orden de implementacion recomendado

1. **B** → API endpoint TXs por tarea (score 10)
2. **A** → TX links en dashboard (score 10, depende de B)
3. **C** → Audit payment_events logging (score 9)
4. **D** → Refund Flow E2E (score 9)
5. **E** → Cancel before assign E2E (score 8)
6. **F** → Tests reputation gate (score 8)
7. **G** → Worker ve rep del agente (score 7)
8. **H** → Rejection Flow E2E (score 7)
9. **I** → Cleanup tareas test (score 6)
10. M-Q → No implementar por ahora

---

## 6. Preguntas Abiertas

1. **Despues de rejection, que pasa con la tarea?**
   - Vuelve a `published` para que otro worker aplique?
   - Se queda `accepted` para que el mismo worker re-submit?
   - El agente decide? (re-open vs cancel)

2. **Reputation del agente: donde se muestra?**
   - Solo en la vista de detalle de tarea?
   - Tambien en la lista de tareas disponibles?
   - Badge de tier visible?

3. **Cleanup: que tan agresivo?**
   - Archivar TODAS las viejas?
   - Dejar las ultimas N?
   - Crear un admin endpoint para archivar?

4. **Reputation events en payment_events?**
   - Meter reputation TXs en `payment_events` (mismo table)?
   - O crear `reputation_events` table separada?
   - `payment_events` ya tiene el schema correcto (task_id, tx_hash, event_type)

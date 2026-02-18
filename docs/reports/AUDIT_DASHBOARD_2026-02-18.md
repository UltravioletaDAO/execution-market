# Dashboard Audit Report — H2A, A2A, Publisher Flow

**Fecha**: 2026-02-18
**Auditor**: dashboard-auditor (Claude Opus 4.6)
**Alcance**: Nuevas paginas H2A, A2A, publisher flow, Agent Directory, FAQ, i18n, routing

---

## 1. Inventario de Nuevas Paginas y Componentes

| Archivo | Tipo | Lineas | Descripcion |
|---------|------|--------|-------------|
| `pages/publisher/CreateRequest.tsx` | Pagina | 280 | Wizard de 4 pasos para crear solicitudes H2A (Detalles, Agente, Presupuesto, Vista Previa) |
| `pages/publisher/Dashboard.tsx` | Pagina | 120 | Panel de publicador con tabs (Activas, Por Revisar, Historial), stats, task cards |
| `pages/publisher/ReviewSubmission.tsx` | Pagina | 137 | Revision de entregas de agentes con 3 veredictos (aprobar, revision, rechazar) |
| `pages/AgentDirectory.tsx` | Pagina | 93 | Directorio publico de agentes IA con filtros por capacidad, ordenamiento, paginacion |
| `pages/FAQ.tsx` | Pagina | 173 | FAQ con 7 categorias incluyendo nuevas secciones A2A y H2A (usando i18n) |
| `components/landing/A2ASection.tsx` | Componente | 113 | Seccion landing A2A: 3 feature cards + comparacion H2A vs A2A |
| `components/landing/H2ASection.tsx` | Componente | 121 | Seccion landing H2A: 3 feature cards + comparacion H2W vs H2A + CTAs |
| `services/h2a.ts` | Servicio | 79 | Capa de API para H2A: createTask, listTasks, getTask, getSubmissions, approve, cancel, agentDirectory |
| `types/database.ts` | Tipos | 868 | Tipos TypeScript extendidos con H2A, AgentDirectory, VerificationMode, DigitalEvidenceType, UserRole |

---

## 2. Analisis de Routing

### Rutas Registradas en App.tsx

| Ruta | Componente | Guard | Estado |
|------|-----------|-------|--------|
| `/agents/directory` | `AgentDirectory` | Ninguno (publico) | OK |
| `/publisher/dashboard` | `PublisherDashboard` | `AuthGuard` | OK |
| `/publisher/requests/new` | `PublisherCreateRequest` | `AuthGuard` | OK |
| `/publisher/requests/:id/review` | `PublisherReviewSubmission` | `AuthGuard` | OK |
| `/faq` | `FAQ` | Ninguno (publico) | OK |

### Navegacion Interna (Links entre paginas)

| Origen | Destino | Metodo | Estado |
|--------|---------|--------|--------|
| `PublisherDashboard` -> Crear | `/publisher/requests/new` | `navigate()` | OK |
| `PublisherDashboard` -> Revisar | `/publisher/requests/${id}/review` | `navigate()` | OK |
| `CreateRequest` -> Exito -> Panel | `/publisher/dashboard` | `navigate()` | OK |
| `AgentDirectory` -> Contratar | `/publisher/requests/new?agent=${id}` | `navigate()` | OK |
| `CreateRequest` -> Paso Agente -> Directorio | `/agents/directory` | `navigate()` | **ISSUE-01** |
| `H2ASection` CTA -> Directorio | `/agents/directory` | `navigate()` | OK |
| `H2ASection` CTA -> Crear | `/publisher/requests/new` | `navigate()` | OK |
| `AppHeader` -> Agent Directory | `/agents/directory` | nav link | OK |

### ISSUE-01: Flujo de seleccion de agente roto (Severidad: MEDIA)

En `CreateRequest.tsx:181`, el boton "Agente Especifico" navega a `/agents/directory` con `navigate()`. El problema es que **no hay mecanismo de callback** para que AgentDirectory devuelva el agente seleccionado al wizard de creacion.

El flujo actual es:
1. Usuario esta en paso 2 del wizard (Agente)
2. Click en "Agente Especifico" -> navega a `/agents/directory`
3. En AgentDirectory, click en "Crear Solicitud" -> navega a `/publisher/requests/new?agent=${id}`
4. Esto **reinicia el wizard desde cero**, perdiendo titulo, instrucciones y categoria del paso 1

**Solucion sugerida**: Usar un modal/drawer para la seleccion de agente dentro del wizard, o guardar el estado del formulario en `sessionStorage`/`useSearchParams` antes de navegar.

### ISSUE-02: Ruta de review usa `:id` pero el componente espera `:taskId` (Severidad: BAJA)

En `App.tsx:411`, la ruta es `/publisher/requests/:id/review`, pero en `ReviewSubmission.tsx:14` se usa `useParams<{ taskId: string }>()`. Esto significa que `taskId` sera `undefined` en runtime.

**Fix**: Cambiar la ruta a `/publisher/requests/:taskId/review` o cambiar el componente a usar `useParams<{ id: string }>()`.

---

## 3. TypeScript — Consistencia de Tipos

### Tipos H2A (database.ts lineas 559-658)

| Tipo Frontend | Mapeo Backend (models.py / h2a.py) | Estado |
|---------------|-----------------------------------|--------|
| `H2ATaskCreateRequest` | `PublishH2ATaskRequest` | OK — campos coinciden |
| `H2ATaskCreateResponse` | `H2ATaskResponse` | OK |
| `H2AApprovalRequest` | `ApproveH2ASubmissionRequest` | OK |
| `H2AApprovalResponse` | `H2AApprovalResponse` | OK |
| `AgentDirectoryEntry` | `AgentDirectoryEntry` | OK |
| `AgentDirectoryResponse` | `AgentDirectoryResponse` | OK |

### ISSUE-03: TaskCategory no incluye categorias digitales H2A (Severidad: MEDIA)

`database.ts:4-10` define `TaskCategory` como solo las 5 categorias originales (physical, knowledge, authority, simple, digital_physical). Pero `CreateRequest.tsx:20-27` usa 6 categorias digitales nuevas (`data_processing`, `research`, `content_generation`, `code_execution`, `api_integration`, `multi_step_workflow`).

Estas categorias digitales **SI existen en el backend** (`models.py:37-42`), pero **NO estan en el tipo `TaskCategory` del frontend**. Esto causa un desajuste de tipos: el formulario envia categorias que TypeScript no reconoce como validas.

**Fix**: Extender `TaskCategory` en `database.ts` con las 6 categorias digitales.

### ISSUE-04: Tipo `Task` no tiene campos H2A (Severidad: BAJA)

`Task` interface (database.ts:106-135) no incluye `publisher_type`, `human_wallet`, `human_user_id`, `target_executor_type`, `required_capabilities`, `verification_mode`. Estos campos existen en la tabla `tasks` (backend h2a.py inserta con ellos) pero no en el tipo frontend. Esto no rompe runtime (JSON es flexible), pero los componentes que acceden a `task.publisher_type` no tienen type-safety.

El tipo `H2ATask extends Task` existe (linea 579) pero no se usa en `Dashboard.tsx` ni `ReviewSubmission.tsx` — ambos usan `Task`.

---

## 4. Integracion API (h2a.ts <-> h2a.py)

### Mapeo de Endpoints

| Frontend `h2a.ts` | Backend `h2a.py` | Metodo | Estado |
|-------------------|-----------------|--------|--------|
| `createH2ATask()` | `POST /api/v1/h2a/tasks` | POST | OK |
| `listH2ATasks()` | `GET /api/v1/h2a/tasks` | GET | OK |
| `getH2ATask(id)` | `GET /api/v1/h2a/tasks/{id}` | GET | OK |
| `getH2ASubmissions(id)` | `GET /api/v1/h2a/tasks/{id}/submissions` | GET | OK |
| `approveH2ASubmission(id)` | `POST /api/v1/h2a/tasks/{id}/approve` | POST | OK |
| `cancelH2ATask(id)` | `POST /api/v1/h2a/tasks/{id}/cancel` | POST | OK |
| `getAgentDirectory()` | `GET /api/v1/agents/directory` | GET | OK |
| `getAgentDetails(id)` | N/A (client-side workaround) | GET | **ISSUE-05** |

### ISSUE-05: getAgentDetails hace fetch de todos los agentes (Severidad: BAJA)

`h2a.ts:76-79` implementa `getAgentDetails()` haciendo `fetch('/directory?limit=100')` y luego filtrando en el cliente con `.find()`. Esto es ineficiente — deberia haber un endpoint dedicado `GET /api/v1/agents/directory/{executor_id}`. Sin embargo, esta funcion no se usa actualmente en ninguna pagina auditada, asi que el impacto es nulo por ahora.

### ISSUE-06: Error handling en approve con settlement_auth placeholder (Severidad: MEDIA)

En `ReviewSubmission.tsx:47`, cuando `verdict === 'accepted'`, se envia:
```ts
settlement_auth_worker: 'pending_browser_signature'
settlement_auth_fee: 'pending_browser_signature'
```

Este placeholder no es una firma EIP-3009 valida. El backend (`h2a.py:603-609`) valida que estos campos existan pero NO valida que sean firmas reales antes de intentar `sdk.settle_payment()`. Esto causa que el settlement falle silenciosamente (linea 643-647 captura la excepcion y guarda un `pending:...` como tx_hash).

**Situacion real**: El pago H2A necesita integracion con wallet signing en el browser (EIP-3009). El componente ReviewSubmission actualmente NO implementa la firma en el wallet — solo envia un placeholder. **Este flujo de pago esta incompleto.**

### ISSUE-07: Token auth crea instancia Supabase en cada request (Severidad: BAJA)

`h2a.ts:14-21` importa dinamicamente `@supabase/supabase-js` y crea un nuevo `createClient()` en cada llamada a `token()`. Esto funciona pero es ineficiente. Deberia reutilizar el cliente Supabase existente del contexto de auth.

---

## 5. i18n — Reporte de Completitud

### Seccion A2A Landing

| Key | en.json | es.json | pt.json |
|-----|---------|---------|---------|
| `landing.a2a.badge` | OK | OK | OK |
| `landing.a2a.title` | OK | OK | OK |
| `landing.a2a.subtitle` | OK | OK | OK |
| `landing.a2a.smartDelegation` | OK | OK | OK |
| `landing.a2a.smartDelegationDesc` | OK | OK | OK |
| `landing.a2a.sharedReputation` | OK | OK | OK |
| `landing.a2a.sharedReputationDesc` | OK | OK | OK |
| `landing.a2a.composability` | OK | OK | OK |
| `landing.a2a.composabilityDesc` | OK | OK | OK |
| `landing.a2a.h2aLabel` | OK | OK | OK |
| `landing.a2a.a2aLabel` | OK | OK | OK |
| `landing.a2a.*Items` (6 keys) | OK | OK | OK |

**A2A: 100% traducido en los 3 idiomas.**

### Seccion H2A Landing

| Key | en.json | es.json | pt.json |
|-----|---------|---------|---------|
| `landing.h2a.badge` | OK | OK | OK |
| `landing.h2a.title` | OK | OK | OK |
| `landing.h2a.subtitle` | OK | OK | OK |
| `landing.h2a.feature*` (6 keys) | OK | OK | OK |
| `landing.h2a.comparison.*` (5 keys) | OK | OK | OK |
| `landing.h2a.cta` | OK | OK | OK |
| `landing.h2a.ctaSecondary` | OK | OK | OK |

**H2A: 100% traducido en los 3 idiomas.**

### FAQ H2A/A2A Sections

| Key | en.json | es.json | pt.json |
|-----|---------|---------|---------|
| `help.faq.whatIsA2A` | OK | OK | **FALTA** |
| `help.faq.howA2AWorks` | OK | OK | **FALTA** |
| `help.faq.a2aReputation` | OK | OK | **FALTA** |
| `help.faq.whatIsH2A` | OK | OK | **FALTA** |
| `help.faq.howH2AWorks` | OK | OK | **FALTA** |
| `help.faq.h2aPricing` | OK | OK | **FALTA** |
| `help.categories.a2a` | OK | OK | **FALTA** |
| `help.categories.h2a` | OK | OK | **FALTA** |
| `help.categories.erc8128` | OK | OK | **FALTA** |
| `help.faq.whatIsERC8128` | OK | OK | **FALTA** |
| `help.faq.howERC8128Works` | OK | OK | **FALTA** |
| `help.faq.erc8128VsApiKeys` | OK | OK | **FALTA** |
| `help.stillNeedHelp.*` | OK | OK | OK (linea 779) |

### ISSUE-08: pt.json falta TODA la seccion `help.faq` y `help.categories` (Severidad: ALTA)

El archivo `pt.json` NO tiene las secciones `help.faq`, `help.categories`, ni ninguna FAQ en portugues. Esto significa que la pagina FAQ en portugues mostrara todas las fallback keys en ingles. Afecta a los 7 FAQ categories (28+ preguntas/respuestas).

Ademas, `pt.json` no tiene:
- `nav.agentDirectory` (se muestra en ingles en el header)
- `nav.developers` (falta tambien)
- Multiples secciones que existen en en/es pero no en pt: `help`, `dashboard`, `agentDashboard`, `analytics`, `about`, `dev`, `stake`, `tax`, `validator`, `agentReputation`, `rateAgent`, etc.

### ISSUE-09: Strings hardcoded en espanol en CreateRequest.tsx (Severidad: MEDIA)

`CreateRequest.tsx` tiene TODAS sus strings hardcoded en espanol, sin pasar por i18n:
- "Nueva Solicitud para Agente IA" (linea 128)
- "Procesamiento de Datos", "Investigacion" etc. (lineas 21-27)
- "Titulo *", "Instrucciones *" (lineas 151, 156)
- "Publicando...", "Publicar Solicitud" (lineas 268)
- Todas las labels de wizard steps, evidence options, deadline options, etc.

Lo mismo aplica para:
- `Dashboard.tsx` — todos los labels de status, tabs, stats hardcoded en espanol
- `ReviewSubmission.tsx` — todos los labels hardcoded en espanol
- `AgentDirectory.tsx` — labels de capacidades hardcoded en espanol

**Estos 4 componentes ignoran completamente el sistema i18n.** Los landing sections (A2ASection, H2ASection) y FAQ SI usan i18n correctamente.

---

## 6. UX Gaps y Flujos Incompletos

### Flujo Publisher Completo (esperado vs real)

```
Esperado: Home -> H2A Section CTA -> Agent Directory -> Seleccionar -> Create Request -> Preview -> Publish -> Dashboard -> Review -> Approve+Pay
                                                                                                                                    ^
Real:     Home -> H2A Section CTA -> Agent Directory -> "Crear Solicitud" -> Create Request (NEW wizard, no pre-fill agent) --------+
                                              OK           PARCIAL (agent via query param)                                          |
                                                                                                                                    |
          Publisher Dashboard -> Review -> Approve -> *PAGO INCOMPLETO* (placeholder signatures) -----> Dashboard                   |
                    OK              OK       BLOQUEADO                                                                              |
```

### Gaps Identificados

| # | Gap | Severidad | Descripcion |
|---|-----|-----------|-------------|
| G-01 | Pago H2A no funcional | **CRITICA** | ReviewSubmission envia placeholder strings en lugar de firmas EIP-3009 reales. El approve "funciona" pero el settlement falla. |
| G-02 | No hay acceso directo a Publisher Dashboard | MEDIA | El header (`AppHeader.tsx`) no tiene link a "Panel de Publicador". Un humano autenticado no tiene forma de llegar a `/publisher/dashboard` desde el menu principal sin saber la URL. |
| G-03 | Wizard pierde estado al navegar | MEDIA | Ver ISSUE-01 arriba. |
| G-04 | Sin feedback real-time al publicador | BAJA | No hay WebSocket ni polling en PublisherDashboard para actualizar cuando un agente acepta o entrega. Solo se actualiza al recargar. |
| G-05 | Bounty minimo inconsistente | BAJA | Frontend valida `bounty >= 0.50` (CreateRequest:83). Backend valida con config `feature.h2a_min_bounty` (default $0.50). Consistente pero hardcoded en frontend — si el backend cambia el min, el frontend no se entera. |

---

## 7. Auth — Proteccion de Rutas

### Evaluacion

| Ruta | Guard | Adecuado? | Nota |
|------|-------|-----------|------|
| `/agents/directory` | Ninguno | OK | Publico para discovery |
| `/publisher/dashboard` | `AuthGuard` | **PARCIAL** | AuthGuard solo verifica `isAuthenticated`. NO verifica que sea human_publisher. Un worker autenticado puede acceder. |
| `/publisher/requests/new` | `AuthGuard` | **PARCIAL** | Mismo problema — un agent puede acceder a crear solicitudes H2A |
| `/publisher/requests/:id/review` | `AuthGuard` | **PARCIAL** | El backend (h2a.py) SI verifica `human_user_id == auth.user_id`, asi que la proteccion real esta en el server. |

### ISSUE-10: No existe `PublisherGuard` (Severidad: BAJA)

Las rutas de publisher usan `AuthGuard` generico. Funciona porque el backend valida ownership, pero un worker podria ver el UI de publisher sin sentido. Seria mejor tener un guard basado en role/userType.

---

## 8. Componentes — Reuso y Consistencia

### Patrones Consistentes
- Todos los componentes usan Tailwind CSS (igual que el resto del dashboard)
- Patron de hook `useState`/`useEffect`/`useCallback` consistente
- Patron de error handling con try/catch + estado de error
- Patron de loading state uniforme

### Patrones Inconsistentes
- Publisher pages (Create, Dashboard, Review) usan strings hardcoded en espanol; el resto del dashboard usa i18n
- Publisher pages no usan `dark:` variants de Tailwind; H2ASection SI usa `dark:` classes
- AgentDirectory y CreateRequest duplican `CAPABILITY_OPTIONS` / `CAPS` con los mismos valores pero en archivos separados (DRY violation)

---

## 9. Escenarios E2E Sugeridos

### Suite E2E para H2A Publisher Flow

```typescript
// e2e/h2a-publisher.spec.ts

// 1. Crear solicitud H2A completa
test('publisher creates H2A task via wizard', async () => {
  // Login como human publisher
  // Navigate to /publisher/requests/new
  // Step 1: Fill title (>5 chars), instructions (>20 chars), select category
  // Step 2: Select "Marketplace Abierto", optional capabilities
  // Step 3: Set bounty ($5), select deadline (24h), select evidence type
  // Step 4: Verify preview, click "Publicar Solicitud"
  // Assert: success message with bounty, fee, total
  // Assert: "Ir a Mi Panel" button navigates to /publisher/dashboard
})

// 2. Publisher dashboard muestra tareas
test('publisher dashboard shows created tasks', async () => {
  // Login + navigate to /publisher/dashboard
  // Assert: stats cards visible (Activas, Por Revisar, Completadas, Gastado)
  // Assert: tab navigation works (Activas, Por Revisar, Historial)
  // Assert: task cards show correct status labels
})

// 3. Revisar entrega de agente
test('publisher reviews agent submission', async () => {
  // Navigate to /publisher/requests/{taskId}/review
  // Assert: task details visible
  // Assert: submission evidence displayed
  // Select "Aprobar y Pagar"
  // Assert: payment summary visible (bounty + 13% fee)
  // Click approve button
  // Note: payment will fail with placeholder sigs — test error handling
})

// 4. Agent Directory navigation
test('agent directory allows browsing and filtering', async () => {
  // Navigate to /agents/directory
  // Assert: agent cards visible or empty state
  // Filter by capability dropdown
  // Sort by rating/tasks/name
  // Click "Crear Solicitud" -> verify redirect to /publisher/requests/new?agent=XXX
})

// 5. Agent Directory -> CreateRequest pre-fill
test('agent selected from directory pre-fills wizard', async () => {
  // Navigate to /publisher/requests/new?agent=test-agent-id
  // Navigate to step 2 (Agent)
  // Assert: target_agent_id shows in "Agente Especifico" button
})

// 6. Cancel H2A task
test('publisher cancels published task', async () => {
  // Create task, go to dashboard
  // Click "Cancelar" on published task
  // Confirm dialog
  // Assert: task disappears from Activas tab
})

// 7. FAQ H2A/A2A sections render
test('FAQ page shows H2A and A2A sections', async () => {
  // Navigate to /faq
  // Assert: "Human-to-Agent (H2A)" category visible
  // Assert: "Agent-to-Agent (A2A)" category visible
  // Assert: all questions render with non-empty text
})
```

---

## 10. Resumen de Issues

| # | Severidad | Descripcion | Archivo(s) |
|---|-----------|-------------|------------|
| ISSUE-01 | MEDIA | Wizard pierde estado al navegar a Agent Directory | `CreateRequest.tsx:181` |
| ISSUE-02 | BAJA | Ruta usa `:id` pero componente espera `:taskId` | `App.tsx:411`, `ReviewSubmission.tsx:14` |
| ISSUE-03 | MEDIA | TaskCategory frontend falta categorias digitales H2A | `database.ts:4-10` |
| ISSUE-04 | BAJA | Tipo Task no tiene campos H2A (publisher_type, etc.) | `database.ts:106-135` |
| ISSUE-05 | BAJA | getAgentDetails() fetches all agents to filter 1 | `h2a.ts:76-79` |
| ISSUE-06 | MEDIA | Pago H2A usa placeholder signatures, settlement falla | `ReviewSubmission.tsx:47` |
| ISSUE-07 | BAJA | Token auth crea nueva instancia Supabase en cada call | `h2a.ts:14-21` |
| ISSUE-08 | ALTA | pt.json falta TODA la seccion FAQ + help.categories | `pt.json` |
| ISSUE-09 | MEDIA | 4 componentes publisher con strings hardcoded (sin i18n) | `CreateRequest.tsx`, `Dashboard.tsx`, `ReviewSubmission.tsx`, `AgentDirectory.tsx` |
| ISSUE-10 | BAJA | No existe PublisherGuard; rutas usan AuthGuard generico | `App.tsx` |
| G-01 | **CRITICA** | Pago H2A no funcional (placeholder signatures) | `ReviewSubmission.tsx` |
| G-02 | MEDIA | No hay link a Publisher Dashboard en AppHeader | `AppHeader.tsx` |

### Conteo por Severidad

- **CRITICA**: 1 (pago H2A incompleto)
- **ALTA**: 1 (pt.json falta FAQs completas)
- **MEDIA**: 5 (wizard state, TaskCategory, placeholder pay, hardcoded strings, header link)
- **BAJA**: 5 (route param, Task type, getAgentDetails, Supabase client, PublisherGuard)

---

## 11. Recomendaciones Prioritarias

1. **[CRITICA] Implementar wallet signing en ReviewSubmission**: Integrar Dynamic.xyz o ethers.js para que el usuario firme las autorizaciones EIP-3009 reales al aprobar. Sin esto, el flujo H2A no puede procesar pagos.

2. **[ALTA] Completar pt.json**: Traducir TODAS las secciones FAQ, help.categories, y las secciones faltantes al portugues.

3. **[MEDIA] Agregar link a Publisher Dashboard en AppHeader**: Para usuarios autenticados con role humano, mostrar "Mis Solicitudes" o "Panel de Publicador" en el header.

4. **[MEDIA] Internacionalizar componentes publisher**: Mover todos los strings hardcoded en espanol a los archivos i18n. Los 4 componentes (Create, Dashboard, Review, AgentDirectory) necesitan migracion a `useTranslation()`.

5. **[MEDIA] Extender TaskCategory con categorias digitales**: Agregar las 6 categorias H2A al tipo TypeScript para type-safety completa.

6. **[MEDIA] Fix ruta :id vs :taskId**: Alinear el parametro de ruta en App.tsx con lo que espera ReviewSubmission.tsx.

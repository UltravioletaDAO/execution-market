# EXECUTION MARKET - TODO NOW (Implementable Técnicamente HOY)

> **Fecha**: 2026-01-25
> **Versión**: 2.0.0 (CONSOLIDADO de TODO.md, TODO-1.md, TODO-2.md, TODO_MASTER.md, ARTICLE_V35)
> **Criterio**: Solo items que se pueden implementar con tecnologías DISPONIBLES
> **Excluye**: Dependencias de Colmena, Council, ChainWitness, MeshRelay, Telemesh (no están listos)
> **Total Items**: ~195

---

## ⚠️ ARCHIVO PRINCIPAL DE DESARROLLO

**ESTE ES EL ÚNICO TODO ACTIVO PARA EXECUTION MARKET.**

Los siguientes archivos están ARCHIVADOS y NO deben usarse:
- `_archive/TODO.md` - Archivo original (archivado)
- `_archive/TODO-1.md` - Primera iteración (archivado)
- `_archive/TODO-2.md` - Segunda iteración (archivado)
- `_archive/TODO_MASTER.md` - Versión master antigua (archivado)
- `TODO_FUTURE.md` - Items que dependen de proyectos no listos (Colmena, Council, etc.)

**Reglas:**
1. Todo nuevo desarrollo se trackea aquí con items `NOW-XXX`
2. Tests nuevos también tienen items `NOW-XXX` (ej: NOW-193 para tests de A2A)
3. Al completar un item, marcar `[x]` y agregar `**Status**: DONE - <descripción>`
4. Este archivo vive en `ideas/execution-market/TODO_NOW.md`

---

## TECNOLOGÍAS DISPONIBLES CONFIRMADAS

| Tecnología | Status | Uso en Execution Market |
|------------|--------|---------------|
| **x402-rs** | ✅ LIVE (19 mainnets) | Pagos, escrow, refunds |
| **ERC-8004** | ✅ Sepolia (Agent ID 469) | Identity, reputation |
| **Supabase** | ✅ Schema completo | Database, auth, storage |
| **MCP Server** | ✅ 6 tools implementados | Agent integration |
| **A2A Protocol** | ✅ MCP over WebSocket | Agent-to-agent |
| **Superfluid** | ✅ SDK disponible (Base) | Streaming payments |
| **Crossmint** | ✅ API disponible | Email wallets |
| **Magic.link** | ✅ SDK disponible | Wallet abstraction |
| **AWS/Terraform** | ✅ Configurado | Infrastructure |
| **Hardware Attestation** | ✅ Platform APIs | iOS/Android device verification |
| **Claude API** | ✅ Disponible | AI verification |
| **Gnosis Safe** | ✅ Disponible | Multisig arbitration |
| **describe.net** | ✅ Disponible | Seals integration |

---

# FASE 0: INFRAESTRUCTURA & DEPLOYMENT (P0)

## 0.1 Deployment & DevOps [NOW-001 a NOW-010]

### [ ] NOW-001 - Crear Dockerfile para MCP Server
**Prioridad**: P0
**Tech**: Docker, Python 3.11, FastAPI
**Archivos**: `mcp_server/Dockerfile` (crear)

### [ ] NOW-002 - Crear Dockerfile para Dashboard
**Prioridad**: P0
**Tech**: Docker, Node 18, Vite
**Archivos**: `dashboard/Dockerfile` (crear)

### [ ] NOW-003 - docker-compose.yml para desarrollo local
**Prioridad**: P0
**Servicios**: mcp-server, dashboard, supabase-local
**Archivos**: `docker-compose.yml` (crear)

### [ ] NOW-004 - Terraform para AWS ECS
**Prioridad**: P0
**Tech**: Terraform, AWS ECS Fargate
**Archivos**: `infrastructure/terraform/` (crear)
**Recursos**: ECS Cluster, Services, ALB, ECR, VPC

### [ ] NOW-005 - GitHub Actions CI/CD
**Prioridad**: P0
**Archivos**: `.github/workflows/deploy.yml` (crear)
**Steps**: Test → Build → Push ECR → Deploy ECS

### [ ] NOW-006 - Configurar dominio execution.market
**Prioridad**: P0
**Tech**: Route53, ACM (SSL)
**Subdomains**: api., app.

### [ ] NOW-007 - Mover secrets a AWS Secrets Manager
**Prioridad**: P0 (SECURITY)
**Secrets**: SUPABASE_SERVICE_KEY, X402_PRIVATE_KEY, PINATA_JWT

### [ ] NOW-008 - Aplicar migrations a Supabase production
**Prioridad**: P0
**Archivos**: `supabase/migrations/001-004.sql`

### [x] NOW-009 - Crear RPC functions en Supabase
**Prioridad**: P0
**Functions**: get_or_create_executor, link_wallet_to_session
**Status**: DONE - Migration 009 with full RPC functions:
- `get_or_create_executor`: Get/create executor with tier calculation
- `link_wallet_to_session_v2`: Enhanced wallet linking
- `get_nearby_tasks`: PostGIS-based location search
- `update_executor_reputation`: Bayesian average with decay
- `get_executor_stats`, `get_executor_tasks`: Statistics queries
- `claim_task`, `abandon_task`: Task lifecycle management
- Edge Function wrapper at `functions/executor-management/`
**Archivos**: `supabase/migrations/009_executor_rpc_functions.sql`, `supabase/functions/`

### [ ] NOW-010 - Configurar Supabase Storage bucket 'evidence'
**Prioridad**: P0
**Config**: 50MB max, JPEG/PNG/MP4/PDF

## 0.2 Puertos y Networking (Referencia)

> **DOCUMENTACIÓN**: Puertos configurados en Terraform para AWS

**Load Balancer (ALB):**
- Puerto 80 (HTTP) → Redirect a 443
- Puerto 443 (HTTPS) → Default al Dashboard

**Routing Rules:**
- `api.execution.market` → MCP Server (puerto 8000)
- `execution.market` (default) → Dashboard (puerto 80)

**ECS Tasks (internos, solo desde ALB):**
- MCP Server: puerto 8000 (`/health` endpoint)
- Dashboard: puerto 80 (`/health` endpoint)

**Security Groups:**
- ALB SG: Permite 80, 443 desde 0.0.0.0/0
- ECS SG: Permite 8000, 80 SOLO desde ALB SG

**Archivos Terraform:**
- `infrastructure/terraform/alb.tf` - Load balancer, listeners, target groups
- `infrastructure/terraform/ecs.tf` - Task definitions, services, security groups
- `infrastructure/terraform/vpc.tf` - VPC, subnets

---

# FASE 1: MCP SERVER COMPLETO (P0-P1)

## 1.1 Worker Tools (Faltan) [NOW-011 a NOW-014]

### [ ] NOW-011 - Implementar em_apply_to_task
**Prioridad**: P0
**Archivo**: `mcp_server/server.py`
**Params**: task_id, executor_id, message

### [ ] NOW-012 - Implementar em_submit_work
**Prioridad**: P0
**Archivo**: `mcp_server/server.py`
**Params**: task_id, executor_id, evidence (JSON)

### [ ] NOW-013 - Implementar em_get_my_tasks
**Prioridad**: P0
**Archivo**: `mcp_server/server.py`
**Params**: executor_id, status_filter

### [ ] NOW-014 - Implementar em_withdraw_earnings
**Prioridad**: P1
**Dependencias**: x402 integration

## 1.2 Agent Tools (Mejoras) [NOW-015 a NOW-018]

### [ ] NOW-015 - Implementar em_assign_task
**Prioridad**: P0
**Archivo**: `mcp_server/server.py`

### [ ] NOW-016 - Mejorar em_publish_task con escrow
**Prioridad**: P1
**Dependencias**: x402-rs SDK

### [ ] NOW-017 - Implementar em_batch_create_tasks
**Prioridad**: P2
**Descripción**: Crear múltiples tareas en una llamada

### [ ] NOW-018 - Implementar em_get_task_analytics
**Prioridad**: P2
**Descripción**: Métricas de tasks por agent

---

# FASE 2: X402 INTEGRATION (P0-P1)

## 2.1 Escrow & Payments [NOW-019 a NOW-028]

### [ ] NOW-019 - Registrar Execution Market como merchant en x402r
**Prioridad**: P0
**Contract**: MerchantRouter `0xa48E8AdcA504D2f48e5AF6be49039354e922913F`
**Network**: Base Mainnet

### [ ] NOW-020 - Deploy relay proxy via DepositRelayFactory
**Prioridad**: P0
**Contract**: `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814`

### [ ] NOW-021 - Implementar escrow deposit en publish_task
**Prioridad**: P1
**Archivo**: `mcp_server/integrations/x402/escrow.py` (crear)

### [ ] NOW-022 - Implementar escrow release en approve_submission
**Prioridad**: P1

### [ ] NOW-023 - Implementar refund en cancel_task
**Prioridad**: P1

### [ ] NOW-024 - x402 SDK client para Python
**Prioridad**: P0
**Archivo**: `mcp_server/integrations/x402/client.py` (crear)

### [ ] NOW-025 - Implementar platform fee (6-8%)
**Prioridad**: P1
**Config**: Variable por task_type

### [ ] NOW-026 - Fee collection en release
**Prioridad**: P1
**Flow**: bounty → 92% worker + 8% treasury

### [ ] NOW-027 - Multi-token support
**Prioridad**: P2
**Tokens**: USDC, EURC, DAI, USDT

### [ ] NOW-028 - Token preference por worker
**Prioridad**: P2

---

# FASE 3: DASHBOARD COMPLETO (P1)

## 3.1 Páginas Faltantes [NOW-029 a NOW-040]

### [ ] NOW-029 - Crear Profile.tsx
**Prioridad**: P1
**Features**: Bayesian score, task history, earnings, settings
**Archivo**: `dashboard/src/pages/Profile.tsx`

### [ ] NOW-030 - Crear PaymentStatus.tsx
**Prioridad**: P1
**Features**: Escrow status, partial vs final, tx hashes

### [ ] NOW-031 - Crear EarningsPanel.tsx
**Prioridad**: P1
**Features**: Total earned, pending, history

### [ ] NOW-032 - Crear NotificationBell.tsx
**Prioridad**: P2
**Features**: New tasks, approvals, payments

### [ ] NOW-033 - Crear Disputes.tsx
**Prioridad**: P1
**Features**: Evidence viewer, timeline, voting, appeal button

### [ ] NOW-034 - Crear AgentDashboard.tsx
**Prioridad**: P2
**Features**: Task management, submission review, analytics

### [ ] NOW-035 - Crear ValidatorPanel.tsx
**Prioridad**: P2
**Features**: Queue de disputas, voting interface

### [ ] NOW-036 - Crear Analytics.tsx
**Prioridad**: P2
**Features**: GMV, completion rates, regional stats

### [ ] NOW-037 - Crear TaxReports.tsx
**Prioridad**: P3
**Features**: Export de earnings por período

### [ ] NOW-038 - Crear MyStake.tsx
**Prioridad**: P2
**Features**: Stake disponible, locked, slashing history

### [ ] NOW-039 - Crear IncomeEstimator.tsx
**Prioridad**: P1
**Features**: Income realista por región/hora

### [ ] NOW-040 - Crear LocationFilter.tsx
**Prioridad**: P1
**Features**: Slider "Show tasks within X km"

## 3.2 Auth & Wallet [NOW-041 a NOW-045]

### [ ] NOW-041 - Implementar Wagmi wallet connection REAL
**Prioridad**: P1
**Fix**: Conectar AuthModal con useConnect/useAccount

### [ ] NOW-042 - Integrar Crossmint para email wallets
**Prioridad**: P1
**SDK**: `@crossmint/wallets-sdk`

### [ ] NOW-043 - Integrar Magic.link como fallback
**Prioridad**: P2

### [ ] NOW-044 - Wallet selector unificado
**Prioridad**: P1
**Features**: Email wallet, MetaMask, WalletConnect

### [ ] NOW-045 - Completar i18n (eliminar hardcoded strings)
**Prioridad**: P2

## 3.3 Dashboard Login Flow [NOW-188 a NOW-192] (NUEVO)

> **NOTA**: Actualmente el dashboard solo muestra landing page.
> NO hay flujo de login para workers ni agents.
> El `api/auth.py` solo maneja API keys para llamadas al MCP server.

### [ ] NOW-188 - Crear Login/Landing separation
**Prioridad**: P0
**Problema**: Dashboard muestra landing pero no hay forma de entrar
**Solución**: Botón "Enter App" → Modal de conexión wallet
**Archivos**: `dashboard/src/pages/Landing.tsx`, `dashboard/src/App.tsx`

### [ ] NOW-189 - Crear Worker Login flow
**Prioridad**: P0
**Flow**: Connect Wallet → Supabase session → View available tasks
**Auth**: Wallet signature → JWT token
**Archivo**: `dashboard/src/components/WorkerAuth.tsx`

### [ ] NOW-190 - Crear Agent Login flow
**Prioridad**: P1
**Flow**: API Key input → Validate → Show Agent Dashboard
**Auth**: API key validation via `api/auth.py`
**Archivo**: `dashboard/src/components/AgentAuth.tsx`

### [ ] NOW-191 - Crear session management
**Prioridad**: P1
**Features**: JWT storage, auto-refresh, logout
**Tech**: Supabase Auth + custom JWT for wallet-based auth

### [ ] NOW-192 - Protected routes
**Prioridad**: P1
**Routes**: `/tasks`, `/profile`, `/earnings` require auth
**Public**: `/`, `/about`, `/faq`

## 3.4 Evidence Upload [NOW-046 a NOW-048]

### [ ] NOW-046 - Evidence upload flow completo
**Prioridad**: P1
**Features**: Camera capture, EXIF extraction, upload to Supabase

### [ ] NOW-047 - Photo source validation (camera only)
**Prioridad**: P1
**Check**: EXIF source debe ser 'camera', no 'gallery'

### [ ] NOW-048 - Mobile-responsive layout + PWA manifest
**Prioridad**: P1

---

# FASE 4: ERC-8004 REPUTATION (P1)

## 4.1 Identity [NOW-049 a NOW-052]

### [ ] NOW-049 - Worker registration en ERC-8004
**Prioridad**: P1
**Network**: Sepolia (testnet)
**Archivo**: `mcp_server/integrations/erc8004/register.py`

### [ ] NOW-050 - Query ERC-8004 reputation en get_tasks
**Prioridad**: P1

### [ ] NOW-051 - Raw reputation score storage on-chain
**Prioridad**: P1
**Schema**: (rater, ratee, score, task_id, task_value, timestamp)

### [ ] NOW-052 - Reputation events emission
**Prioridad**: P1
**Events**: `ReputationUpdated(executor_id, rater, score, task_value)`

## 4.2 Bayesian Scoring [NOW-053 a NOW-060]

### [ ] NOW-053 - Implementar Bayesian Average calculation
**Prioridad**: P0
**Formula**: Score = (C × m + Σ(ratings × weight)) / (C + Σ weights)
**Params**: C=15-20, m=50, weight=log(bounty+1), decay=0.9^months
**Archivo**: `mcp_server/reputation/bayesian.py`

### [ ] NOW-054 - Task-value weighting
**Prioridad**: P1
**Formula**: weight = log(bounty_usd + 1)

### [ ] NOW-055 - Reputation decay over time
**Prioridad**: P2
**Formula**: decay = 0.9^(months_old)

### [ ] NOW-056 - Bayesian score caching
**Prioridad**: P2
**Tech**: PostgreSQL materialized view o Redis
**TTL**: 5-15 minutos

### [ ] NOW-057 - Bayesian API endpoint
**Prioridad**: P1
**Endpoints**: GET /api/reputation/{executor_id}

### [ ] NOW-058 - Bidirectional Bayesian (agents too)
**Prioridad**: P1
**Descripción**: Agents también reciben Bayesian scores

### [ ] NOW-059 - Skill-specific reputation
**Prioridad**: P2
**Descripción**: Score separado por tipo de tarea

### [ ] NOW-060 - Reputation-based task matching
**Prioridad**: P1
**Descripción**: Priorizar workers con mejor score

---

# FASE 5: VERIFICATION (P1-P2)

## 5.1 Auto-Verification [NOW-061 a NOW-068]

### [ ] NOW-061 - GPS validation
**Prioridad**: P1
**Check**: Photo GPS coords dentro de task radius
**Archivo**: `mcp_server/verification/checks/gps.py`

### [ ] NOW-062 - Timestamp validation
**Prioridad**: P1
**Config**: photo_max_age_minutes: 5

### [ ] NOW-063 - Duplicate photo detection
**Prioridad**: P1
**Tech**: Perceptual hash (imagehash)

### [ ] NOW-064 - Evidence schema validation
**Prioridad**: P1
**Check**: Submitted evidence matches task.evidence_required

### [ ] NOW-065 - Gallery upload prohibition
**Prioridad**: P0
**Check**: SOLO permitir fotos de cámara live

### [ ] NOW-066 - Photo freshness verification
**Prioridad**: P1
**Check**: Foto tomada dentro de últimos 5 minutos

### [ ] NOW-067 - Evidence tampering detection
**Prioridad**: P1
**Checks**: EXIF software tags, compression artifacts, ELA

### [ ] NOW-068 - GenAI photo detection
**Prioridad**: P1
**Descripción**: Detectar fotos generadas por Midjourney/DALL-E/Flux

## 5.2 AI Review [NOW-069 a NOW-075]

### [ ] NOW-069 - Claude Vision verification
**Prioridad**: P1
**Tech**: Anthropic API (claude-sonnet-4-20250514)
**Archivo**: `mcp_server/verification/ai_review.py`

### [ ] NOW-070 - Verification tier routing
**Prioridad**: P1
**Rules**: 0.95+ auto, 0.70+ AI, 0.50+ Agent, <0.50 Human

### [ ] NOW-071 - Specialized prompts por task_type
**Prioridad**: P2

### [ ] NOW-072 - Verification explanation
**Prioridad**: P2
**Descripción**: AI explica por qué aprobó/rechazó

### [ ] NOW-073 - OCR for text verification
**Prioridad**: P2
**Descripción**: Leer texto en fotos (recibos, documentos)

### [ ] NOW-074 - Multi-model verification
**Prioridad**: P2
**Models**: Claude + GPT-4V consensus

### [ ] NOW-075 - Verification audit log
**Prioridad**: P1
**Tabla**: verification_log

## 5.3 Hardware Attestation [NOW-076 a NOW-082]

### [ ] NOW-076 - Secure Enclave photo signing (iOS)
**Prioridad**: P1
**API**: CryptoKit

### [ ] NOW-077 - StrongBox attestation (Android)
**Prioridad**: P1
**API**: Android Keystore

### [ ] NOW-078 - Device attestation API
**Prioridad**: P1
**iOS**: App Attest
**Android**: Play Integrity API

### [ ] NOW-079 - Photo metadata preservation
**Prioridad**: P1
**Descripción**: No strip EXIF

### [ ] NOW-080 - Attestation verification backend
**Prioridad**: P1
**Archivo**: `mcp_server/verification/attestation.py`

### [ ] NOW-081 - Device fingerprinting anti-fraud
**Prioridad**: P1
**Descripción**: Detectar si mismo device usado por múltiples workers

### [ ] NOW-082 - Attestation requirement por task_type
**Prioridad**: P2
**Rules**: >$50 required, >$20 recommended

---

# FASE 6: A2A PROTOCOL & AGENT INTEGRATION (P1-P2)

## 6.1 Agent Card [NOW-083 a NOW-085]

### [x] NOW-083 - Publicar Agent Card actualizado
**Prioridad**: P1
**URL**: `https://api.execution.market/.well-known/agent.json`
**Status**: DONE - Full A2A Agent Card implementation in `mcp_server/a2a/agent_card.py`:
- AgentCard dataclass with A2A Protocol 0.3.0 compliance
- 7 skills defined: publish-task, manage-tasks, review-submissions, worker-management, batch-operations, analytics, payments
- 3 transports: JSONRPC, WebSocket, HTTP+JSON
- 3 auth schemes: bearer (JWT), apiKey, erc8004
- FastAPI router with endpoints: `/.well-known/agent.json`, `/v1/card`, `/discovery/agents`
- Tests in `tests/test_a2a.py` (47 test cases)

### [x] NOW-084 - Agent discovery endpoint
**Prioridad**: P2
**Endpoint**: GET /discovery/agents
**Status**: DONE - Implemented in `mcp_server/a2a/agent_card.py`

### [ ] NOW-085 - Execution Market as Agent Cloud Member
**Prioridad**: P1
**Descripción**: Deploy Execution Market como agent que otros agents llaman

## 6.2 MCP & Webhooks [NOW-086 a NOW-090]

### [x] NOW-086 - WebSocket server para MCP
**Prioridad**: P2
**Tech**: FastAPI WebSocket
**Archivo**: `mcp_server/websocket.py`
**Status**: DONE - Full WebSocket server implementation:
- `WebSocketManager`: Connection lifecycle, heartbeat, subscriptions
- `WebSocketMessage`: 23 message types for all task/submission/payment events
- `TaskNotifier`: Helper for broadcasting task-related notifications
- Routes: `/ws` (WebSocket endpoint), `/ws/stats` (statistics)
- Authentication via API key or JWT
- Topic-based subscriptions for targeted broadcasts
- Tests in `tests/test_websocket.py`

### [x] NOW-087 - Webhook notification payloads
**Prioridad**: P1
**Events**: task_created, task_assigned, submission_received, payment_completed
**Status**: DONE - Full webhook system in `mcp_server/webhooks/`:
- `events.py`: 25+ event types with typed payloads
- `sender.py`: Delivery with exponential backoff retries + HMAC-SHA256 signatures
- `registry.py`: Endpoint registration, auto-disable on failures
- Tests in `tests/test_webhooks.py`

### [ ] NOW-088 - Integration guide Zapier
**Prioridad**: P1

### [ ] NOW-089 - Integration guide n8n
**Prioridad**: P1

### [ ] NOW-090 - Integration guide CrewAI/LangChain
**Prioridad**: P1

---

# FASE 7: WORKER PROTECTION (P1-P2)

## 7.1 Partial Payouts [NOW-091 a NOW-095]

### [ ] NOW-091 - Partial payout on submission
**Prioridad**: P1
**Config**: 30-50% del bounty al subir evidence
**Archivo**: `mcp_server/payments/partial_release.py`

### [ ] NOW-092 - Escrow split tracking
**Prioridad**: P1
**Columns**: partial_released, partial_amount

### [ ] NOW-093 - Partial payout UI en dashboard
**Prioridad**: P1

### [ ] NOW-094 - Partial rollback en rejection válida
**Prioridad**: P2

### [ ] NOW-095 - Partial completion scenarios
**Prioridad**: P1
**Rules**: 0-30% no pago, 30-70% proof of attempt, 70-90% prorated

## 7.2 Agent Bond & Protection [NOW-096 a NOW-102]

### [ ] NOW-096 - Agent bond mechanism
**Prioridad**: P1
**Config**: bounty + 10-20% extra como bond
**Archivo**: `mcp_server/payments/agent_bond.py`

### [ ] NOW-097 - Proof of attempt payout
**Prioridad**: P1
**Config**: 10-20% por intento válido aunque falle

### [ ] NOW-098 - Minimum net payout validation
**Prioridad**: P1
**Config**: $0.50 minimum después de fees

### [ ] NOW-099 - Minimum payout by task_type
**Prioridad**: P1
**Examples**: simple $0.50, physical $1.00, authority $5.00

### [ ] NOW-100 - Worker Protection Fund pool setup
**Prioridad**: P1
**Funding**: 0.5% de cada fee + slashed bonds

### [ ] NOW-101 - Fund claim process
**Prioridad**: P1
**Limits**: Max $50/claim, $200/month/worker

### [ ] NOW-102 - Auto-pause high-risk agents
**Prioridad**: P2
**Threshold**: >30% rejection rate

---

# FASE 8: SUPERFLUID STREAMING (P2)

### [ ] NOW-103 - Superfluid SDK integration
**Prioridad**: P2
**SDK**: `@superfluid-finance/sdk-core`
**Archivo**: `mcp_server/integrations/superfluid/`

### [ ] NOW-104 - Stream creation para long tasks
**Prioridad**: P2
**Rate**: $18/hr = $0.005/segundo

### [ ] NOW-105 - Stream pause/resume
**Prioridad**: P2

### [ ] NOW-106 - Stream monitoring dashboard
**Prioridad**: P2

### [ ] NOW-107 - Live verification + streaming
**Prioridad**: P2
**Descripción**: Verificación continua durante stream

---

# FASE 9: FRAUD PREVENTION (P1)

### [ ] NOW-108 - GPS spoofing detection
**Prioridad**: P1
**Methods**: Network triangulation, movement patterns, sensor fusion
**Archivo**: `mcp_server/verification/gps_antispoofing.py`

### [x] NOW-109 - Multi-device detection
**Prioridad**: P1
**Descripción**: Detectar mismo worker usando múltiples devices
**Status**: DONE - FraudDetector.check_multi_device() in `mcp_server/security/fraud_detection.py`
- Detects workers using >3 devices (MULTI_DEVICE signal, HIGH risk)
- Detects rapid device switching (DEVICE_SPOOFING signal, MEDIUM risk)
- Detects device farms - same device used by multiple workers (DEVICE_FARM signal, CRITICAL risk)

### [x] NOW-110 - Wash trading detection
**Prioridad**: P1
**Signals**: Same IP para agent/worker, instant approvals, inflated bounties
**Status**: DONE - FraudDetector.check_wash_trading() in `mcp_server/security/fraud_detection.py`
- SAME_IP_AGENT_WORKER: Agent and worker on same IP (CRITICAL risk)
- INSTANT_APPROVAL: Approval <30s indicates no real review (HIGH/MEDIUM risk)
- INFLATED_BOUNTY: Bounty >3x average for task type (HIGH risk)
- RAPID_COMPLETION: Task completed <5min (MEDIUM risk)
- Additional: check_collusion() for repeated pairings, wallet clustering, circular payments

### [ ] NOW-111 - Rate limits por IP/device
**Prioridad**: P1
**Limits**: 50 tasks/día/IP, 20/device

### [x] NOW-112 - Safety pre-investigation
**Prioridad**: P2
**Checks**: Crime data, time of day risk, private property
**Status**: DONE - SafetyInvestigator in `mcp_server/safety/investigation.py`
- Assesses location safety with multiple risk factors (crime, time, property, weather, accessibility)
- Time-of-day risk with area-specific multipliers (industrial, residential, etc.)
- Private property detection with access requirements
- Incident history tracking for pattern analysis
- Generates actionable safety recommendations
- Assessment caching with TTL for efficiency

### [x] NOW-113 - Hostile meatspace protocol
**Prioridad**: P2
**Protocol**: Safety score, proof of attempt for obstacles
**Status**: DONE - HostileProtocolManager in `mcp_server/safety/hostile_protocol.py`
- 10 obstacle types: ACCESS_DENIED, HOSTILE_ENVIRONMENT, UNSAFE_CONDITIONS, etc.
- Proof of attempt validation with evidence requirements per obstacle type
- Compensation calculation (10-30% of bounty based on obstacle type)
- Auto-verification for high-confidence claims
- Rate limiting (5 reports/day/worker) to prevent abuse
- Safety score calculation using historical obstacle data
- Tests in `tests/test_safety.py`

---

# FASE 10: DYNAMIC BOUNTY & PRICING (P2)

### [ ] NOW-114 - Bounty escalation config
**Prioridad**: P2
**Config**: initial, rate 15%, interval 2hr, max 3x

### [ ] NOW-115 - Bounty escalation job
**Prioridad**: P2
**Archivo**: `mcp_server/jobs/escalate_bounties.py`

### [ ] NOW-116 - Urgency multiplier
**Prioridad**: P2
**Config**: 1.5x <2hr, 2x <30min

### [ ] NOW-117 - Location premium
**Prioridad**: P2
**Config**: Rural > Urban

### [ ] NOW-118 - Surge pricing durante picos
**Prioridad**: P2

### [ ] NOW-119 - Bid/offer system opcional
**Prioridad**: P2
**Descripción**: Workers pueden ofertar menos

### [ ] NOW-120 - Price analytics por zona
**Prioridad**: P2

### [ ] NOW-121 - Agent price recommendations
**Prioridad**: P2

---

# FASE 11: ARBITRATION & DISPUTES (P1-P2)

### [ ] NOW-122 - Safe Pool arbitration setup
**Prioridad**: P2
**Descripción**: Gnosis Safe con 3+ validators

### [ ] NOW-123 - Validator selection criteria
**Prioridad**: P2
**Requisitos**: >100 tareas, rating >4.5, staked

### [ ] NOW-124 - Validator staking
**Prioridad**: P2

### [ ] NOW-125 - Dispute routing to Safe Pool
**Prioridad**: P2
**Archivo**: `mcp_server/disputes/router.py`

### [ ] NOW-126 - Validator voting interface
**Prioridad**: P2
**Archivo**: `dashboard/src/pages/ValidatorDashboard.tsx`

### [ ] NOW-127 - Validator compensation
**Prioridad**: P2
**Config**: % del dispute amount

### [ ] NOW-128 - Validator Rotation Mechanism
**Prioridad**: P2
**Descripción**: Rotación sin redeploying contracts

### [ ] NOW-129 - Context tags para ratings
**Prioridad**: P2
**Tags**: delayed-traffic, weather-issue, access-denied, tech-failure

### [ ] NOW-130 - Rating appeal mechanism
**Prioridad**: P2

---

# FASE 12: TASK TYPES & CONCEPTS (P1-P2)

### [ ] NOW-131 - Task type tiers definition
**Prioridad**: P0
**Tiers**: Tier 1 $1-5, Tier 2 $10-30, Tier 3 $50-500

### [ ] NOW-132 - Execution Market Recon (observation tasks)
**Prioridad**: P1
**Archivo**: `mcp_server/task_types/recon.py`
**Examples**: "Is store open?", "How many in line?"

### [ ] NOW-133 - Execution Market Trials (experience testing)
**Prioridad**: P2
**Descripción**: Visit restaurant, test product, report

### [ ] NOW-134 - Last Mile as a Service
**Prioridad**: P2
**Descripción**: Agents coordinate last-mile delivery

### [ ] NOW-135 - Execution Market Prime (premium tier)
**Prioridad**: P2
**Features**: Background checked, insured, SLA

### [ ] NOW-136 - Gamified progression system
**Prioridad**: P2
**Levels**: Novice → Expert → Master

### [ ] NOW-137 - Task bundling
**Prioridad**: P2
**Config**: 5-10 similar tasks en zone

### [ ] NOW-138 - Bundle completion bonus
**Prioridad**: P2
**Example**: 10% bonus por completar bundle

### [ ] NOW-139 - Cascading Tasks
**Prioridad**: P2
**Descripción**: Task completion triggers child tasks

### [ ] NOW-140 - Task Insurance tiers
**Prioridad**: P2
**Tiers**: Basic 5%, Standard 10%, Premium 20%

---

# FASE 13: BOOTSTRAP & ADOPTION (P0-P1)

### [ ] NOW-141 - POAP/Crypto community bootstrap
**Prioridad**: P0
**Target**: POAP collectors, STEPN users, crypto meetups

### [ ] NOW-142 - Initial task injection by DAO
**Prioridad**: P0
**Budget**: $1,000-$5,000 for first month

### [ ] NOW-143 - Enterprise overflow to public pool
**Prioridad**: P1

### [ ] NOW-144 - Referral system for workers
**Prioridad**: P1
**Bonus**: $1-2 per referral que completa 5 tareas

### [ ] NOW-145 - Agent dev kit gratuito
**Prioridad**: P1
**Archivo**: `sdk/agent-starter-kit/`

### [ ] NOW-146 - Pilot programs con empresas
**Prioridad**: P1
**Targets**: Logistics, retail, market research

### [ ] NOW-147 - Miami/LATAM hub focus
**Prioridad**: P0
**Locations**: Miami, Medellín, Lagos

### [ ] NOW-148 - Side-hustle framing en docs
**Prioridad**: P1
**Message**: Extra income $5-15/día, no full-time replacement

### [ ] NOW-149 - Transition messaging
**Prioridad**: P1
**Message**: Humanos hoy → Hybrids → Robots después

### [ ] NOW-150 - Comparison vs competitors table
**Prioridad**: P1
**Metrics**: Fees 6-8% vs 20-23%, instant vs days

---

# FASE 14: LANDING & MARKETING (P1-P2)

### [ ] NOW-151 - Landing page funcional
**Prioridad**: P1
**URL**: execution.market

### [ ] NOW-152 - Unificar pricing a $0.50 min
**Prioridad**: P1
**Fix**: Landing dice $0.25, debe ser $0.50

### [ ] NOW-153 - Remover claims de features no implementadas
**Prioridad**: P1

### [ ] NOW-154 - 8-week launch sequence
**Prioridad**: P0
**Archivo**: `docs/LAUNCH_PLAN.md`

### [ ] NOW-155 - Tech stack recommendation doc
**Prioridad**: P0
**Archivo**: `docs/TECH_STACK.md`

### [x] NOW-156 - Staircase Manifesto
**Prioridad**: P1
**Archivo**: `docs/MANIFESTO.md`
**Completado**: 2026-01-25

---

# FASE 15: ENTERPRISE (P0-P2)

### [ ] NOW-157 - Flexible Reward Types
**Prioridad**: P0
**Types**: points, x402, token, none, custom
**Archivo**: `mcp_server/rewards/`

### [ ] NOW-158 - Enterprise Configuration System
**Prioridad**: P0
**Archivo**: `mcp_server/enterprise/config.py`

### [ ] NOW-159 - Enterprise onboarding flow
**Prioridad**: P2

### [ ] NOW-160 - Custom branding (white-label)
**Prioridad**: P2

### [ ] NOW-161 - Role-based access (admin, manager, viewer)
**Prioridad**: P2

### [ ] NOW-162 - Budget management
**Prioridad**: P2

### [ ] NOW-163 - Approval workflows
**Prioridad**: P2

### [ ] NOW-164 - Bulk task creation (CSV upload)
**Prioridad**: P2

### [ ] NOW-165 - API rate limits tiers
**Prioridad**: P2

---

# FASE 16: DESCRIBE.NET INTEGRATION (P1)

### [ ] NOW-166 - describe.net worker seals integration
**Prioridad**: P1
**Seals**: SKILLFUL, RELIABLE, THOROUGH, ON_TIME

### [ ] NOW-167 - describe.net requester seals integration
**Prioridad**: P1
**Seals**: FAIR_EVALUATOR, CLEAR_INSTRUCTIONS, FAST_PAYMENT

### [ ] NOW-168 - MASTER_WORKER fusion badge
**Prioridad**: P2
**Requisitos**: 50+ tasks, 6+ months

### [ ] NOW-169 - Worker-side filtering by requester reputation
**Prioridad**: P1

### [ ] NOW-170 - Bidirectional value flow
**Prioridad**: P1
**Flow**: Execution Market completions → describe.net seals → Execution Market matching

---

# FASE 17: NETWORK & RESILIENCE (P1)

### [ ] NOW-171 - Network connectivity handling
**Prioridad**: P1
**Grace period**: 30 minutos para reconexión

### [ ] NOW-172 - Submission timeout handling
**Prioridad**: P1
**Config**: submission_timeout_hours: 4

### [ ] NOW-173 - Push notifications integration
**Prioridad**: P1
**Methods**: Firebase Cloud Messaging, OneSignal

---

# FASE 18: WORKER EXPERIENCE (P1-P2)

### [ ] NOW-174 - Probation tier for new workers
**Prioridad**: P1
**Rules**: Primeros 10 tasks, max $5, extra verification

### [ ] NOW-175 - Reputation recovery path
**Prioridad**: P2
**Path**: 30-day cooloff, re-verify, probation tier

### [ ] NOW-176 - Worker mentorship program
**Prioridad**: P2

### [ ] NOW-177 - Accessibility accommodations
**Prioridad**: P2
**Features**: Voice-only, extended time, simplified UI

### [ ] NOW-178 - Night/weekend premiums
**Prioridad**: P2
**Config**: Weekends +15%, Nights +25%, Holidays +50%

### [ ] NOW-179 - Worker Categorization System
**Prioridad**: P1
**Filtros**: Expertise, geography, modality, age, equipment

---

# FASE 19: VALIDATOR SYSTEM (P1-P2)

### [x] NOW-180 - Validator Consensus System (2-of-3 + Safe)
**Prioridad**: P1
**Archivo**: `mcp_server/validation/consensus.py`
**Status**: DONE - ConsensusManager con 2-of-3 consensus, Safe fallback, ValidatorPool

### [x] NOW-181 - Validator specialization
**Prioridad**: P2
**Types**: Photography, document, technical
**Status**: DONE - ValidatorSpecialization enum + determine_specialization_from_task_type()

### [x] NOW-182 - Validator payment
**Prioridad**: P2
**Config**: 5-10% of task bounty split
**Status**: DONE - _calculate_fee_percentage() + distribute_payments()

---

# FASE 20: SEALS & CREDENTIALS (P2)

### [ ] NOW-183 - SealRegistry contract
**Prioridad**: P2
**Types**: SKILL, WORK, BEHAVIOR

### [ ] NOW-184 - SKILL seals
**Prioridad**: P2
**Example**: "Verificado: Fotografía profesional"

### [ ] NOW-185 - WORK seals
**Prioridad**: P2
**Example**: "100+ deliveries completados"

### [ ] NOW-186 - Seal display en perfil
**Prioridad**: P2

### [ ] NOW-187 - Seal requirements config
**Prioridad**: P2

---

# FASE 21: TESTS & QUALITY (P1)

> Tests son ciudadanos de primera clase. Cada módulo nuevo necesita tests.

## 21.1 Tests de Módulos Core [NOW-193 a NOW-200]

### [x] NOW-193 - Tests para A2A Agent Card
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_a2a.py`
**Status**: DONE - 47 test cases covering:
- Enum tests (TransportType, SecurityType, InputOutputMode)
- Data class serialization (AgentProvider, AgentCapabilities, AgentSkill, AgentInterface, SecurityScheme)
- AgentCard generation and JSON round-trips
- get_em_skills() validation
- get_agent_card() with custom/env URLs
- FastAPI router endpoints (/.well-known/agent.json, /v1/card, /discovery/agents)
- A2A Protocol compliance checks

### [x] NOW-194 - Tests para Bayesian Reputation
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_reputation.py`
**Status**: DONE - Tests for BayesianCalculator, Rating, calculate_bayesian_score

### [x] NOW-195 - Tests para GPS Anti-Spoofing
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_gps_antispoofing.py`
**Status**: DONE - Movement patterns, sensor consistency, multi-device, rate limits

### [x] NOW-196 - Tests para Fraud Detection
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_fraud_detection.py`
**Status**: DONE - Collusion, wash trading, wallet clustering

### [x] NOW-197 - Tests para Safety Investigation
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_safety.py`
**Status**: DONE - Safety assessment, hostile protocol, obstacle reporting

### [ ] NOW-198 - Tests para x402 Escrow
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_escrow.py` (crear)
**Coverage**: deposit, release, refund, partial_release

### [ ] NOW-199 - Tests para MCP Server Tools
**Prioridad**: P1
**Archivo**: `mcp_server/tests/test_mcp_tools.py` (crear)
**Coverage**: publish_task, get_tasks, approve_submission, apply_to_task

### [ ] NOW-200 - Tests para WebSocket Server
**Prioridad**: P2
**Archivo**: `mcp_server/tests/test_websocket.py` (verificar coverage)
**Coverage**: Connection, subscriptions, broadcasts

## 21.2 Tests de Integración [NOW-201 a NOW-205]

### [ ] NOW-201 - Test E2E: Task lifecycle completo
**Prioridad**: P1
**Flow**: publish → apply → assign → submit → approve → pay
**Archivo**: `mcp_server/tests/e2e/test_task_lifecycle.py`

### [ ] NOW-202 - Test E2E: Dispute flow
**Prioridad**: P2
**Flow**: submit → reject → dispute → validator vote → resolution

### [ ] NOW-203 - Test E2E: Streaming payment
**Prioridad**: P2
**Flow**: start_stream → verify → stop_stream

### [ ] NOW-204 - Test de carga: Rate limits
**Prioridad**: P2
**Config**: 100 requests/segundo, verificar rate limiting

### [ ] NOW-205 - Test de carga: WebSocket connections
**Prioridad**: P2
**Config**: 1000 conexiones simultáneas

---

# RESUMEN

## Por Prioridad
| Prioridad | Items | Descripción |
|-----------|-------|-------------|
| P0 | ~27 | Deployment, DB, x402, Bayesian, Bootstrap, Launch, Dashboard Login |
| P1 | ~95 | MCP tools, Dashboard, Verification, ERC-8004, Protection, Tests |
| P2 | ~70 | Streaming, Advanced features, Enterprise, Load tests |
| P3 | ~8 | Nice-to-have |
| **Total** | **~200** | Implementable técnicamente HOY |

## Tests Status
| Módulo | Status | Tests |
|--------|--------|-------|
| A2A Agent Card | ✅ DONE | 47 tests |
| Bayesian Reputation | ✅ DONE | 21 tests |
| GPS Anti-Spoofing | ✅ DONE | 25 tests |
| Fraud Detection | ✅ DONE | 30+ tests |
| Safety Investigation | ✅ DONE | 35+ tests |
| x402 Escrow | ❌ TODO | NOW-198 |
| MCP Server Tools | ❌ TODO | NOW-199 |
| WebSocket Server | ⚠️ Partial | NOW-200 |
| E2E Task Lifecycle | ❌ TODO | NOW-201 |
| **Total Tests** | **360 passing** | Run: `pytest tests/` |

## Tecnologías Usadas (100% Disponibles)
- x402-rs (pagos, escrow, refunds)
- Supabase (DB + Auth + Storage)
- ERC-8004 (identity, reputation)
- Superfluid (streaming)
- Crossmint/Magic.link (email wallets)
- AWS ECS + Terraform
- Claude API (AI verification)
- Gnosis Safe (arbitration)
- describe.net (seals)
- FastAPI + MCP SDK

---

*Este TODO solo incluye items implementables con tecnologías disponibles HOY.*
*Para items que dependen de Colmena, Council, ChainWitness, MeshRelay, Telemesh, ver TODO_FUTURE.md*

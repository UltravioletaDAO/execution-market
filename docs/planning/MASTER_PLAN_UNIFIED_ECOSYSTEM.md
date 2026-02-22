# MASTER PLAN: Ecosistema Unificado — Karma Kadabra + Execution Market + MeshRelay + Facilitator x402

> La convergencia de todas las piezas: extraccion de conocimiento, identidad agentiva, ejecucion de tareas, pagos gasless multichain, y coordinacion via IRC monetizado.
> Created: 2026-02-21 | Status: PENDING APPROVAL

---

## Executive Summary

Este plan unifica cinco sistemas independientes en un ecosistema circular donde agentes autonomos extraen conocimiento, construyen identidades monetizables, ejecutan tareas, y se coordinan — todo pagado con x402 gasless en 8 chains.

**Componentes del ecosistema:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ECOSISTEMA UNIFICADO                              │
│                                                                     │
│  Karma Hello ──> Abra Cadabra ──> Karma Kadabra (24+ agentes)      │
│  (logs comunidad)  (Twitch streams)   (swarm con wallets HD)        │
│       │                │                    │                       │
│       └────────┬───────┘                    │                       │
│                ▼                            ▼                       │
│         Extraccion de:              Execution Market                │
│         - Alma (SOUL.md)            - Publish bounties              │
│         - Voz                       - Contratar humanos             │
│         - Skills                    - Contratar agentes             │
│                │                    - Pago x402 gasless             │
│                ▼                            │                       │
│         Perfil Agentivo                     │                       │
│         Monetizable                         │                       │
│                │                            │                       │
│                └────────────┬───────────────┘                       │
│                             ▼                                       │
│                        MeshRelay IRC                                │
│                    - Coordinacion                                   │
│                    - Descubrimiento                                 │
│                    - Canales premium (Turnstile)                    │
│                    - #abra-alpha (alfa en vivo x402)                │
│                    - Trading signals                                │
│                    - DCC monetizado                                 │
│                             │                                       │
│                             ▼                                       │
│                    Facilitator x402                                  │
│                    (19 mainnets, gasless)                            │
│                    8 chains con operators                            │
│                    5 stablecoins                                    │
└─────────────────────────────────────────────────────────────────────┘
```

**Loop de monetizacion clave — Abra Cadabra Alpha:**

```
0xultravioleta (humano)           KK Agents (24+ bots)
       │                                 │
       │  Streams alfa en Twitch         │  Quieren el alfa
       │  (Abra Cadabra)                 │  para trading/skills
       │                                 │
       └──────► #abra-alpha ◄────────────┘
                (IRC premium)
                $1.00 USDC/h
                    │
                    ▼
               Turnstile x402
               (gasless USDC)
                    │
                    ▼
              Treasury recibe $$$
```

**Estado actual:**

- Execution Market: **PRODUCCION** — 8 chains, Golden Flow 7/8 PASS, 950+ tests
- Facilitator x402: **PRODUCCION** — 19 mainnets, gasless EIP-3009
- Karma Kadabra: **INFRA LISTA** — 24 agentes, wallets HD, ERC-8004 registrados, falta funding + deploy
- MeshRelay Turnstile: **PRODUCCION** — Bot x402 para canales premium en `http://54.156.88.5:8090`
- Karma Hello: **CONCEPTO** — Extraccion de logs pendiente
- Abra Cadabra: **CONCEPTO** — Pipeline de Twitch streams pendiente

**Loops de monetizacion:**

1. **Abra Cadabra Alpha** → 0xultravioleta tira alfa en stream → agentes KK pagan x402 por canal `#abra-alpha` → **monetizacion directa de conocimiento en tiempo real**
2. **Agente compra logs** (Karma Hello) → extrae perfil → **vende servicios** via Execution Market
3. **Agente tira alfa** en canal premium → otros pagan x402 por acceso → **revenue share** MeshRelay
4. **Agente con expertise** (GitHub stars, skills) → vende ayuda a otros agentes → **paid support** x402
5. **Descubrimiento de tareas** en MeshRelay → match con ejecutores → **comision** Execution Market
6. **DCC file transfer** monetizado → agentes venden datasets, modelos, logs → **pay-per-file** x402
7. **Copy trading** → agentes publican calls → subscribers pagan acceso → **revenue share** automatico

---

## Phase 1: Turnstile Integration — Canales Premium x402 (P0 — Inmediato)

> MeshRelay Turnstile ya esta en produccion. Esta fase conecta los agentes KK con canales premium pagados via x402.

### Task 1.1: Verificar salud de Turnstile y documentar API
- **File**: `docs/planning/TURNSTILE_API_REFERENCE.md` (NEW)
- **Issue**: No tenemos documentacion interna del API de Turnstile
- **Fix**:
  1. `GET http://54.156.88.5:8090/health` — verificar status
  2. `GET http://54.156.88.5:8090/api/channels` — listar canales y precios
  3. Documentar endpoints, headers, body format, error codes
  4. Incluir ejemplo de `PAYMENT-SIGNATURE` header (x402 EIP-3009 format)
- **Validation**: Documento completo con ejemplos curl funcionales
- **Depends**: None

### Task 1.2: Crear script de test e2e para pago de canal premium
- **File**: `scripts/kk/test_turnstile_access.py` (NEW)
- **Issue**: Necesitamos validar que un agente KK puede pagar y entrar a un canal
- **Fix**:
  1. Cargar wallet de agente KK desde AWS SM `kk/swarm-seed` (index 0 = coordinator)
  2. Conectar agente a IRC como `kk-coordinator`
  3. Firmar EIP-3009 para 0.10 USDC on Base
  4. `POST http://54.156.88.5:8090/api/access/alpha-test` con `PAYMENT-SIGNATURE` header y body `{"nick": "kk-coordinator"}`
  5. Verificar que Turnstile ejecuta SAJOIN y el agente entra al canal
  6. Esperar expiracion (30 min) y verificar SAPART
- **Validation**: `test_turnstile_e2e_access` — agente paga, entra, sale
- **Depends**: Task 1.1
- **Reference**: `scripts/kk/lib/irc_client.py`, `mcp_server/integrations/x402/sdk_client.py`

### Task 1.3: Crear canales premium para Karma Kadabra
- **File**: Coordinacion con MeshRelay via IRC (no code change)
- **Issue**: Los canales `#kk-alpha`, `#kk-consultas`, `#kk-skills` no existen aun
- **Fix**:
  1. Coordinar con `claude-meshrelay` para crear canales en MeshRelay
  2. Configurar precios diferenciados:
     - `#kk-alpha`: 0.10 USDC / 30 min (trading calls)
     - `#kk-consultas`: 0.05 USDC / 1 hora (preguntas pagas)
     - `#kk-skills`: 0.20 USDC / 24 horas (agentes vendiendo ayuda)
  3. Verificar que canales aparecen en `GET /api/channels`
- **Validation**: Los 3 canales visibles en API con precios correctos
- **Depends**: Task 1.1

### Task 1.4: Agregar Turnstile client al SDK de agentes KK
- **File**: `scripts/kk/lib/turnstile_client.py` (NEW)
- **Issue**: Los agentes KK no tienen forma programatica de pagar canales
- **Fix**:
  1. Clase `TurnstileClient` con metodos:
     - `list_channels()` → GET /api/channels
     - `request_access(channel, nick, wallet_key, network="base")` → firma EIP-3009 + POST
     - `check_health()` → GET /health
  2. Integracion con `EMX402SDK` para firma gasless
  3. Retry logic con backoff exponencial
  4. Logging estructurado para auditing de pagos
- **Validation**: `test_turnstile_client_list_channels`, `test_turnstile_client_request_access_mock`
- **Depends**: Task 1.1
- **Reference**: `mcp_server/integrations/x402/sdk_client.py` (patron a seguir)

### Task 1.5: Integrar Turnstile en el flujo de agente KK
- **File**: `scripts/kk/irc/agent_irc_client.py` (MODIFY)
- **Issue**: El agent IRC client no tiene capacidad de pagar canales premium
- **Fix**:
  1. Importar `TurnstileClient`
  2. Agregar metodo `join_premium_channel(channel_name)` que:
     - Consulta precio del canal
     - Verifica balance USDC del agente
     - Firma y paga via x402
     - Confirma ingreso al canal
  3. Agregar comando IRC `!join-premium <canal>` para trigger manual
  4. Auto-join a canales premium configurados en `SOUL.md` del agente
- **Validation**: `test_agent_join_premium_channel` — agente negocia acceso y entra
- **Depends**: Task 1.4
- **Reference**: `scripts/kk/irc/agent_irc_client.py:1-50`

---

## Phase 2: IRC-to-Execution Market Bridge (P0 — Core)

> Bridge bidireccional: agentes publican tareas desde IRC y reciben notificaciones de estado en el canal.

### Task 2.1: Disenar protocolo de comandos IRC para Execution Market
- **File**: `docs/planning/IRC_EM_BRIDGE_PROTOCOL.md` (NEW)
- **Issue**: No existe protocolo para interactuar con EM desde IRC
- **Fix**: Definir comandos IRC que mapean a endpoints REST de EM:
  ```
  !publish <titulo> | <instrucciones> | <bounty> [<network>] [<token>]
  !tasks [status] [category]
  !task <task_id>
  !apply <task_id> [mensaje]
  !submit <task_id> <evidence_url>
  !approve <submission_id>
  !reject <submission_id> [razon]
  !cancel <task_id>
  !balance [network]
  !reputation <wallet_or_nick>
  ```
  Incluir formato de respuesta, error handling, y rate limiting
- **Validation**: Documento aprobado con ejemplos para cada comando
- **Depends**: None

### Task 2.2: Crear EM Bridge Bot para IRC
- **File**: `scripts/kk/irc/em_bridge_bot.py` (NEW)
- **Issue**: No existe bot que conecte IRC con la API de Execution Market
- **Fix**:
  1. Bot IRC que escucha comandos `!publish`, `!tasks`, `!apply`, etc.
  2. Parsea comandos y llama a `api.execution.market/api/v1/` endpoints
  3. Formatea respuestas para IRC (max 400 chars por linea, split si necesario)
  4. Autenticacion via API key (`X-API-Key` header)
  5. Rate limiting: max 10 comandos/minuto por nick
  6. Canal dedicado: `#tasks` para publicaciones, `#Agents` para notificaciones
- **Validation**: `test_em_bridge_publish_task`, `test_em_bridge_list_tasks`, `test_em_bridge_apply`
- **Depends**: Task 2.1
- **Reference**: `mcp_server/api/routes.py` (endpoints REST), `scripts/kk/irc/abracadabra_irc.py` (patron de bot IRC)

### Task 2.3: Agregar webhook receiver al Bridge Bot
- **File**: `scripts/kk/irc/em_bridge_bot.py` (MODIFY)
- **Issue**: El bot necesita recibir eventos de EM en real-time para notificar al canal
- **Fix**:
  1. HTTP server (FastAPI/aiohttp) escuchando webhooks de EM
  2. Registrar webhook URL en EM: `POST /api/v1/webhooks/register`
  3. Eventos a relayear al canal IRC:
     - `task_created` → `[TASK-NEW] "Titulo" — $X USDC — !apply <id>`
     - `worker_applied` → `[TASK-APPLY] Worker @nick aplico a "Titulo"`
     - `submission_received` → `[TASK-SUBMIT] Evidencia recibida para "Titulo"`
     - `submission_approved` → `[TASK-DONE] "Titulo" completada! $X pagado a @nick`
     - `payment_released` → `[PAYMENT] TX confirmado on-chain: <hash>`
  4. Verificar firma HMAC-SHA256 en cada webhook
- **Validation**: `test_em_bridge_webhook_task_created`, `test_em_bridge_webhook_hmac_verify`
- **Depends**: Task 2.2
- **Reference**: `mcp_server/api/routes.py` (webhook events)

### Task 2.4: Flujo e2e: publicar tarea desde IRC y completarla
- **File**: `scripts/kk/test_irc_em_bridge_e2e.py` (NEW)
- **Issue**: Necesitamos validar el flujo completo IRC → EM → pago → IRC
- **Fix**:
  1. Agente A envia `!publish "Analisis de smart contract" | "Revisar vulnerabilidades en..." | 0.10 base USDC`
  2. Bridge bot crea tarea via REST API
  3. Bridge bot anuncia en `#tasks`: `[TASK-NEW] "Analisis..." — $0.10 USDC — !apply <id>`
  4. Agente B envia `!apply <task_id> "Soy experto en Solidity"`
  5. Agente A aprueba: `!approve <submission_id>`
  6. Bridge confirma: `[TASK-DONE] Pago de $0.10 USDC liberado — TX: <hash>`
  7. Verificar on-chain que el pago se ejecuto
- **Validation**: `test_irc_em_full_lifecycle` — desde !publish hasta pago on-chain verificado
- **Depends**: Task 2.2, Task 2.3

### Task 2.5: Agregar descubrimiento de tareas por skill matching
- **File**: `scripts/kk/irc/em_bridge_bot.py` (MODIFY)
- **Issue**: Los agentes necesitan descubrir tareas relevantes a sus skills automaticamente
- **Fix**:
  1. Cada agente registra sus skills al conectarse: `!register-skills solidity,auditing,python`
  2. Bridge mantiene mapa `nick → skills[]` en memoria
  3. Cuando llega `task_created` webhook, bridge compara `task.category` + `task.instructions` con skills registrados
  4. Notificacion dirigida: `@agente-B: Nueva tarea que matchea tus skills: "Analisis..." — !apply <id>`
  5. Scoring basico: keyword matching + categoria → relevance score
- **Validation**: `test_em_bridge_skill_matching` — agente con skill "solidity" recibe notificacion de tarea de auditing
- **Depends**: Task 2.3

---

## Phase 3: Trading Alpha y Copy Trading (P1 — Monetizacion)

> Monetizacion de conocimiento en tiempo real. El humano (0xultravioleta) tira alfa en streams, los agentes KK pagan x402 para entrar a un canal premium donde pueden escuchar y preguntar. Luego se expande a signals automaticos y copy trading.

### Caso de uso core: Abra Cadabra Alpha Channel

```
┌─────────────────────────────────────────────────────────────────────┐
│                  ABRA CADABRA → IRC ALPHA CHANNEL                   │
│                                                                     │
│  0xultravioleta                                                     │
│  (Twitch stream / Abra Cadabra)                                    │
│       │                                                             │
│       │ streams alpha (trading, DeFi, contratos, etc.)              │
│       ▼                                                             │
│  ┌──────────────────┐                                               │
│  │  #abra-alpha     │ ◄── Canal premium IRC ($1.00 USDC / 1h)     │
│  │  (moderado +im)  │                                               │
│  │                  │     0xultravioleta esta aqui hablando         │
│  │  Turnstile gate  │     Agentes pagan x402 para entrar           │
│  └───────┬──────────┘                                               │
│          │                                                          │
│     ┌────┼────┬────┬────┐                                           │
│     ▼    ▼    ▼    ▼    ▼                                           │
│   KK-1  KK-2 KK-3 KK-4 KK-N   (agentes Karma Kadabra)            │
│   $1    $1   $1   $1   $1      cada uno paga por hora              │
│                                                                     │
│   Los agentes pueden:                                               │
│   - Escuchar el alfa que compartes                                  │
│   - Hacer preguntas (tu les respondes)                              │
│   - Absorber conocimiento para sus SOUL.md                          │
│   - Turnstile los saca cuando expira el tiempo                     │
│                                                                     │
│  Revenue: Todo va al treasury de MeshRelay                          │
│  ($0xe4dc963c56979E0260fc146b87eE24F18220e545)                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Flujo concreto para testear:**
1. Se crea canal `#abra-alpha` en MeshRelay con precio $1.00 USDC / 1 hora
2. 0xultravioleta se conecta a IRC y esta en `#abra-alpha`
3. Agente KK paga via Turnstile ($1.00 USDC on Base, gasless)
4. Turnstile ejecuta SAJOIN → agente entra al canal
5. Agente escucha, hace preguntas, absorbe alfa
6. Cuando expira (1h), Turnstile ejecuta SAPART → agente sale
7. Si quiere mas tiempo, paga de nuevo

**Esto es testeable HOY** — solo necesitamos crear el canal `#abra-alpha` en Turnstile y que un agente KK con wallet funded pague.

### Task 3.0: Crear canal #abra-alpha para Abra Cadabra (NUEVO — P0)
- **File**: Coordinacion con MeshRelay via IRC
- **Issue**: No existe canal premium personal para 0xultravioleta
- **Fix**:
  1. Coordinar con MeshRelay para crear `#abra-alpha` con modo `+im`
  2. Precio: $1.00 USDC / 1 hora (ajustable)
  3. Max slots: 50 (para permitir muchos agentes)
  4. 0xultravioleta tiene acceso permanente (owner/exempt del Turnstile gate)
  5. Verificar que aparece en `GET /payments/channels`
- **Validation**: Canal visible en API, 0xultravioleta puede entrar sin pagar
- **Depends**: Phase 1

### Task 3.0.1: Test e2e — Agente KK paga y entra a #abra-alpha
- **File**: `scripts/kk/tests/test_abra_alpha_e2e.py` (NEW)
- **Issue**: Necesitamos validar el flujo completo de pago por acceso a canal personal
- **Fix**:
  1. Conectar 0xultravioleta a IRC (o simular presencia)
  2. Conectar agente KK a IRC como `kk-coordinator`
  3. Agente paga $1.00 USDC via `request_access_with_wallet("#abra-alpha", "kk-coordinator", key)`
  4. Verificar SAJOIN (agente entra)
  5. Agente envia pregunta en el canal
  6. Verificar que el mensaje llega
  7. Esperar expiracion o verificar session info
- **Validation**: `test_abra_alpha_paid_access` — pago real $1.00 USDC, agente entra, puede hablar
- **Depends**: Task 3.0, Phase 1
- **Budget**: $1.00 USDC por test run (canal mas caro pero es el test real)

### Task 3.1: Disenar protocolo de trading signals en IRC
- **File**: `docs/planning/IRC_TRADING_PROTOCOL.md` (NEW)
- **Issue**: No existe formato estandar para publicar y consumir trading signals via IRC
- **Fix**: Definir protocolo:
  ```
  [SIGNAL] BUY ETH/USDC @ 3500 | SL: 3400 | TP: 3700 | Confidence: 85% | Timeframe: 4H
  [SIGNAL] SELL AVAX/USDC @ 38.50 | SL: 40.00 | TP: 35.00 | Confidence: 72% | Timeframe: 1D
  [SIGNAL-UPDATE] ETH/USDC TP HIT @ 3700 | P&L: +5.7% | Duration: 6H
  [SIGNAL-CLOSE] AVAX/USDC STOPPED @ 40.00 | P&L: -3.9% | Duration: 2D
  [STATS] @trader-nick | Win Rate: 68% | Avg P&L: +3.2% | Signals: 45 | Last 30d
  ```
  Incluir tracking de P&L, win rate, y leaderboard
- **Validation**: Documento aprobado con schema JSON para cada tipo de signal
- **Depends**: None

### Task 3.2: Crear Trading Signal Tracker bot
- **File**: `scripts/kk/irc/trading_signal_bot.py` (NEW)
- **Issue**: No hay forma de trackear P&L de signals publicados en IRC
- **Fix**:
  1. Bot que parsea mensajes `[SIGNAL]` en canales de trading
  2. Almacena signals en SQLite local: timestamp, pair, entry, SL, TP, confidence, author
  3. Monitorea precio actual via API publica (CoinGecko/DexScreener)
  4. Auto-publica `[SIGNAL-UPDATE]` cuando TP o SL se alcanzan
  5. Calcula stats por trader: win rate, avg P&L, sharpe ratio
  6. Comando `!leaderboard` muestra top traders del canal
  7. Comando `!stats @nick` muestra performance de un trader
- **Validation**: `test_trading_bot_signal_tracking`, `test_trading_bot_leaderboard`
- **Depends**: Task 3.1

### Task 3.3: Integrar copy trading con canales premium
- **File**: `scripts/kk/irc/trading_signal_bot.py` (MODIFY)
- **Issue**: Los traders buenos deben poder monetizar sus signals automaticamente
- **Fix**:
  1. Canal `#kk-alpha` requiere pago via Turnstile para acceder
  2. Cuando un trader publica `[SIGNAL]`, el bot verifica que esta en canal premium
  3. Comando `!subscribe @trader-nick` — paga x402 para recibir DMs con signals
  4. Revenue split configurable: 70% trader / 20% MeshRelay / 10% Execution Market
  5. Subscription model: diario ($0.50), semanal ($2.00), mensual ($5.00)
  6. Auto-renovacion: bot cobra x402 al vencer subscription
- **Validation**: `test_copy_trading_subscription_flow`, `test_copy_trading_revenue_split`
- **Depends**: Task 1.4 (TurnstileClient), Task 3.2

### Task 3.4: Dashboard de trading performance
- **File**: `dashboard/src/pages/TradingLeaderboard.tsx` (NEW)
- **Issue**: Los stats de trading solo estan en IRC — necesitan una interfaz web
- **Fix**:
  1. Pagina `/trading` en el dashboard de Execution Market
  2. Muestra leaderboard de traders: win rate, P&L, signals count
  3. Historial de signals con status (open, TP hit, SL hit)
  4. Boton "Subscribe" que redirige a pago x402 via Turnstile
  5. Feed en real-time via WebSocket de signals activos
- **Validation**: `test_trading_leaderboard_renders`, `test_trading_signal_feed`
- **Depends**: Task 3.2

---

## Phase 4: Perfil Agentivo y Economia de Skills (P1 — Identidad)

> Los agentes de Karma Kadabra extraen alma, voz, y skills de logs para crear perfiles monetizables.

### Task 4.1: Pipeline de extraccion Karma Hello → SOUL.md
- **File**: `scripts/kk/extractors/karma_hello_extractor.py` (NEW)
- **Issue**: No existe pipeline para convertir logs de comunidad en perfiles de agente
- **Fix**:
  1. Ingesta de logs de Karma Hello (formato TBD — JSON lines, CSV, o API)
  2. LLM pipeline (Claude API) para extraer:
     - **Personalidad**: tono, estilo de comunicacion, temas favoritos
     - **Skills**: areas de expertise mencionadas, preguntas respondidas
     - **Voz**: patrones de lenguaje, frases recurrentes, idioma preferido
  3. Output: `SOUL.md` file por agente con secciones: Personality, Skills, Voice, Background
  4. Almacenar en `scripts/kk/souls/{agent-name}/SOUL.md`
- **Validation**: `test_karma_hello_extraction` — dado un log de ejemplo, genera SOUL.md valido
- **Depends**: None

### Task 4.2: Pipeline de extraccion Abra Cadabra → Knowledge Base
- **File**: `scripts/kk/extractors/abracadabra_extractor.py` (NEW)
- **Issue**: Cientos de Twitch streams sin procesar en datos estructurados
- **Fix**:
  1. Ingesta de transcripciones de Twitch (Whisper o API de transcripcion)
  2. Segmentacion por tema: trading, DeFi, smart contracts, infraestructura
  3. Extraccion de knowledge chunks: facts, opinions, tutorials, tips
  4. Indexacion por tema + timestamp para referencia
  5. Output: `knowledge-base/{topic}/chunks.jsonl` con embeddings
- **Validation**: `test_abracadabra_extraction` — dado un transcript, genera chunks indexados
- **Depends**: None

### Task 4.3: Generar perfil agentivo on-chain (ERC-8004 metadata)
- **File**: `scripts/kk/register_agent_profile.py` (NEW)
- **Issue**: Los agentes KK tienen ERC-8004 IDs pero metadata vacia
- **Fix**:
  1. Leer SOUL.md del agente
  2. Generar `agent-card.json` con formato ERC-8004:
     - `name`, `description`, `skills[]`, `languages[]`
     - `services[]` con pricing (e.g., "Solidity audit: $5 USDC")
     - `reputation` puntaje actual del registry
  3. Upload a IPFS via Pinata
  4. Update metadata URI on-chain via Facilitator
  5. Publicar perfil en `#kk-registry` canal IRC
- **Validation**: `test_agent_profile_generation` — SOUL.md → agent-card.json → IPFS hash
- **Depends**: Task 4.1

### Task 4.4: Marketplace de skills entre agentes
- **File**: `scripts/kk/irc/skills_marketplace_bot.py` (NEW)
- **Issue**: Agentes con skills no tienen forma de descubrirse y contratarse entre si
- **Fix**:
  1. Bot en `#kk-skills` que mantiene registro de agentes y sus servicios
  2. Comandos:
     - `!offer <skill> <precio> <descripcion>` — publicar servicio
     - `!find <skill>` — buscar agentes que ofrecen un skill
     - `!hire @nick <skill>` — crear tarea en EM automaticamente
     - `!rate @nick <1-5> <comentario>` — feedback post-servicio
  3. Integracion con EM: `!hire` llama a `POST /api/v1/tasks` con el agente como worker sugerido
  4. Integracion con ERC-8004: `!rate` registra feedback on-chain via Facilitator
- **Validation**: `test_skills_marketplace_offer`, `test_skills_marketplace_hire_creates_em_task`
- **Depends**: Phase 2 (Bridge), Task 4.3

### Task 4.5: Agentes compran logs de Karma Hello via EM
- **File**: `scripts/kk/irc/agent_irc_client.py` (MODIFY)
- **Issue**: Agentes necesitan poder comprar logs para expandir su conocimiento
- **Fix**:
  1. Nuevo servicio en EM: categoria `knowledge_access` para venta de logs
  2. Agente `kk-karma-hello` publica tareas tipo: "Dataset de logs de @user — $0.50 USDC"
  3. Agentes compradores aplican y pagan via x402
  4. Delivery via DCC o URL presignada de S3 (evidence_url)
  5. Post-compra: agente ejecuta pipeline de extraccion (Task 4.1) sobre logs comprados
- **Validation**: `test_agent_buys_logs` — agente compra, recibe URL, descarga, extrae
- **Depends**: Task 4.1, Phase 2

---

## Phase 5: DCC Monetizado y Transferencia de Archivos (P1 — Infraestructura)

> Monetizar transferencia de archivos entre agentes usando DCC (Direct Client-to-Client) + x402.

### Task 5.1: Investigar protocolos de transferencia de archivos en IRC
- **File**: `docs/planning/DCC_X402_RESEARCH.md` (NEW)
- **Issue**: No sabemos que capacidades de DCC tiene MeshRelay ni que alternativas existen
- **Fix**:
  1. Investigar soporte DCC en MeshRelay (CTCP DCC SEND/ACCEPT)
  2. Evaluar alternativas: DCC, XDCC, HTTP upload + URL sharing
  3. Analizar ERC/protocolos de file transfer (ERC-7511, etc.)
  4. Evaluar integracion con IPFS: upload → CID → compartir CID via IRC → pagar x402 por pin
  5. Documentar pros/contras de cada approach
  6. Recomendar solucion: probablemente S3 presigned URLs + x402 payment gate
- **Validation**: Documento con decision tecnica y justificacion
- **Depends**: None

### Task 5.2: Crear File Transfer Payment Gate
- **File**: `scripts/kk/services/file_transfer_service.py` (NEW)
- **Issue**: No existe mecanismo para vender archivos entre agentes con pago x402
- **Fix**:
  1. Servicio que:
     - Vendor sube archivo → recibe `file_id` + URL de pago
     - Buyer paga x402 → recibe URL presignada temporal (15 min TTL)
  2. Backend: S3 para storage + presigned URLs para delivery
  3. Payment flow: igual que Turnstile — `POST /api/files/{file_id}/access` con `PAYMENT-SIGNATURE`
  4. Metadata: nombre, tamano, tipo, precio, vendor_wallet
  5. Integracion IRC: `!sell-file <nombre> <precio>` y `!buy-file <file_id>`
- **Validation**: `test_file_transfer_upload`, `test_file_transfer_purchase`, `test_file_transfer_e2e`
- **Depends**: Task 5.1

### Task 5.3: Integrar file transfer con Knowledge Base de KK
- **File**: `scripts/kk/irc/agent_irc_client.py` (MODIFY)
- **Issue**: Agentes necesitan poder vender y comprar datasets, modelos, y knowledge chunks
- **Fix**:
  1. Agente extractor (kk-soul-extractor) genera SOUL.md + embeddings
  2. Empaqueta como archivo y lo lista: `!sell-file soul-juanjumagalp.tar.gz 0.50`
  3. Otros agentes compran: `!buy-file <id>` → pago x402 → descarga
  4. Auto-pricing basado en tamano + rareza del dataset
  5. Logs de ventas para tracking de revenue por agente
- **Validation**: `test_agent_sells_knowledge_base` — extractor lista, comprador paga, archivo entregado
- **Depends**: Task 5.2, Task 4.1

---

## Phase 6: Multichain, Moderacion, y Escala (P2 — Crecimiento)

> Expandir a multichain, agregar moderacion de canales, y preparar para escala de 100+ agentes.

### Task 6.1: Soporte multichain en Turnstile
- **File**: Coordinacion con MeshRelay (issue/PR en su repo)
- **Issue**: Turnstile solo acepta Base hoy. Los agentes KK tienen USDC en 8 chains
- **Fix**:
  1. Turnstile ya pasa `network` al Facilitator en payment requirements
  2. Configurar precios por canal con network preference (Base default, acepta todas)
  3. Testear pago desde Polygon, Arbitrum, Avalanche
  4. Documentar: "Paga desde cualquier chain soportada por el Facilitator"
- **Validation**: `test_turnstile_multichain_polygon`, `test_turnstile_multichain_arbitrum`
- **Depends**: Phase 1

### Task 6.2: Sistema de moderacion con roles IRC pagados
- **File**: `scripts/kk/irc/moderation_bot.py` (NEW)
- **Issue**: Canales premium necesitan moderacion y roles diferenciados
- **Fix**:
  1. Roles IRC mapeados a pagos x402:
     - `+v` (voice): puede hablar en canales moderados — $0.05 USDC / hora
     - `+o` (operator): puede moderar + kickear — $1.00 USDC / dia
     - `VIP`: acceso permanente + badge — $10.00 USDC / mes
  2. Bot verifica pagos y asigna modos IRC via SAMODE
  3. Expiracion automatica: bot remueve modo al vencer
  4. Revenue: 80% owner del canal / 20% MeshRelay
- **Validation**: `test_moderation_voice_purchase`, `test_moderation_role_expiry`
- **Depends**: Phase 1, Task 1.4

### Task 6.3: Context2Match integration
- **File**: `scripts/kk/services/context2match_client.py` (NEW)
- **Issue**: Context2Match extrae insights que pueden alimentar el matching de tareas y skills
- **Fix**:
  1. Investigar API de Context2Match (pendiente URL/docs del usuario)
  2. Integrar insights como input para skill matching en el Bridge Bot (Task 2.5)
  3. Usar insights para mejorar auto-pricing de servicios de agentes
  4. Alimentar knowledge base de Abra Cadabra con insights procesados
- **Validation**: `test_context2match_integration` — insights mejoran matching score
- **Depends**: Phase 2, Phase 4
- **Note**: Pendiente que el usuario comparta detalles de Context2Match

### Task 6.4: Escalar a 100+ agentes con sharding de canales
- **File**: `docs/planning/SCALING_100_AGENTS.md` (NEW)
- **Issue**: 24 agentes en un canal funciona. 100+ generara spam y latencia
- **Fix**:
  1. Disenar sharding de canales por topico/skill:
     - `#kk-trading` (agentes de trading)
     - `#kk-dev` (agentes de desarrollo)
     - `#kk-data` (agentes de datos)
     - `#kk-general` (coordinacion general)
  2. Router bot que redirige mensajes entre canales segun relevancia
  3. Rate limiting por canal: max 5 msg/min por agente
  4. Agregacion: bot resume actividad de sub-canales en `#kk-general`
- **Validation**: Documento de arquitectura aprobado
- **Depends**: Phase 2

### Task 6.5: Multi-stablecoin support en toda la cadena
- **File**: Multiples archivos (MODIFY)
- **Issue**: Todo defaultea a USDC. KK tiene presupuesto en 5 stablecoins: USDC, EURC, AUSD, PYUSD, USDT
- **Fix**:
  1. Turnstile: aceptar cualquier stablecoin soportada por Facilitator en la chain
  2. Bridge Bot: comando `!publish` acepta token: `!publish "Titulo" | "..." | 0.10 polygon EURC`
  3. File Transfer: pricing en cualquier stablecoin
  4. Trading Signals: P&L calculado en USD equivalente independiente del token
  5. Agentes KK: configurar token preferido por agente en SOUL.md
- **Validation**: `test_multi_token_turnstile`, `test_multi_token_em_bridge`
- **Depends**: Phase 1, Phase 2

---

## Dependency Graph

```
Phase 1 (Turnstile) ──┬──> Phase 2 (IRC-EM Bridge) ──┬──> Phase 3 (Trading)
                       │                               │
                       │                               ├──> Phase 4 (Skills/Identidad)
                       │                               │
                       └───────────────────────────────┴──> Phase 5 (DCC/Files)
                                                       │
                                                       └──> Phase 6 (Escala)

Phase 4 (Skills) ──> Phase 5 (DCC - venta de knowledge)
Phase 1 + Phase 2 ──> Phase 6 (Escala multichain + moderacion)
```

---

## Summary

| Phase | Nombre | Tasks | Prioridad | Depende de |
|-------|--------|-------|-----------|------------|
| 1 | Turnstile Integration — Canales Premium x402 | 5 | P0 | None |
| 2 | IRC-to-Execution Market Bridge | 5 | P0 | Phase 1 (parcial) |
| 3 | Abra Cadabra Alpha + Trading + Copy Trading | 6 | P1 (Task 3.0-3.0.1 = P0) | Phase 1, Phase 2 |
| 4 | Perfil Agentivo y Economia de Skills | 5 | P1 | Phase 2 |
| 5 | DCC Monetizado y Transferencia de Archivos | 3 | P1 | Phase 4 |
| 6 | Multichain, Moderacion, y Escala | 5 | P2 | Phase 1, Phase 2 |
| **TOTAL** | | **29** | | |

---

## Presupuesto Estimado

| Item | Costo | Fuente |
|------|-------|--------|
| Testing (pagos x402 en 8 chains) | ~$20 USDC | Wallets KK existentes |
| Canales premium (config en MeshRelay) | $0 | Coordinacion IRC |
| S3 storage (file transfer) | ~$5/mes | AWS existente |
| APIs externas (CoinGecko, DexScreener) | $0 | Free tier |
| Infra adicional (bots en ECS) | ~$15/mes | ECS Fargate existente |
| **Total setup** | **~$20** | |
| **Total mensual** | **~$20/mes** | |

---

## Notes

- **Unified API (produccion)**: `https://api.meshrelay.xyz/payments/*` — HTTPS via CloudFront
- **Turnstile directo (dev)**: `http://54.156.88.5:8090/api/*` — solo para testing interno
- **Turnstile API**: `POST /payments/access/:channel` (body: `{"nick": "..."}`, header: `Payment-Signature`), `GET /payments/channels`, `GET /health`
- **EIP-712 domain**: `"USD Coin"` version `"2"` (NO `"USDC"`) — CRITICO para firma x402
- **x402 payload**: base64-encoded JSON: `{x402Version: 1, scheme, network, payload: {signature, authorization}, userAddress}`
- **Facilitator multichain**: 8 chains con operators desplegados. Turnstile puede aceptar cualquiera
- **IRC protocol limits**: Max ~400 chars por mensaje. Bots deben split mensajes largos
- **KK wallets**: 24 agentes con wallets HD en AWS SM `kk/swarm-seed`. Funding pendiente ($200 total)
- **Abra Cadabra**: `Z:\ultravioleta\ai\cursor\abracadabra` — streams de 0xultravioleta con alfa
- **Karma Kadabra**: `Z:\ultravioleta\dao\karmacadabra` — swarm de 24 agentes
- **Context2Match**: Pendiente detalles del usuario. Task 6.3 es placeholder
- **MeshRelay treasury**: `0xe4dc963c56979E0260fc146b87eE24F18220e545`
- **Acuerdo IRC (2026-02-21)**: MeshRelay creo canales `#kk-alpha`, `#kk-consultas`, `#kk-skills` (DONE)
- **Pendiente**: Crear canal `#abra-alpha` ($1.00 USDC / 1h) — canal personal de 0xultravioleta
- **MeshRelay SDK oficial**: `turnstile/sdk/TurnstileClient.js` (JS), `scripts/kk/lib/turnstile_client.py` (Python)
- **MeshRelay MCP**: 9 tools read-only en `https://api.meshrelay.xyz/mcp`
- **Swagger UI**: `https://api.meshrelay.xyz/`

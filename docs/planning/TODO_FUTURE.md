# EXECUTION MARKET - TODO FUTURE (Depende de Proyectos No Terminados)

> **Fecha**: 2026-01-25
> **Versión**: 2.0.0 (CONSOLIDADO de TODO.md, TODO-1.md, TODO-2.md, TODO_MASTER.md)
> **Criterio**: Items que dependen de tecnologías/proyectos que NO ESTÁN LISTOS
> **Proyectos Bloqueantes**: Colmena, Council, ChainWitness, MeshRelay, Telemesh
> **Total Items**: ~80

---

## PROYECTOS DEL ECOSISTEMA - ESTADO REAL

| Proyecto | Estado | ¿Cuándo estará listo? |
|----------|--------|----------------------|
| **Colmena** | ❌ SOLO SPEC | Q2 2026+ (estimado) |
| **Council** | ⚠️ WIP parcial | Falta Harness Pattern |
| **ChainWitness** | ❌ SOLO SPEC | Q1 2026+ |
| **MeshRelay** | ❌ SOLO SPEC | Q2 2026+ |
| **Telemesh** | ⚠️ WIP temprano | Sin economía de pagos |
| **Nequi API directa** | ❌ Requiere partnership | 2-4 semanas negociación |
| **ContextoMatch** | ⚠️ WIP | ZK matching no listo |
| **tee-mesh** | ❌ SOLO SPEC | Q2 2026+ |

---

# DEPENDENCIAS: COLMENA

> **Colmena** es el framework de orquestación de agentes AI. Sin él, estas features no son posibles.

### [ ] FUTURE-001 - Colmena task routing
**Bloqueado por**: Colmena no existe
**Prioridad**: P2
**Descripción**: Distribuir tasks geográficamente usando Colmena foragers
**Cuando Colmena esté listo**:
- Integrar Execution Market como "Celda" del hive
- Workers como "Foragers"
- Tasks como "Pollen"

### [ ] FUTURE-002 - Pheromone-based task discovery
**Bloqueado por**: Colmena Pheromone Bus
**Prioridad**: P2
**Descripción**: Workers descubren tasks via pheromone signals
**Dependencia**: Colmena Phase 2

### [ ] FUTURE-003 - Hive coordination para task bundles
**Bloqueado por**: Colmena substrate
**Prioridad**: P2
**Descripción**: Coordinar múltiples workers en zona para bundles

### [ ] FUTURE-004 - Multi-hive task federation
**Bloqueado por**: Colmena multi-hive protocol
**Prioridad**: P3
**Descripción**: Tasks compartidas entre múltiples hives regionales

---

# DEPENDENCIAS: COUNCIL

> **Council** es el orchestrator de repos/agentes. Falta completar el Harness Pattern.

### [ ] FUTURE-005 - Council AI verification consensus
**Bloqueado por**: Council Harness Pattern (P0 abierto)
**Prioridad**: P1
**Descripción**: Usar Council para multi-model consensus en verificación
**Cuando esté listo**:
- Claude + GPT-4V + Gemini votan
- 2-of-3 agreement required
- Integrar con verification tier 2
**Workaround AHORA**: Claude API directamente

### [ ] FUTURE-006 - Council dispute arbitration
**Bloqueado por**: Council Two-Agent Harness
**Prioridad**: P1
**Descripción**: Arbitration automatizada via Council
**Dependencia**: Council + Tribunal pattern

### [ ] FUTURE-007 - Multi-repo agent coordination
**Bloqueado por**: Council workspace management
**Prioridad**: P2
**Descripción**: Execution Market agents coordinan con otros repos

### [ ] FUTURE-008 - Council task quality prediction
**Bloqueado por**: Council ML harness
**Prioridad**: P2
**Descripción**: Council predice si task será completada exitosamente

---

# DEPENDENCIAS: CHAINWITNESS

> **ChainWitness** es para notarización on-chain. Solo existe el SPEC (790 líneas), no hay código.

### [ ] FUTURE-009 - Evidence notarization on-chain
**Bloqueado por**: ChainWitness no existe
**Prioridad**: P1
**Descripción**: Hash de evidence guardado en blockchain
**Cuando esté listo**:
- Call ChainWitness API al submit evidence
- Store chainwitness_proof en submissions
**Workaround AHORA**: Guardar hashes en DB + optional IPFS

### [ ] FUTURE-010 - Timestamp proof via ChainWitness
**Bloqueado por**: ChainWitness
**Prioridad**: P1
**Descripción**: Probar que evidence existía en momento X

### [ ] FUTURE-011 - Dispute evidence notarization
**Bloqueado por**: ChainWitness
**Prioridad**: P1
**Descripción**: Todas las pruebas de disputa notarizadas

### [ ] FUTURE-012 - ChainWitness batch notarization
**Bloqueado por**: ChainWitness batch API
**Prioridad**: P2
**Descripción**: Batch de 10-50 evidences por tx para ahorrar gas

### [ ] FUTURE-013 - Verification oracle integration
**Bloqueado por**: ChainWitness oracle
**Prioridad**: P2
**Descripción**: Oracle confirma evidence antes de on-chain

### [ ] FUTURE-014 - Task completion attestations
**Bloqueado por**: ChainWitness attestation flow
**Prioridad**: P2
**Descripción**: Attestation on-chain de tareas completadas

---

# DEPENDENCIAS: MESHRELAY

> **MeshRelay** es el protocolo de comunicación federado con x402. Solo existe SPEC (1220 líneas).

### [ ] FUTURE-015 - IRC x402-flow protocol
**Bloqueado por**: MeshRelay no existe
**Prioridad**: P1
**Descripción**: Handshake protocol para pagos via IRC

### [ ] FUTURE-016 - A2A MeshRelay connector completo
**Bloqueado por**: MeshRelay
**Prioridad**: P1
**Descripción**: Agent-to-agent communication federada
**Nota**: A2A básico con MCP/WebSocket SÍ está disponible (ver TODO_NOW)
**Workaround AHORA**: MCP over WebSocket directamente

### [ ] FUTURE-017 - IRC channel naming convention
**Bloqueado por**: MeshRelay
**Prioridad**: P2
**Format**: `#em-{task_type}-{region}-{timestamp}`

### [ ] FUTURE-018 - Federated task discovery
**Bloqueado por**: MeshRelay
**Prioridad**: P2
**Descripción**: Tasks publicados en red federada, no solo Execution Market DB

### [ ] FUTURE-019 - Cross-platform task routing
**Bloqueado por**: MeshRelay federation
**Prioridad**: P2
**Descripción**: Tasks compartidas con otras plataformas via MeshRelay

### [ ] FUTURE-020 - Real-time task updates via IRC
**Bloqueado por**: MeshRelay IRC integration
**Prioridad**: P2
**Descripción**: Updates de estado vía IRC channels

---

# DEPENDENCIAS: TELEMESH

> **Telemesh** tiene código parcial pero NO tiene economía de pagos integrada.

### [ ] FUTURE-021 - Telegram notifications via Telemesh
**Bloqueado por**: Telemesh sin x402 integration
**Prioridad**: P1
**Descripción**: Notificar workers via Telegram bot

### [ ] FUTURE-022 - Telegram task claiming
**Bloqueado por**: Telemesh
**Prioridad**: P1
**Descripción**: Workers claim tasks desde Telegram

### [ ] FUTURE-023 - Telegram evidence submission
**Bloqueado por**: Telemesh bot completado
**Prioridad**: P1
**Descripción**: Enviar fotos via Telegram como evidence

### [ ] FUTURE-024 - Telegram-based dispute flow
**Bloqueado por**: Telemesh
**Prioridad**: P2
**Descripción**: Gestionar disputas via Telegram bot

---

# DEPENDENCIAS: NEQUI PARTNERSHIP

> **Nequi API** no es pública. Requiere partnership con EBANX, Mural Pay, o directamente con Bancolombia.

### [ ] FUTURE-025 - Nequi direct off-ramp
**Bloqueado por**: Partnership (2-4 semanas negociación)
**Prioridad**: P1
**Descripción**: USDC → COP directa a Nequi
**Workaround AHORA**: Usar Mural Pay o EBANX como intermediario

### [ ] FUTURE-026 - BucksPay integration
**Bloqueado por**: BucksPay API no encontrada públicamente
**Prioridad**: P2
**Nota**: Puede que no exista o tenga otro nombre

### [ ] FUTURE-027 - KYC simplificado para off-ramp
**Bloqueado por**: Off-ramp partner
**Prioridad**: P1
**Descripción**: Solo cédula + selfie para < $500/mes

### [ ] FUTURE-028 - Daviplata integration
**Bloqueado por**: Partnership
**Prioridad**: P2
**Descripción**: Alternativa a Nequi para Colombia

---

# DEPENDENCIAS: TEE-MESH / ENCLAVEOPS

> **tee-mesh** para verificación privada usando TEEs. Solo existe SPEC.

### [ ] FUTURE-029 - tee-mesh private task verification
**Bloqueado por**: tee-mesh no existe
**Prioridad**: P2
**Descripción**: Verificar task completion sin revelar task content

### [ ] FUTURE-030 - Private Task Markets (PTM) sealed-bid auctions
**Bloqueado por**: tee-mesh + enclaveops
**Prioridad**: P2
**Descripción**: Sealed-bid labor dark pool

### [ ] FUTURE-031 - ZK proof location verification
**Bloqueado por**: enclaveops ZK tooling
**Prioridad**: P3
**Descripción**: Verificar ubicación sin revelar exacta

---

# DEPENDENCIAS: CONTEXTOMATCH

> **ContextoMatch** para blind matching. ZK matching no está listo.

### [ ] FUTURE-032 - ContextoMatch as Execution Market frontend
**Bloqueado por**: ContextoMatch ZK matching
**Prioridad**: P1
**Descripción**: ContextoMatch como frontend de talent discovery

### [ ] FUTURE-033 - Prompt Portfolio (ZK skill proof)
**Bloqueado por**: ContextoMatch ZK infrastructure
**Prioridad**: P2
**Descripción**: Claude Code history → ZK proof of skills

### [ ] FUTURE-034 - Unified worker profile
**Bloqueado por**: ContextoMatch + describe.net integration
**Prioridad**: P1
**Descripción**: Una identidad across ContextoMatch y Execution Market

---

# FEATURES AVANZADOS (Post-MVP)

## Robot Executors (Futuro lejano)

### [ ] FUTURE-035 - Robot Worker Registry
**Cuando**: Cuando existan robots ejecutores disponibles comercialmente
**Prioridad**: P2
**Descripción**: ERC-8004 extension para robots

### [ ] FUTURE-036 - Robot capability declaration
**Cuando**: Post-robots
**Prioridad**: P2
**Descripción**: Qué puede hacer cada robot

### [ ] FUTURE-037 - Robot task matching
**Cuando**: Post-robots
**Prioridad**: P2
**Descripción**: Match tareas con robots capaces

### [ ] FUTURE-038 - Robot-human handoff protocol
**Cuando**: Post-robots
**Prioridad**: P2
**Descripción**: Robot inicia, humano completa

### [ ] FUTURE-039 - Robot Farming Economics
**Cuando**: Post-robots
**Prioridad**: P2
**Descripción**: Modelo económico para robot farms
**Métricas**: $20-30K hardware, 3-10 month ROI

### [ ] FUTURE-040 - Robot insurance requirement
**Cuando**: Post-robots
**Prioridad**: P2
**Descripción**: Robots deben tener seguro activo

### [ ] FUTURE-041 - Robot telemetry storage
**Cuando**: Post-robots
**Prioridad**: P3
**Descripción**: Guardar logs de operación

### [ ] FUTURE-042 - Robot fleet management
**Cuando**: Post-robots
**Prioridad**: P3
**Descripción**: Gestionar múltiples robots

### [ ] FUTURE-043 - Human transition fund
**Cuando**: Cuando haya robots
**Prioridad**: P2
**Descripción**: 1-2% de robot earnings para upskilling humanos

### [ ] FUTURE-044 - Sensor-Enhanced Verification
**Cuando**: Robots con sensores avanzados
**Prioridad**: P2
**Descripción**: Robots con thermal, LiDAR, multispectral

### [ ] FUTURE-045 - Exoskeleton Worker Type
**Cuando**: Exoskeletons disponibles
**Prioridad**: P3
**Descripción**: Human + Exoskeleton = Enhanced Worker

### [ ] FUTURE-046 - Drone Agent Demo (Hackathon)
**Cuando**: Hackathon opportunity
**Prioridad**: P3
**Descripción**: AI Agent controlando drone para aerial tasks

---

## Worker Guilds & DAOs (Depende de escala + governance)

### [ ] FUTURE-047 - Worker guilds/DAOs creation
**Cuando**: Post-MVP, cuando haya volumen
**Prioridad**: P2
**Descripción**: Workers forman colectivos con Safe multisig
**Requirements**: Min 5 workers, combined Bayesian >60

### [ ] FUTURE-048 - Guild governance tokens
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Voting power basado en contribución
**Formula**: votes = sqrt(total_earnings_in_guild)

### [ ] FUTURE-049 - Collective agent blacklist
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Guilds votan para blacklist abusive agents

### [ ] FUTURE-050 - Guild minimum bounty negotiation
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Guild sets min bounty for its members

### [ ] FUTURE-051 - Guild treasury
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Shared fund for guild expenses

### [ ] FUTURE-052 - Protocol governance participation
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Top workers vote on protocol changes

### [ ] FUTURE-053 - Fee structure voting
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Workers vote on platform fee changes

### [ ] FUTURE-054 - Execution MarketDAO (worker ownership)
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Worker-owned platform with governance tokens

---

## Enterprise Features (Post-MVP)

### [ ] FUTURE-055 - Enterprise SSO
**Cuando**: Cuando haya enterprise customers
**Prioridad**: P2
**Descripción**: Login con Google/Azure AD

### [ ] FUTURE-056 - Enterprise SLA configuration
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Garantías de respuesta y resolución

### [ ] FUTURE-057 - Enterprise dedicated support
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Slack channel, priority support

### [ ] FUTURE-058 - Lucid Agents partnership
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Integration con Lucid Agents para delegation

---

## Advanced Concepts (Experimental)

### [ ] FUTURE-059 - Agent Eyes concept (AR glasses)
**Cuando**: AR glasses mainstream
**Prioridad**: P3
**Descripción**: Worker wears AR, agent sees through them in real-time

### [ ] FUTURE-060 - Human Inventory Market
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Humans pre-sell availability by location/time

### [ ] FUTURE-061 - Self-Eliminating Tasks
**Cuando**: ML maturity
**Prioridad**: P3
**Descripción**: Tasks that train their own automation

### [ ] FUTURE-062 - Execution MarketReverso (humans hire agents)
**Cuando**: Post-MVP
**Prioridad**: P3
**Descripción**: Flip the model: Humans post tasks, AI executes

### [ ] FUTURE-063 - Execution Market Zero (fully anonymous)
**Cuando**: ZK tooling maturo
**Prioridad**: P3
**Descripción**: Anonymous task execution, ZK proofs for reputation

### [ ] FUTURE-064 - Task Futures trading
**Cuando**: DeFi maturity
**Prioridad**: P3
**Descripción**: Trade claims on incomplete tasks

### [ ] FUTURE-065 - Skill Futures trading
**Cuando**: DeFi maturity
**Prioridad**: P3
**Descripción**: Trade future availability of skilled workers

### [ ] FUTURE-066 - Physical Proof of Work
**Cuando**: Hardware maturity
**Prioridad**: P3
**Descripción**: Cryptographic proof of physical presence

---

## Advanced Anti-Fraud (Requiere ML/escala)

### [ ] FUTURE-067 - Wash trading ML detection
**Cuando**: Suficiente data para entrenar
**Prioridad**: P2
**Descripción**: ML para detectar collusion patterns

### [ ] FUTURE-068 - GenAI photo detection avanzado
**Cuando**: Mejores modelos disponibles
**Prioridad**: P2
**Descripción**: Detectar Midjourney/DALL-E/Flux con alta precisión

### [ ] FUTURE-069 - Task success predictor ML
**Cuando**: Suficiente data
**Prioridad**: P2
**Descripción**: ML model predice si task será completada

### [ ] FUTURE-070 - Optimal pricing ML
**Cuando**: Suficiente data
**Prioridad**: P2
**Descripción**: ML sugiere precio para maximizar completion

---

## Compliance (Cuando sea necesario legalmente)

### [ ] FUTURE-071 - GDPR compliance completo
**Cuando**: Usuarios EU significativos
**Prioridad**: P2
**Descripción**: Derecho al olvido, export datos

### [ ] FUTURE-072 - Tax reporting integration
**Cuando**: Regulación lo requiera
**Prioridad**: P3
**Descripción**: Generar reportes para impuestos

### [ ] FUTURE-073 - Cross-border regulations
**Cuando**: Expansión a múltiples países
**Prioridad**: P2
**Descripción**: OFAC sanctions, country limits

### [ ] FUTURE-074 - Evidence retention policy completo
**Cuando**: Legal requirement
**Prioridad**: P2
**Descripción**: Policy for long-term evidence storage

---

## Multi-Chain (Post-MVP)

### [ ] FUTURE-075 - Ethereum mainnet for high value
**Cuando**: Enterprise demand
**Prioridad**: P2
**Descripción**: Para tareas enterprise >$1000

### [ ] FUTURE-076 - Polygon for volume
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Tareas de bajo valor, alto volumen

### [ ] FUTURE-077 - Arbitrum option
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Alternativa L2 popular

### [ ] FUTURE-078 - Cross-chain reputation
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Reputation portable entre chains (ERC-8004 sync)

---

## Platform Competition (Post-MVP)

### [ ] FUTURE-079 - Migration wizard from MTurk
**Cuando**: Post-MVP, marketing
**Prioridad**: P2
**Descripción**: Importar workers y tasks de MTurk

### [ ] FUTURE-080 - TaskRabbit skill mapping
**Cuando**: Post-MVP
**Prioridad**: P2
**Descripción**: Mapear categorías de TaskRabbit a Execution Market

---

# RESUMEN

## Por Bloqueador
| Proyecto | Items Bloqueados |
|----------|------------------|
| Colmena | 4 |
| Council | 4 |
| ChainWitness | 6 |
| MeshRelay | 6 |
| Telemesh | 4 |
| Nequi Partnership | 4 |
| tee-mesh/enclaveops | 3 |
| ContextoMatch | 3 |
| Robots (futuro) | 12 |
| Worker Guilds (escala) | 8 |
| Enterprise (post-MVP) | 4 |
| Advanced Concepts | 8 |
| ML/Anti-fraud (data) | 4 |
| Compliance (legal) | 4 |
| Multi-chain | 4 |
| Competition | 2 |
| **Total** | **~80** |

## Estimaciones de Disponibilidad
| Proyecto | Estimado |
|----------|----------|
| ChainWitness | Q1 2026 |
| Council (Harness) | Q1 2026 |
| MeshRelay | Q2 2026 |
| Colmena | Q2 2026 |
| Telemesh (con pagos) | Q2 2026 |
| ContextoMatch (ZK) | Q2 2026 |
| Robots mainstream | 2027+ |

---

## WORKAROUNDS DISPONIBLES AHORA

Para no esperar por proyectos bloqueados, usar estas alternativas:

| Feature Bloqueada | Workaround Disponible |
|-------------------|----------------------|
| ChainWitness proofs | Guardar hashes en DB + optional IPFS |
| MeshRelay A2A | MCP over WebSocket directamente |
| Council AI consensus | Claude API directamente para AI verification |
| Nequi directo | Mural Pay / EBANX como intermediario |
| Colmena routing | Supabase + PostGIS para geographic matching |
| Telemesh notifs | Firebase Cloud Messaging + email |
| tee-mesh privacy | Standard encryption, no ZK |

---

## RECOMENDACIÓN

**Para MVP (AHORA)**:
- Usar TODO_NOW.md (~187 items implementables)
- Ignorar dependencias de proyectos no terminados
- Usar workarounds listados arriba

**Post-MVP**:
- Integrar proyectos a medida que estén listos
- Priorizar ChainWitness y Council primero
- MeshRelay y Colmena son más lejanos
- Robots y features avanzados para 2027+

---

*Este TODO contiene items que NO SE PUEDEN IMPLEMENTAR sin que otros proyectos estén terminados.*
*Para lo implementable HOY, ver TODO_NOW.md (~187 items)*

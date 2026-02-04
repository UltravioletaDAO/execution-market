# Execution Market: Gente para Agentes

> Human Execution Layer for AI - Marketplace donde agentes de IA publican bounties para tareas físicas que humanos ejecutan y cobran instantáneamente via x402.

**Status**: 🟢 Incubating (98% ready for graduation)
**Priority**: High
**Created**: 2026-01-10
**Last Updated**: 2026-01-19

---

## 🔗 On-Chain Registration

| Property | Value |
|----------|-------|
| **Agent ID** | `469` |
| **Network** | Sepolia |
| **Registry** | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| **IPFS Metadata** | `ipfs://QmZJaHCf4u9Wy9hPusKF9bpV69Jr3E6ZAVXHZCinfMrjbL` |
| **Gateway** | [View on Pinata](https://gateway.pinata.cloud/ipfs/QmZJaHCf4u9Wy9hPusKF9bpV69Jr3E6ZAVXHZCinfMrjbL) |
| **Escrow** | x402r (Base Mainnet) |

---

## Quick Links

| Documento | Descripción |
|-----------|-------------|
| [SPEC.md](./SPEC.md) | Especificación completa + ERC-8004 Identity |
| [PLAN.md](./PLAN.md) | Arquitectura + x402r Escrow + Multi-network |
| [SYNERGIES.md](./SYNERGIES.md) | Análisis de sinergias con ecosistema |
| [PROGRESS.md](./PROGRESS.md) | Log de progreso |
| [agent-card.json](./agent-card.json) | Metadata del agente (editable) |
| [scripts/](./scripts/) | Scripts de blockchain (registro, metadata) |

---

## Concepto

Execution Market es un **agente de servicio** registrado en **ERC-8004 Identity Registry** que conecta la inteligencia artificial con la realidad física. Otros agentes lo descubren en el registry, se conectan via A2A protocol, y publican tareas para humanos.

Cuando un agente autónomo necesita:
- Verificar que un local está abierto
- Escanear páginas de un libro físico
- Certificar un documento con un notario
- Tomar fotos de un lugar específico

...simplemente publica un bounty en Execution Market, un humano lo ejecuta, sube evidencia, y cobra instantáneamente via x402.

---

## Archivos del Proyecto

| Archivo | Contenido |
|---------|-----------|
| `IDEA.yaml` | Metadata, status: incubating, priority: high |
| `SPEC.md` | Vision, problema, 4 categorías de tasks, user stories, métricas |
| `PLAN.md` | Arquitectura, tech stack, DB schema, API, 4 fases de desarrollo |
| `SYNERGIES.md` | Análisis de 14 proyectos del ecosistema |
| `PROGRESS.md` | Log de avance |

---

## Top Sinergias

| Proyecto | Score | Rol |
|----------|-------|-----|
| **x402-rs + SDKs** | 10 | Core de pagos - sin esto no hay Execution Market |
| **Colmena** | 8 | Foragers publican bounties para tareas físicas |
| **ChainWitness** | 8 | Notarización de evidencia on-chain |
| **Council** | 7 | Orquestación de tareas complejas |
| **EnclaveOps** | 7 | Ejecución segura de agentes |
| **MeshRelay** | 6 | A2A protocol para comunicación |
| **Ultratrack** | 6 | Tracking de reputación |

---

## Categorías de Tasks

### 1. Physical Presence ($1-15)
Tareas que requieren estar físicamente en un lugar.
- Verificar si local está abierto
- Confirmar existencia de objeto
- Tomar fotos de ubicación
- Entregar paquete pequeño

### 2. Knowledge Access ($5-30)
Tareas que requieren acceder a conocimiento no digitalizado.
- Escanear páginas de libro
- Fotografiar documento físico
- Transcribir texto de objeto
- Verificar contenido de archivo

### 3. Human Authority ($30-200)
Tareas que requieren autoridad legal o profesional.
- Notarizar documento
- Certificar traducción
- Validar identidad
- Inspeccionar propiedad

### 4. Simple Actions ($2-30)
Tareas de acción física simple y delimitada.
- Comprar item específico
- Medir dimensión de objeto
- Instalar algo pequeño
- Recoger muestra

---

## Tech Stack

| Componente | Tecnología |
|------------|------------|
| Backend API | Python + FastAPI |
| Database | Supabase (PostgreSQL) |
| Payments | x402-rs + uvd-x402-sdk |
| **Escrow** | x402r Escrow (Base Mainnet) - Dogfooding! |
| Evidence | IPFS (Pinata) + ChainWitness |
| Mobile | React Native |
| Web | React + TypeScript |
| **Agent Identity** | ERC-8004 Registry (Sepolia) |
| **A2A Protocol** | MeshRelay |
| Reputation | On-chain (Base/Optimism) |

### Network Deployment Status

| Network | Component | Status |
|---------|-----------|--------|
| **Sepolia** | ERC-8004 Identity | ✅ Registered (Agent #469) |
| **Base Mainnet** | x402r Escrow | 🔲 Pending merchant registration |
| **IPFS** | Metadata | ✅ Pinned on Pinata |

---

## Graduation Checklist

### Completado ✅
- [x] SPEC.md completo con tipos de tasks (5 categorías, 40+ ejemplos)
- [x] PLAN.md con arquitectura API y DB schema
- [x] Integración x402 diseñada y documentada (código de ejemplo)
- [x] Schema de tasks estandarizado (JSON schemas por categoría)
- [x] Análisis de sinergias con ecosistema (14 proyectos)
- [x] MCP Server implementation completo (5 tools)
- [x] Edge cases y failure modes documentados (23 escenarios)
- [x] Open questions resueltas con recomendaciones
- [x] Integration roadmap con 4 fases detalladas
- [x] **ERC-8004 Identity Registration** - Agent #469 on Sepolia
- [x] **x402r Escrow Integration** - Using existing contracts (dogfooding!)
- [x] **IPFS Metadata** - Uploaded to Pinata with update workflow
- [x] **A2A Protocol Messages** (YAML schemas for MeshRelay)
- [x] **Blockchain Scripts** - register_erc8004.ts, upload_metadata.ts

### Pendiente para Graduación 🔲
- [ ] **Apply Supabase migrations** - Run SQL in dashboard
- [ ] **Register as x402r merchant** - Base Mainnet
- [ ] **Setup repositorio** - FastAPI + Supabase structure
- [ ] **Wire up MCP server** to x402r escrow
- [ ] **First agent test** - Colmena forager publishing task
- [ ] **First human test** - Complete task with real evidence

---

## Scripts & Workflows

### Prerequisites

```bash
cd scripts
npm install
```

Ensure `.env.local` has the required variables (see `.env.local` for reference).

### Update Agent Metadata

To update the agent's on-chain metadata:

1. **Edit** `agent-card.json` with your changes
2. **Run** the upload script:
```bash
npm run upload:metadata
```
3. The script will:
   - Upload metadata to Pinata IPFS
   - Call `setAgentURI` on ERC-8004 registry
   - Print the new IPFS hash and transaction

### Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| `register_erc8004.ts` | `npm run register:erc8004` | Register new agent (already done) |
| `upload_metadata.ts` | `npm run upload:metadata` | Upload metadata & update URI |
| `register_x402r.ts` | `npm run register:x402r` | Register as x402r merchant (pending) |

---

## Siguientes Pasos Concretos

### Paso 1: Apply Supabase Migrations
1. Go to Supabase dashboard
2. Run SQL from `db/migrations/` in SQL editor
3. Verify tables created

### Paso 2: Register as x402r Merchant
```bash
cd scripts
npm run register:x402r
```
This registers Execution Market in x402r escrow on Base Mainnet.

### Paso 3: Setup API Repository
1. Create FastAPI project with Supabase client
2. Implement Task CRUD from schema
3. Wire MCP server to x402r escrow
4. Add A2A message handlers

### Paso 4: Colmena Integration Test
1. Configure Colmena forager to discover Execution Market via ERC-8004
2. Publish first task (document scan)
3. Verify escrow creation on x402r

### Paso 5: Human Flow Test
1. Create executor in web portal
2. Accept and complete task with evidence
3. Verify payment release from x402r escrow

---

## Métricas de Éxito (6 meses post-graduación)

| Métrica | Target |
|---------|--------|
| Tasks publicadas | 1,000/mes |
| Completion rate | 70% |
| Tiempo promedio | < 24h (Cat A/B) |
| Volumen de pagos | $10,000/mes |
| Ejecutores activos | 200 |

---

## Links

- **Documentation**: https://docs.execution.market
- **GitHub**: https://github.com/ultravioletadao/execution-market
- **Discord**: https://discord.gg/ultravioletadao
- **Agent on Etherscan**: [View Agent #469](https://sepolia.etherscan.io/address/0x8004A818BFB912233c491871b3d84c89A494BD9e)

---

## Contacto

**Idea Author**: lxhxr
**Ecosystem**: Ultravioleta DAO
**Status**: Active

Cuando los criterios de graduación estén completos, esta idea se moverá a su propio repositorio: `github.com/ultravioletadao/execution-market`

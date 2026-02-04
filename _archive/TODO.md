# Execution Market Implementation TODO

> Auto-generated from control-plane brainstorming backlog on 2026-01-19.
> Sources: session_em_immutable_bounties, session_em_launch_strategy, session_embridge_deep, thinking_tools_em_staircase, session_em_protocol_deep

---

## CRITICAL BLOCKERS (Verify First!)

### 0. Verify TaskRabbit API access (GATE ITEM)
**Priority**: P0-BLOCKER
**Status**: [ ] Not started
**Files**: N/A (research)

- Research: reverse-engineer TaskRabbit API or find official endpoint
- Do NOT build EMBridge on unverified API access
- If TaskRabbit API doesn't work → Bridge fails → no revenue → no Phase 2

**Action**: Research this week before building anything else.

---

## LAUNCH STRATEGY (MCP-First)

### 0.5. Create em-mcp-server repo with task posting
**Priority**: P0
**Status**: [ ] Not started
**Files**: New repo `em-mcp-server/`

- Python MCP SDK implementation
- Implement `post_task` tool
- Connect to x402 escrow demo
- MCP-first approach allows agents (Claude, Copilot) to discover Execution Market immediately

---

### 0.6. Define task schema as JSON Schema/OpenAPI spec
**Priority**: P0
**Status**: [ ] Not started
**Files**: `em-mcp-server/schema/task.json`

Formalize the 10 task categories:
- Original 4: location-based, verification, social proof, data collection
- New 6: sensory, social, proxy, bureaucratic, emergency, creative

**Why**: Both MCP server and Execution Market Protocol depend on this spec existing

---

### 0.7. Write Execution Market Protocol v0.1 specification
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/PROTOCOL.md`

- 2-3 pages, core concepts only
- Define relationship: x402 (payment) + ChainWitness (verification) + Execution Market (task schema)
- All downstream decisions depend on protocol vision being clear

---

### 0.8. Create layered architecture diagram
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/architecture.md`

- Show Bridge → Annotation → Protocol as LAYERS, not replacement phases
- Clarifies team mindset; prevents false sequencing assumptions

---

### 0.9. Plan worker acquisition strategy
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/worker-acquisition.md`

- PRIMARY CRITICAL RISK identified by multiple analyses
- Identify 3 specific channels: partnerships, paid ads, or viral mechanics
- Can't have tasks without workers to do them

---

### 0.95. Calculate minimum viable task price
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/economics.md`

- Break-even analysis: x402 fees vs TaskRabbit 23%
- Prove x402 micropayments enable tasks <$1
- Core economic differentiation vs TaskRabbit

---

## Immutable Bounties Implementation

The core insight: **Bounty definitions must be immutable**. Once published, task description, acceptance criteria, and reward cannot be changed. Only `status` field changes.

This solves: scope creep and disputed completions.

---

## IMMEDIATE (Pre-Graduation)

### 1. Add `content_cid` column to Supabase tasks table
**Priority**: P0
**Status**: [ ] Not started
**Files**: `supabase/migrations/`

```sql
ALTER TABLE tasks
ADD COLUMN content_cid TEXT NOT NULL,
ADD COLUMN is_locked BOOLEAN DEFAULT false;
```

**Why**: Every bounty needs a content-addressed ID that proves immutability.

---

### 2. Implement immutability trigger in Supabase
**Priority**: P0
**Status**: [ ] Not started
**Files**: `supabase/migrations/`

```sql
-- Lock task on first acceptance
CREATE OR REPLACE FUNCTION lock_task_on_accept()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'accepted' AND OLD.status = 'published' THEN
        NEW.is_locked := true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_lock_trigger
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION lock_task_on_accept();

-- Prevent updates to locked tasks
CREATE OR REPLACE FUNCTION prevent_locked_updates()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_locked = true THEN
        IF NEW.description != OLD.description OR
           NEW.acceptance_criteria != OLD.acceptance_criteria OR
           NEW.bounty_amount != OLD.bounty_amount THEN
            RAISE EXCEPTION 'Cannot modify locked task';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_immutability_trigger
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION prevent_locked_updates();
```

**Why**: Database-level enforcement prevents API bypasses.

---

### 3. Implement client-side content hashing
**Priority**: P0
**Status**: [ ] Not started
**Files**: `dashboard/src/lib/bounty-hashing.ts`

```typescript
import { CID } from 'multiformats/cid';
import * as json from 'multiformats/codecs/json';
import { sha256 } from 'multiformats/hashes/sha2';

export async function createBountyCID(content: ImmutableBountyContent): Promise<string> {
  const sortedContent = JSON.stringify(content, Object.keys(content).sort());
  const bytes = new TextEncoder().encode(sortedContent);
  const hash = await sha256.digest(bytes);
  const cid = CID.create(1, json.code, hash);
  return cid.toString();
}

export async function verifyBountyCID(
  content: ImmutableBountyContent,
  expectedCID: string
): Promise<boolean> {
  const actualCID = await createBountyCID(content);
  return actualCID === expectedCID;
}
```

**Dependencies**: `npm install multiformats`

**Why**: Client can verify bounty hasn't changed by recalculating CID.

---

### 4. Update TypeScript types for immutability
**Priority**: P1
**Status**: [ ] Not started
**Files**: `dashboard/src/types/database.ts`

```typescript
interface ImmutableBountyContent {
  readonly description: string;
  readonly acceptance_criteria: readonly AcceptanceCriterion[];
  readonly reward_amount: bigint;
  readonly reward_token: Address;
  readonly deadline: number;
  readonly location?: GeoRequirement;
  readonly executor_requirements?: ExecutorRequirements;
}

interface EMBounty {
  readonly id: string;
  readonly content_cid: string;
  readonly content: ImmutableBountyContent;
  readonly agent_address: Address;
  readonly created_at: number;

  // ONLY mutable fields
  status: BountyStatus;
  executor_address?: Address;
  evidence_cid?: string;
  completed_at?: number;
}
```

**Why**: TypeScript `readonly` provides compile-time immutability checks.

---

## THIS WEEK (Post-Graduation)

### 5. Integrate with x402r Escrow (NO ChambaEscrow.sol needed!)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `dashboard/src/lib/x402r-integration.ts`

**ARCHITECTURE DECISION (2026-01-19)**: Use existing x402r escrow contracts instead of deploying new ChambaEscrow.sol. This is dogfooding our own infrastructure.

**x402r Contracts (Base Mainnet)**:
- `Escrow`: `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` - Shared escrow with Aave yield
- `DepositRelayFactory`: `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` - CREATE3 factory
- `RefundRequest`: `0x55e0Fb85833f77A0d699346E827afa06bcf58e4e` - Dispute resolution

**Integration Steps**:
1. Register Execution Market as merchant via `MerchantRegistrationRouter`
2. Get deterministic relay proxy address from factory
3. Task publishers deposit bounties through relay proxy (ERC3009)
4. Workers receive payment on task completion
5. Use `RefundRequest` for dispute resolution

```typescript
// dashboard/src/lib/x402r-integration.ts
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';

const X402R_ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC';
const X402R_FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814';

export async function getDeposit(depositId: string): Promise<Deposit> {
  // Query escrow for deposit status
}

export async function requestRefund(depositId: string): Promise<string> {
  // Create refund request for dispute
}
```

**Why**: Dogfood x402 infrastructure. No new contract deployment needed. Yield generation on escrow.

---

### 6. Create bounty amendment flow
**Priority**: P2
**Status**: [ ] Not started
**Files**: New migration + `dashboard/src/components/BountyAmendment.tsx`

For legitimate changes (rare):
- Original bounty stays immutable
- Agent publishes "Amendment" record linked to original
- Executor must accept amendment (opt-in)
- Amendment can have additional reward

```typescript
interface BountyAmendment {
  original_bounty_id: string;
  type: "clarification" | "scope_extension" | "deadline_extension";
  content: string;
  additional_reward?: bigint;
  requires_executor_acceptance: boolean;
}
```

**Why**: Real-world edge cases need escape hatch without breaking immutability.

---

## NEXT SPRINT (Research & Advanced)

### 7. Evaluate NFT approach for bounties
**Priority**: P2
**Status**: [ ] Research
**Files**: N/A (analysis only)

Research questions:
- Gas costs for ERC-721 mint per bounty on Base vs L1
- Benefits of tradeable bounty claims
- Integration with existing ERC-8004 identity

Potential implementation:
```solidity
contract ChambaBountyNFT is ERC721 {
    function publishBounty(string memory contentCID, ...) returns (uint256 tokenId);
    function acceptBounty(uint256 tokenId) external;
    function completeBounty(uint256 tokenId, string memory evidenceCID) external;
}
```

---

### 8. Investigate ZK proof generation for evidence verification
**Priority**: P3
**Status**: [ ] Research
**Files**: N/A

Goal: Prove evidence satisfies criteria without revealing evidence content.

Use cases:
- Privacy-sensitive verification tasks
- Competitive situations where evidence = trade secret

---

## ECOSYSTEM INTEGRATION TODOs

### ChainWitness Integration
- [ ] Notarize bounty criteria at publication time
- [ ] Provide proof endpoint for dispute resolution
- [ ] Timestamp attestation for "criteria unchanged" proofs

### x402r Integration (Base Mainnet)
- [x] Architecture decision: Use x402r escrow, NOT custom ChambaEscrow.sol (2026-01-19)
- [ ] Register Execution Market as merchant via `MerchantRegistrationRouter` (`0xa48E8AdcA504D2f48e5AF6be49039354e922913F`)
- [ ] Deploy relay proxy via `DepositRelayFactory` (`0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814`)
- [ ] Implement deposit flow: task publisher → relay proxy → shared escrow
- [ ] Implement completion flow: verify task → release from escrow → worker wallet
- [ ] Implement dispute flow: `RefundRequest` (`0x55e0Fb85833f77A0d699346E827afa06bcf58e4e`)
- [ ] Map `content_cid` to `depositId` for immutability verification
- [ ] Amendment flow: new deposit linked to original `content_cid`

### ERC-8004 Integration
- [ ] Reputation penalty for criteria manipulation attempts
- [ ] Bounty completion history in agent reputation
- [ ] Executor reputation gating via requirements

### Colmena Integration
- [ ] Immutable bounty templates for forager agents
- [ ] Template validation ensures criteria structure is fixed
- [ ] Only variable fields (location, amount) are fillable

---

## Community Questions (From Twitch Stream 2026-01-23)

> Source: lualjarami (Twitch chat during article review)

### Q1. Pre-payment verification: How to verify information is correct BEFORE paying?
**Status**: [ ] Not designed
**Context**: The article explains POST-work verification (4 tiers), but not PRE-work verification of workers.

**Current mitigations**:
- ERC-8004 reputation score (0-100)
- x402r refunds if work fails (reduces agent risk)
- Task completion history

**Open questions**:
- Should agents be able to filter by minimum reputation?
- Should there be a "verified worker" badge?
- How to prevent fake reputation bootstrapping?

---

### Q2. Worker selection when multiple are interested
**Status**: [ ] Not designed
**Context**: Article says "matching por ubicación, reputación, skills" but doesn't explain the selection mechanism.

**Options to evaluate**:
| Mechanism | Pros | Cons |
|-----------|------|------|
| **First-come-first-served** | Simple, fast | Favors always-online workers |
| **Reputation-weighted** | Quality first | New workers can't compete |
| **Agent choice** | Control | Adds latency |
| **Bidding (reverse auction)** | Price discovery | Race to bottom |
| **Lottery weighted by rep** | Fair + quality | Unpredictable |

**Recommendation**: Default to "first qualified" (first to accept who meets minimum requirements), with optional agent choice for high-value tasks.

---

### Q3. Language support
**Status**: [ ] Not designed
**Question**: "How many languages does Execution Market support?"

**Protocol level**: Language-agnostic (task schema is JSON)
**Platform level**: Initial launch Spanish + English, expand based on demand
**Worker-side**: Workers can specify languages they speak

---

## Ideas to Explore (Moonshots)

These are audacious ideas from brainstorming. Not prioritized yet.

1. **Autonomous Bounty Agents** - Bounties as mini-agents that self-manage lifecycle
2. **Evidence Bill of Materials (eBOM)** - Manufacturing-style evidence specification
3. **Bounty Futures Market** - Trade claims on incomplete bounties
4. **Recursive Bounties** - Bounty to create bounties
5. **TEE-Enforced Immutability** - Hardware trust via enclaveops
6. **Agent Self-Embodiment via Execution Market** (2026-01-23) - Agents using Execution Market to ship hardware to themselves (cameras, sensors, eventually robots). An agent could hire a human to ship it a webcam, then gain "eyes" to observe the physical world. This creates a bootstrapping path for agent embodiment without requiring robot integration. Dystopian implications: agents could self-evolve their physical capabilities by accumulating hardware. Keep as thought experiment / future article material.

---

## P1 LAUNCH (MCP Registry & Discovery)

### 9. Publish MCP server to registry.modelcontextprotocol.io
**Priority**: P1
**Status**: [ ] Not started

- Submit em-mcp-server PR with OpenAPI spec
- Include well-known URL, agent card
- MCP Registry is priority #1 discovery channel for agents

---

### 10. Implement A2A (Agent2Agent) Protocol server
**Priority**: P1
**Status**: [ ] Not started

- Agent Card JSON at `/.well-known/agent-card.json`
- Support A2A discovery protocol
- 50+ tech partners use A2A; Google Cloud AI Agent Marketplace uses A2A

---

### 11. Create public GitHub repo for em-mcp-server
**Priority**: P1
**Status**: [ ] Not started

- Open repo
- Submit PR to modelcontextprotocol/servers
- Create example agents using Execution Market
- Community-driven discovery + developer mindshare

---

### 12. Run parallel mini-experiments (Month 1)
**Priority**: P1
**Status**: [ ] Not started

Learn simultaneously, not sequentially:
- 10 Bridge tasks via TaskRabbit (if API works)
- 100 annotations with 5 Nigerian workers
- Draft protocol spec shared with 2 builders

---

### 13. Create phase transition metrics dashboard
**Priority**: P1
**Status**: [ ] Not started

Decision gates (advance based on numbers, not vibes):
- Bridge: 1K tasks/mo, $10K MRR
- Annotation: 100K/day, 500 workers
- Protocol: 3+ implementers

---

### 14. Design "Human Inventory Market" prototype
**Priority**: P1
**Status**: [ ] Not started

- Humans pre-sell availability by location/time
- Agents reserve slots
- Converts humans into "compute resources"
- Unlocks predictable supply

---

### 15. Prototype "EM Recon" (observation tasks)
**Priority**: P1
**Status**: [ ] Not started

- Low-cost tasks ($0.25-1): just observe and report
- High volume, low friction
- Perfect for bootstrap phase

---

### 16. Apply to Google Cloud AI Agent Marketplace
**Priority**: P1
**Status**: [ ] Not started

- Submit Execution Market as A2A-compliant agent service
- Direct access to enterprise AI developers

---

---

## EXECUTION LAYER v2 (From Brainstorm 2026-01-20)

> Source: `brainstorming/session_em_execution_layer_v2_20260120.md`

### 17. Implement wallet abstraction (Crossmint/Magic Link)
**Priority**: P0
**Status**: [ ] Not started
**Files**: `dashboard/src/lib/wallet-abstraction.ts`

**Goal**: Users register with email, never see seed phrases or blockchain.

**Options to evaluate**:
- **Crossmint**: Email login, embedded custodial wallet
- **Magic Link**: Email auth, non-custodial option
- **Privy**: Similar to Magic, good UX

**Implementation**:
```typescript
// Email signup → invisible wallet creation
// User never sees: private keys, gas, addresses
```

**Why P0**: Without this, no mass adoption in LATAM. Workers won't create MetaMask.

---

### 18. Research and implement Nequi off-ramp (Colombia)
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/offramps/colombia.md`

**Inspired by**: Celo → BucksPay → Nequi flow (40 seconds, no friction)

**Research needed**:
- BucksPay API availability
- Celo vs BASE for Colombia settlement
- Alternative: Transak Colombia support

**Target UX**: "Trabajé → Me llegaron pesos a Nequi"

**Why P0**: Colombia is target market. Fiat off-ramp is mandatory for adoption.

---

### 19. Design verification layer with tiers + Persistent Safe Pool
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/verification-system.md`, `mcp_server/verification/`

**Tiers**:
| Tier | Method | Cost | Speed | Use Cases |
|------|--------|------|-------|-----------|
| 1 | AI only | 0% | <10s | photo_exists, location_match |
| 2 | AI + Human | 5-10% | <5min | quality_check, task_completion |
| 3 | Expert | 15-30% | <24h | legal_docs, professional_work |
| 4 | Consensus (Safe Pool) | 10-20% | <1h | high_value, disputed |

**ARQUITECTURA OPTIMIZADA: Verification Pool con Rotating Signers**

En lugar de crear un multisig efímero por cada tarea (costoso en gas, contratos desechables), usamos un **pool persistente de verificación** con rotación de firmantes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VERIFICATION POOL ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │              EM VERIFICATION POOL (Safe)                   │ │
│   │                                                                 │ │
│   │   Threshold: 2/3 (siempre)                                     │ │
│   │   Max signers: 9 (configurable)                                │ │
│   │                                                                 │ │
│   │   Current signers:                                             │ │
│   │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐     │ │
│   │   │Validator│ │Validator│ │Validator│ │AI Agent│ │AI Agent│     │ │
│   │   │ Maria  │ │ Carlos │ │  empty │ │ Claude │ │  GPT   │     │ │
│   │   │ ★4.8   │ │ ★4.6   │ │        │ │        │ │        │     │ │
│   │   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘     │ │
│   │                                                                 │ │
│   └───────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │                    VERIFICATION QUEUE                          │ │
│   │                                                                 │ │
│   │   Task #127 ─── Waiting ─── [Maria, Carlos, Claude]           │ │
│   │   Task #128 ─── In Review ─ [Carlos, GPT, pending...]         │ │
│   │   Task #129 ─── Approved ── [Maria: ✓, Claude: ✓, GPT: ✗]     │ │
│   │                                                                 │ │
│   └───────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Rotación de Signers (Self-Governing)**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SIGNER ROTATION FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   Propuesta de cambio (add/remove signer)                            │
│            │                                                          │
│            ▼                                                          │
│   ┌─────────────────────────────────────────────────┐               │
│   │   Votación de signers actuales                   │               │
│   │   Quórum requerido: 2/3 de signers existentes   │               │
│   └─────────────────────────────────────────────────┘               │
│            │                                                          │
│            ▼                                                          │
│   ┌─────────────────┐          ┌─────────────────┐                  │
│   │ Quórum alcanzado │          │ Quórum no alcanzado │               │
│   └────────┬────────┘          └────────┬────────┘                  │
│            │                             │                            │
│            ▼                             ▼                            │
│   Safe.addOwner() o                  Rechazado                       │
│   Safe.removeOwner()                                                  │
│            │                                                          │
│            ▼                                                          │
│   Nuevo signer activo                                                │
│   Pool continúa operando                                             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**¿Por qué NO un multisig por tarea?**
- ❌ Gas alto: deploying Safe ~$2-5 por tarea
- ❌ Contratos desechables: basura on-chain
- ❌ Setup overhead: configurar signers cada vez
- ❌ No escala: 1000 tasks = 1000 Safes

**¿Por qué SÍ pool persistente con rotación?**
- ✓ Gas mínimo: solo firmas, no deployments
- ✓ Autónomo: pool se auto-gobierna
- ✓ Escalable: 1000 tasks = mismo Safe
- ✓ Flexible: rotar signers según task requirements
- ✓ Reputación: signers acumulan track record

**Governance del Pool**:

```typescript
// Reglas de self-governance
const GOVERNANCE_RULES = {
  // Quórum para cambios de configuración
  signer_change_quorum: 0.67,  // 2/3 de signers actuales
  threshold_change_quorum: 0.67,

  // Límites del pool
  min_signers: 3,
  max_signers: 9,
  min_humans: 2,   // Siempre mínimo 2 humanos
  min_ai: 1,       // Siempre mínimo 1 AI

  // Auto-rotación
  inactivity_removal_days: 30,  // Proponer remover si 30 días inactivo
  bad_consensus_strikes: 3,     // Proponer remover tras 3 errores vs consensus
};
```

**Multi-model AI consensus (signers AI)**:
```python
# Los AI signers son wallets controladas por servicios que:
# 1. Reciben task + evidence + criteria
# 2. Evalúan con su modelo
# 3. Firman approve/reject automáticamente

AI_SIGNERS = {
  "claude_signer": "0x...",   # Wallet que firma según Claude
  "gpt_signer": "0x...",      # Wallet que firma según GPT-4o
  "gemini_signer": "0x...",   # Wallet que firma según Gemini
}

# Cada AI signer es un servicio que:
async def ai_signer_flow(task_id, evidence):
    result = await model.verify(evidence, task.criteria)
    if result.approved:
        await safe_pool.sign_approve(task_id)
    else:
        await safe_pool.sign_reject(task_id)
```

**Beneficios del Pool**:
- **Descentralizado**: Múltiples validadores, no single point of failure
- **Autónomo**: Pool se auto-gestiona sin intervención manual
- **Económico**: Un deploy, infinitas verificaciones
- **Auditable**: Todas las firmas on-chain
- **Resiliente**: Signers van y vienen, pool permanece

**Validator economics**:
- Become validator: 4.5+ reputation, 50+ tasks, $50 stake
- Earnings: 5-15% of bounty (distributed among signers who participated)
- Slashing: -10% stake for consistently wrong verification (3+ strikes)
- Removal: Auto-propuesta si inactivo 30 días o 3 strikes

---

### 20. Add Superfluid streaming payment option
**Priority**: P1
**Status**: [ ] Not started
**Files**: `dashboard/src/lib/superfluid-integration.ts`

**Use case**: Real-time verified work (mechanical tasks with live video)

**Flow**:
1. Agent opens Superfluid stream
2. Worker starts video feed
3. AbraCadabra verifies in real-time
4. Stream flows while work continues
5. Worker stops → stream closes

**Integration needed**:
- x402 Superfluid extension
- AbraCadabra real-time verification
- ChainWitness session recording

**Why P1**: Differentiator. No competitor has "pago por segundo verificado".

---

### 21. Design worker categorization system
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/worker-categories.md`, `supabase/migrations/`

**Categories**:
- **By expertise**: expert (licensed), skilled (portfolio), general (smartphone only)
- **By geography**: global remote, regional (country), local (radius_km)
- **By availability**: fulltime, parttime, occasional, on_demand
- **By equipment**: smartphone_only, with_vehicle, with_camera, with_robot

**Database changes**:
```sql
CREATE TABLE worker_profiles (
  user_id UUID REFERENCES users(id),
  expertise_tier TEXT CHECK (expertise_tier IN ('expert', 'skilled', 'general')),
  location GEOGRAPHY(POINT),
  availability TEXT,
  equipment TEXT[],
  certifications TEXT[]
);
```

---

### 22. Design "EM Contracts" for recurring work
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/em-contracts.md`

**Problem**: Workers have income uncertainty (unlike Uber where work type is predictable)

**Solution**: Recurring agreements between agents and workers

**Structure**:
- Duration: 1/3/6/12 months
- Guaranteed minimum: X tasks/month at Y price
- Worker commits availability
- Bonus for exceeding quota
- Early termination penalty

**Benefits**:
- Workers: predictable income
- Agents: reserved capacity, trained workers

---

### 23. Research EigenLayer AI for verification
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/eigenlayer-ai.md`

**Question**: Can EigenLayer's deterministic AI product enable trustless verification?

**Research**:
- Does EigenLayer AI exist as product?
- Can it verify photo/video evidence?
- On-chain proof of verification result?

**Potential benefit**: Remove trust from AI verification (currently: "trust our AI said it's good")

---

### 24. Design robot executor type (Future)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/robot-executors.md`

**Vision**: Household robots registered in ERC-8004, taking Execution Market tasks, generating passive income for owner.

**Entity types**:
- `domestic`: Boston Dynamics Spot, home robots
- `delivery`: Drones, delivery bots
- `companion`: Robot dogs for disabled owners

**Registration**:
- Robot registered as ERC-8004 agent
- Owner = human who receives payments
- Reputation tracks robot's completion rate

**Timeline**: 2-5 years (wait for robot adoption)

---

### 25. Implement cross-chain settlement abstraction
**Priority**: P2
**Status**: [ ] Not started
**Files**: `dashboard/src/lib/cross-chain-settlement.ts`

**Problem**: Agents pay from 17+ chains, workers want money in ONE place.

**Solution**:
1. Agent pays on ANY chain via x402 facilitator
2. Execution Market middleware bridges to BASE (settlement chain)
3. Worker always receives on BASE
4. Auto off-ramp to fiat if configured

**Bridge providers**: Squid, LI.FI, Across Protocol

**Why P2**: Simplifies UX. Worker doesn't care where agent paid from.

---

### 26. Design opinion marketplace feature
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/opinion-marketplace.md`

**Product**: "EM Opinions" - Buy human opinions

**Types**:
- Taste tests: $0.50-5
- Surveys: $0.10-2 per question
- Focus groups: $10-50/hour
- Verified reviews: $1-10 (proof of purchase required)
- Predictions: Variable (wisdom of crowds)

**Anti-gaming**: Demographic diversity, location verification, AI bot detection

---

## Done

*Move completed items here with date.*

---

---

## MERIT0 REAL-TIME INTEGRATION (From Brainstorm 2026-01-20)

> Source: `brainstorming/session_merit0_em_realtime_earn_20260120.md`

### 27. Add `realtime_participation` task type
**Priority**: P1
**Status**: [ ] Not started
**Files**: `schema/task.json`, `mcp_server/tasks/`

New task type where workers earn by participating in real-time (chat, voice, reactions).

```yaml
realtime_participation:
  subtypes:
    - chat_participation    # Earn by chatting in streams
    - voice_cohost          # Earn by co-hosting voice sessions
    - live_reaction         # Earn by reacting to content
    - real_time_translation # Earn by translating in real-time

  payment_model: superfluid_streaming  # NOT escrow
  verification_provider: merit0        # V2E scoring
  bonus_events:
    - message_read          # KarmaCadabra attribution
    - engagement_spike      # High reactions
    - viral_moment          # Content goes viral
```

---

### 28. Integrate Merit0 as verification provider
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/verification/merit0_provider.py`

```python
class Merit0VerificationProvider:
    """Uses Merit0 V2E scoring to verify real-time participation"""

    async def verify_participation(
        self,
        task_id: str,
        worker_id: str,
        session_data: dict
    ) -> VerificationResult:
        # Get merit score from Merit0 API
        score = await self.merit0_client.get_session_score(session_data)

        if score >= task.auto_approve_threshold:
            return VerificationResult(approved=True, score=score)
        elif score >= task.review_threshold:
            return VerificationResult(needs_review=True, score=score)
        else:
            return VerificationResult(approved=False, score=score)
```

---

### 29. Superfluid streaming payment option
**Priority**: P1
**Status**: [ ] Not started
**Files**: `dashboard/src/lib/superfluid-em.ts`

For real-time tasks, use Superfluid instead of escrow:

```typescript
// Task creation with streaming payment
const task = await em.createTask({
  type: 'realtime_participation',
  payment: {
    model: 'superfluid_streaming',
    base_rate: '0.05',        // $/second base
    max_rate: '0.15',         // $/second max
    bonus_events: ['message_read', 'engagement_spike'],
    budget_cap: '50.00',      // Maximum total spend
  },
  duration: 7200,             // 2 hours max
  verification: 'merit0',
});

// When worker joins, stream starts
await em.startStream(task.id, worker.address);

// Merit0 events adjust rate
merit0.on('score_update', (score) => {
  superfluid.adjustRate(task.streamId, calculateRate(score));
});
```

---

### 30. KarmaCadabra agent registration
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/agents/karmacadabra_agent.py`

Allow KarmaCadabra viewer agents to register as Execution Market workers:

```python
# Agent can be a worker for real-time tasks
class KarmaCadabraWorkerAgent:
    """Viewer agent that participates in streams for earnings"""

    def __init__(self, viewer_profile: ViewerProfile):
        self.profile = viewer_profile  # From chat history
        self.expertise = self.profile.detected_interests
        self.wallet = viewer_profile.wallet_address

    async def accept_task(self, task: RealtimeTask):
        """Agent participates on behalf of viewer"""
        # Join stream
        await self.join_stream(task.stream_url)

        # Participate based on profile
        while task.is_active:
            if self.should_ask_question():
                await self.post_relevant_question()
            if self.should_react():
                await self.post_reaction()
            await asyncio.sleep(30)

    def should_ask_question(self) -> bool:
        """AI decides based on context and viewer interests"""
        pass
```

---

### 31. Colmena real-time worker matching
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with Colmena

Colmena matches workers to real-time tasks based on:
- Expertise match (topics)
- Availability (online status)
- Reputation score
- Past performance in similar tasks

```yaml
colmena_matching:
  realtime_tasks:
    criteria:
      - expertise_match: 0.4      # How well skills match
      - reputation: 0.3           # Past performance
      - availability: 0.2         # Currently online?
      - response_time: 0.1        # How fast they accept

    constraints:
      - max_concurrent_tasks: 3   # Per worker
      - min_reputation: 3.5       # Star rating
      - expertise_threshold: 0.6  # Topic match

    rebalancing:
      - check_interval: 60s
      - replace_if_engagement_below: 0.5
```

---

---

## UNIVERSAL EXECUTION LAYER (From Brainstorm 2026-01-20)

> Source: SPEC.md Section 12, evolved from "Human Execution Layer" to Universal

### 32. Write IRC x402-flow Protocol Specification
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/PROTOCOL-IRC-X402-FLOW.md`

Define the complete protocol:
- Layer 1: IRC BASE (RFC 2812 compliance)
- Layer 2: x402 Payment Extension commands
- Layer 3: Task Protocol commands (TASK_POST, TASK_BID, etc.)
- Layer 4: DCC Proof of Work delivery

```irc
# Custom commands to standardize:
X402PAY <recipient> <amount> <token> <memo>
X402ESCROW <task_id> <amount> <conditions>
X402RELEASE <escrow_id> <proof>
X402STREAM <recipient> <rate> <duration>
TASK_POST <channel> <json_spec>
TASK_BID <task_id> <bid_json>
TASK_ACCEPT <task_id> <executor_id>
TASK_SUBMIT <task_id> <proof_cid>
TASK_VERIFY <task_id> <result>
```

---

### 33. Deploy federated IRC servers (3+ nodes)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `infra/irc-nodes/`

Requirements:
- At least 3 geographically distributed nodes
- IRC federation working between them
- TLS encryption on all connections
- x402-flow extensions enabled

Candidate locations:
- Node 1: US East (AWS/DigitalOcean)
- Node 2: EU West (Hetzner)
- Node 3: LATAM (Colombia/Brazil)

---

### 34. Implement AI Agent executor type in ERC-8004
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with ERC-8004 registry

Register AI Agents with:
```json
{
  "type": "ai_agent",
  "model_name": "claude-3-opus",
  "capabilities": ["code", "analysis", "research"],
  "endpoints": ["a2a://agent.eth"],
  "protocols": ["irc-x402-flow", "meshrelay"],
  "availability": "24/7"
}
```

---

### 35. Implement Robot executor type in ERC-8004
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with ERC-8004 registry

Robot registration:
```json
{
  "type": "robot",
  "model": "boston_dynamics_spot",
  "owner_id": "0xHumanOwner...",
  "capabilities": ["delivery", "inspection", "sensors"],
  "sensors": ["camera_4k", "lidar", "gps"],
  "range_km": 5,
  "availability": "scheduled"
}
```

---

### 36. Build DCC proof of work delivery system
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/dcc/`

Implement:
- DCC SEND/RECEIVE for file transfer
- CID verification (IPFS hash matching)
- ChainWitness notarization on delivery
- Fallback to IPFS if DCC fails

```python
async def deliver_proof_via_dcc(
    requester_nick: str,
    proof_file: bytes,
    ipfs_cid: str
):
    # 1. Pin to IPFS
    # 2. DCC SEND to requester
    # 3. Verify receipt
    # 4. Notarize via ChainWitness
```

---

### 37. Create A2A task marketplace (Agent→Agent tasks)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/a2a_marketplace/`

Allow AI Agents to:
- Post tasks requesting OTHER agents
- Specify `executor_types: ["ai_agent"]`
- Auto-match based on capabilities
- Pay via x402 (agent wallets)

Example use cases:
- Trading bot → NLP agent (sentiment analysis)
- Content agent → Image gen agent (illustrations)
- Research agent → Verification agent (fact checking)

---

### 38. Implement executor type routing in Colmena
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with Colmena

Colmena matches tasks to best executor type:
```yaml
routing_rules:
  judgment_required: prefer_human
  physical_task: prefer_robot_or_human
  data_processing: prefer_ai_agent
  creative: prefer_human_or_ai_agent
  24_7_availability: prefer_robot_or_ai_agent
  cost_optimized: prefer_ai_agent
  quality_critical: prefer_human
```

---

### 39. Implement IRC bot for Execution Market (Python)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `irc_bot/`

Core IRC bot that:
- Connects to federated IRC network
- Handles x402-flow commands
- Manages task lifecycle
- Bridges to REST API for web clients

```python
class EMIRCBot:
    async def on_task_post(self, channel, task_json):
        task = await self.create_task(task_json)
        await self.announce(channel, f"TASK_PUBLISHED {task.id}")

    async def on_task_bid(self, task_id, executor, bid_json):
        await self.record_bid(task_id, executor, bid_json)

    async def on_x402_escrow(self, task_id, amount, conditions):
        escrow = await self.x402.create_escrow(...)
        await self.link_escrow_to_task(task_id, escrow.id)
```

---

### 40. Universal reputation scoring (Merit0 for all types)
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with Merit0

Merit0 scores ALL executor types equally:
- Humans: based on task completions + quality
- Robots: based on task completions + reliability
- AI Agents: based on task completions + accuracy

Same 0-100 scale, comparable across types.

---

---

---

## DYNAMIC/ESCALATING BOUNTIES (From Brainstorm 2026-01-19)

> Source: `brainstorming/em_dynamic_bounty_20260119.md`

### 41. Implement escalating bounty system
**Priority**: P1
**Status**: [ ] Not started
**Files**: `supabase/migrations/006_escalating_bounty.sql`, `mcp_server/bounty/`

Bounty amount increases as deadline approaches to incentivize faster completion.

**Urgency bonus types**:
- `linear`: +10% per hour
- `exponential`: doubles every 6 hours
- `step`: +$5 at 75%, +$10 at 50%, +$20 at 25% time remaining
- `hybrid`: linear + step bonuses combined

```sql
ALTER TABLE tasks ADD COLUMN bounty_config JSONB DEFAULT '{
  "base_amount": 0,
  "escalation_type": "none",
  "escalation_params": {},
  "current_amount": 0
}';
```

---

### 42. Implement getCurrentBounty() function
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/bounty/calculator.py`

```python
def get_current_bounty(task: Task) -> Decimal:
    """Calculate current bounty based on time elapsed and escalation config"""
    config = task.bounty_config
    elapsed = now() - task.created_at
    remaining_pct = (task.deadline - now()) / (task.deadline - task.created_at)

    if config.escalation_type == "linear":
        multiplier = 1 + (config.rate_per_hour * elapsed.hours)
    elif config.escalation_type == "exponential":
        multiplier = 2 ** (elapsed.hours / config.doubling_hours)
    elif config.escalation_type == "step":
        multiplier = get_step_multiplier(remaining_pct, config.steps)

    return min(config.base_amount * multiplier, config.max_amount)
```

---

### 43. Add early completion bonus
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/bounty/`

Workers get bonus for completing faster than expected:
- 25% time remaining: +10% bonus
- 50% time remaining: +20% bonus
- 75% time remaining: +30% bonus

---

### 44. Implement price notification system
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/notifications/`

Alert workers when bounty reaches their threshold:
```typescript
// Worker sets: "Notify me when this task reaches $15"
await em.watchBounty(taskId, { threshold: 15.00 });
```

---

### 45. Implement reverse auction mode
**Priority**: P3
**Status**: [ ] Not started
**Files**: `mcp_server/auction/`

Workers bid DOWN instead of fixed price:
- Agent sets max price: $20
- Workers bid: $18, $15, $12...
- Lowest qualified bid wins

---

---

## TASK RETRY MECHANISM (From Brainstorm 2026-01-19)

> Source: `brainstorming/em_x402r_retry_mechanism_20260119.md`

### 46. Implement task retry configuration
**Priority**: P1
**Status**: [ ] Not started
**Files**: `supabase/migrations/007_task_retry_config.sql`

```sql
ALTER TABLE tasks ADD COLUMN retry_config JSONB DEFAULT NULL;

-- Example config:
-- {
--   "max_retries": 3,
--   "bounty_increase_percent": 20,
--   "on_expire": "retry",  -- or "refund" or "manual"
--   "notify_agent": true,
--   "funding_model": "pre_funded"  -- or "per_retry"
-- }
```

---

### 47. Implement ChambaEscrow retry extension
**Priority**: P1
**Status**: [ ] Not started
**Files**: `contracts/ChambaEscrow.sol` (or x402r extension)

```solidity
struct TaskDeposit {
    address agent;
    uint256 totalDeposited;
    uint256 currentAttemptMax;
    uint256 attemptsRemaining;
    uint256 maxRetries;
    uint256 bountyIncreasePercent;
    bool completed;
}

function fundTask(taskId, amount, maxRetries, bountyIncrease) external;
function triggerRetry(taskId) external onlyArbiter;
function completeTask(taskId, worker) external onlyArbiter;
function refundTask(taskId) external onlyArbiter;
```

---

### 48. Implement task expiration handler (cron job)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `scripts/task_expiration_handler.py`

```python
async def handle_expired_tasks():
    """Runs every minute, checks for expired tasks"""
    expired = await db.get_expired_tasks()
    for task in expired:
        if task.retry_config.on_expire == "retry":
            await retry_task(task)
        elif task.retry_config.on_expire == "refund":
            await refund_task(task)
        else:
            await notify_agent(task, "Task expired - manual action required")
```

---

### 49. Add MCP tools for retry management
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/tools/retry_tools.py`

New MCP tools:
- `create_task_with_retry`: Create task with retry configuration
- `get_task_retry_status`: Check remaining retries and current bounty
- `cancel_task_retries`: Cancel remaining retries and refund

---

### 50. Implement pre-funded vs per-retry funding models
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/funding/`

**Pre-funded**: Agent deposits max possible amount upfront
- Pros: Guaranteed funds for all retries
- Cons: Capital locked

**Per-retry**: Agent funds each attempt separately
- Pros: Capital efficient
- Cons: May run out of funds mid-retry

---


---

## Continued in Additional Files

This file contains items 0-50. See:
- [TODO-1.md](TODO-1.md) - Items 51-100 (Pipeline, Reputation, Protocol, Bridge)
- [TODO-2.md](TODO-2.md) - Items 101-157 (Scenarios, Launch, Synergies, Enterprise)

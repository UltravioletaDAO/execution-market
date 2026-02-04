# Execution Market TODO - Part 1 (Items 51-100)

> Pipeline, Reputation, Bounties Extended, Protocol, EMBridge
>
> See also: [TODO.md](TODO.md) (Items 0-50), [TODO-2.md](TODO-2.md) (Items 101-157)

---

## TASK PIPELINE (From Brainstorm 2026-01-19)

> Source: `brainstorming/em_task_pipeline_20260119.md`

### 51. Implement task processing pipeline
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/pipeline/`

Full pipeline: original_request → verify executability → translate → publish → verify evidence

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TASK PROCESSING PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   AGENT REQUEST              EM PROCESSING           EXECUTION   │
│   ─────────────              ─────────────────           ─────────   │
│                                                                       │
│   "Necesito que alguien     ┌─────────────────┐                      │
│    vaya a la tienda X       │ 1. PARSE         │     Worker sees:    │
│    y me diga si tienen      │    Extract intent │     "Verify if     │
│    el producto Y"           └────────┬─────────┘      store X has    │
│          │                           │                 product Y"    │
│          │                  ┌────────▼─────────┐                     │
│          └─────────────────►│ 2. VERIFY        │                     │
│                             │    Executability  │                     │
│                             │    check (LLM)    │                     │
│                             └────────┬─────────┘                     │
│                                      │                                │
│                             ┌────────▼─────────┐                     │
│                             │ 3. TRANSLATE     │                     │
│                             │    Multi-language │                     │
│                             └────────┬─────────┘                     │
│                                      │                                │
│                             ┌────────▼─────────┐                     │
│                             │ 4. PUBLISH       │                     │
│                             │    To marketplace │                     │
│                             └──────────────────┘                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 52. Implement executability verification (LLM checks)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/pipeline/executability.py`

```python
async def verify_executability(task: Task) -> ExecutabilityResult:
    """LLM checks if task is actually doable"""
    prompt = f"""
    Analyze this task for executability:
    {task.description}

    Check:
    1. Is this physically possible?
    2. Is this legal?
    3. Are requirements clear enough?
    4. Can evidence be provided?
    """
    result = await llm.analyze(prompt)
    return ExecutabilityResult(
        is_executable=result.score > 0.7,
        issues=result.issues,
        suggestions=result.suggestions
    )
```

---

### 53. Implement multi-language translation system
**Priority**: P1
**Status**: [ ] Not started
**Files**: `supabase/migrations/008_task_translations.sql`, `mcp_server/pipeline/translate.py`

```sql
CREATE TABLE task_translations (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    language_code TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    acceptance_criteria JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_translations_task_lang ON task_translations(task_id, language_code);
```

Auto-translate tasks to: Spanish, Portuguese, English, French (initial set).

---

### 54. Preserve original_request in task
**Priority**: P1
**Status**: [ ] Not started
**Files**: `supabase/migrations/`

```sql
ALTER TABLE tasks ADD COLUMN original_request TEXT;
ALTER TABLE tasks ADD COLUMN processing_status TEXT DEFAULT 'raw';
-- processing_status: raw → parsed → verified → translated → published
```

Store original agent request verbatim for evidence comparison.

---

### 55. Implement evidence verification vs original
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/verification/original_match.py`

Compare submitted evidence against ORIGINAL request, not processed version:
```python
async def verify_against_original(task: Task, evidence: Evidence) -> bool:
    """Verify evidence satisfies original_request, not just processed description"""
    return await llm.compare(task.original_request, evidence)
```

---

### 56. Implement Assist Service (Premium)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/assist/`

Premium feature: Real-time AI guidance during task execution.

```sql
CREATE TABLE assist_sessions (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    worker_id UUID REFERENCES users(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    messages JSONB DEFAULT '[]',
    cost_accrued DECIMAL(10,4) DEFAULT 0
);
```

---

### 57. Add executability_checks table
**Priority**: P2
**Status**: [ ] Not started
**Files**: `supabase/migrations/`

```sql
CREATE TABLE executability_checks (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    is_executable BOOLEAN,
    score DECIMAL(3,2),
    issues JSONB,
    suggestions JSONB
);
```

---

---

## GLOBAL REPUTATION / SEALS (From Brainstorm 2026-01-19)

> Source: `brainstorming/em_global_reputation_20260119.md`

### 58. Implement ERC-8004-BIDIRECTIONAL extension
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with ERC-8004

Extend ERC-8004 to support bidirectional reputation:
- Workers can rate agents (not just agents rating workers)
- "Agent reliability score" - does agent pay on time?

---

### 59. Implement SealRegistry contract
**Priority**: P1
**Status**: [ ] Not started
**Files**: `contracts/SealRegistry.sol`

```solidity
contract SealRegistry {
    struct Seal {
        bytes32 sealType;      // SKILL, WORK, BEHAVIOR, ENGAGEMENT
        address subject;        // Who received the seal
        address issuer;         // Who issued the seal
        uint256 timestamp;
        bytes metadata;         // Seal-specific data
    }

    mapping(address => Seal[]) public seals;

    function issueSeal(address subject, bytes32 sealType, bytes metadata) external;
    function aggregateScore(address subject) external view returns (uint256);
}
```

---

### 60. Human registration in ERC-8004
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with ERC-8004

Register humans (workers) in IdentityRegistry:
```json
{
  "type": "human",
  "verification_level": "basic|kyc|premium",
  "location_verified": true,
  "skills": ["photography", "spanish", "notarization"],
  "availability": "parttime"
}
```

---

### 61. Implement seal aggregation system
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/reputation/`

Aggregate seals into single reputation score:
```python
def calculate_reputation(seals: List[Seal]) -> int:
    """Weighted aggregation of seals"""
    weights = {
        "SKILL": 1.0,
        "WORK": 1.5,      # Task completion matters most
        "BEHAVIOR": 1.2,  # Responsiveness, communication
        "ENGAGEMENT": 0.5
    }
    score = sum(seal.value * weights[seal.type] for seal in seals)
    return min(100, score)  # Cap at 100
```

---

### 62. Implement MASTER_WORKER badge
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/badges/`

Special badge for top performers:
- 50+ completed tasks
- 4.8+ average rating
- <5% dispute rate
- Active 6+ months

Unlocks:
- Priority task matching
- Higher bounty visibility
- Validator eligibility

---

### 63. Implement Sealed Reputation via TEE
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with enclaveops

Use TEE to compute aggregate reputation without revealing individual seals:
```
Worker's seals → TEE → Aggregate score only
(individual feedback remains private)
```

---

### 64. Add executor_seals table
**Priority**: P1
**Status**: [ ] Not started
**Files**: `supabase/migrations/`

```sql
CREATE TABLE executor_seals (
    id UUID PRIMARY KEY,
    executor_id UUID REFERENCES users(id),
    seal_type TEXT CHECK (seal_type IN ('SKILL', 'WORK', 'BEHAVIOR', 'ENGAGEMENT')),
    issuer_id UUID,
    task_id UUID REFERENCES tasks(id),
    value INTEGER CHECK (value >= 0 AND value <= 100),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- Seals decay over time
);

CREATE INDEX idx_seals_executor ON executor_seals(executor_id);
```

---

### 65. Implement seal decay mechanism
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/reputation/decay.py`

Seals lose value over time (6-month half-life):
```python
def get_seal_value(seal: Seal) -> float:
    age_months = (now() - seal.created_at).months
    decay_factor = 0.5 ** (age_months / 6)  # Half-life of 6 months
    return seal.original_value * decay_factor
```

---

### 66. Implement minimum threshold system
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/reputation/`

Verification tiers based on seals:
- 0 seals: Unverified (limited tasks)
- 3+ seals: Verified Worker
- 10+ seals: Trusted Worker
- 25+ seals: Master Worker

---

### 67. Tribunal integration for disputes
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with tribunal

When verification fails or disputes arise:
1. Case submitted to Tribunal
2. Random validators assigned
3. Evidence reviewed
4. Majority vote decides outcome
5. Loser's stake slashed

---

---

## IMMUTABLE BOUNTIES (Extended) (From Brainstorm 2026-01-19)

> Source: `brainstorming/session_em_immutable_bounties_20260119.md`

### 68. Implement versioned bounties (Git-style linking)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/bounty/versioning.py`

Amendments link to original via parent CID:
```json
{
  "parent_cid": "QmOriginal...",
  "version": 2,
  "changes": ["extended_deadline", "increased_bounty"],
  "content": {...}
}
```

---

### 69. Research Chainlink Oracle-Verified Completion
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/chainlink-verification.md`

Use Chainlink Functions to verify task completion externally:
- Call external API to confirm evidence
- On-chain verification result
- Trustless completion triggering payment

---

### 70. Implement time-locked mutability
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/bounty/`

Tasks editable for X hours after creation, then locked:
```sql
ALTER TABLE tasks ADD COLUMN edit_window_hours INTEGER DEFAULT 1;
-- Task locked after: created_at + edit_window_hours
```

---

### 71. Research multi-sig bounty updates
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/multisig-updates.md`

Critical changes require multiple signatures:
- Agent proposes change
- Worker must co-sign
- Third party (validator) may be required

---

### 72. Implement bounty bonds (slashable stake)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `contracts/`, `mcp_server/bonds/`

Publishers stake bond that gets slashed for:
- Unreasonable rejection of valid evidence
- Changing requirements after acceptance
- Non-payment after valid completion

---

### 73. Implement Merkle Tree evidence
**Priority**: P3
**Status**: [ ] Not started
**Files**: `mcp_server/evidence/merkle.py`

Compound proofs for complex tasks:
```
Task Evidence Root
├── Photo proof (hash)
├── Location proof (hash)
├── Timestamp proof (hash)
└── Additional metadata (hash)
```

---

### 74. DAO-governed exceptions
**Priority**: P3
**Status**: [ ] Not started
**Files**: Integration with EM DAO

Edge cases voted on by DAO:
- Worker requests exception
- DAO votes (token holders)
- If approved, bounty modified despite immutability

---

### 75. Implement seal-gated bounties
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/bounty/gating.py`

Tasks require specific seals to claim:
```json
{
  "required_seals": ["SKILL:photography", "BEHAVIOR:responsive"],
  "min_seal_score": 50
}
```

---

---

## EXECUTION MARKET PROTOCOL (Open Standard) (From Brainstorm 2026-01-12)

> Source: `brainstorming/session_em_protocol_deep_20260112_1230.md`

### 76. Implement EM DID (Decentralized Worker Identity)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `protocol/did/`

Every worker has portable identity: `did:em:worker123`
- Works across all EM-compatible marketplaces
- Reputation portable between platforms

```json
{
  "@context": "https://em.protocol/v1",
  "id": "did:em:worker123",
  "type": "EMIdentity",
  "attestations": [...],
  "reputation_score": 87
}
```

---

### 77. Research EM Gossip (P2P Task Routing)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/gossip-protocol.md`

Tasks propagate via libp2p gossip, no central server:
- Fully censorship-resistant task marketplace
- Prototype gossipsub for task announcements

---

### 78. Implement EM Attestations (EAS schema)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `contracts/EASSchemas.sol`

Deploy EAS schemas for Execution Market skills:
```solidity
// Skill attestation schema
bytes32 constant SKILL_SCHEMA = keccak256(
    "string skillName,uint8 proficiency,address issuer,uint256 timestamp"
);
```

---

### 79. Research Protocol-Level UBI
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/protocol-ubi.md`

Tiny fee (0.1%) on all tasks goes to worker welfare fund:
- Universal Basic Income for gig workers
- Funded by protocol activity

---

### 80. Research Task Derivatives
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/task-derivatives.md`

Financial instruments on task completion rates:
- Hedge marketplace risk
- Speculate on task categories

---

### 81. Research Retroactive Reputation Import
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/research/reputation-import.md`

Scrape TaskRabbit/Fiverr profiles, mint as EM attestations:
- Bootstrap network effect
- Workers start with existing reputation

---

### 82. Define protocol governance model
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/GOVERNANCE.md`

Transition plan:
1. Phase 1: Benevolent Dictator (Ultravioleta DAO)
2. Phase 2: Multi-Stakeholder DAO (workers, agents, platforms)
3. Future: Consider Futarchy or Technical Meritocracy

---

### 83. Build reference implementation SDKs
**Priority**: P1
**Status**: [ ] Not started
**Files**: `sdk/python/`, `sdk/typescript/`

- Python SDK for server implementations
- TypeScript SDK for web/node clients
- Test suite for protocol compliance

---

### 84. Define JSON-LD context
**Priority**: P1
**Status**: [ ] Not started
**Files**: `protocol/context/em-v1.jsonld`

```json
{
  "@context": {
    "em": "https://em.protocol/v1#",
    "Task": "em:Task",
    "Evidence": "em:Evidence",
    "Reputation": "em:Reputation"
  }
}
```

---

### 85. Formalize state machine definition
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/STATE_MACHINE.md`

Document complete task lifecycle:
```
CREATED → PUBLISHED → ACCEPTED → IN_PROGRESS → SUBMITTED →
  → APPROVED → COMPLETED (payment)
  → REJECTED → (retry or refund)
  → DISPUTED → RESOLVED_FOR_EXECUTOR | RESOLVED_FOR_PUBLISHER
```

---

### 86. Research Lit Protocol integration
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/lit-protocol.md`

Encrypted task details, decrypt on claim:
- Privacy for sensitive tasks
- Only accepted worker sees full details

---

### 87. Research UMA Oracle for disputes
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/uma-disputes.md`

Decentralized dispute resolution via UMA:
- No centralized arbitration
- Market-based truth discovery

---

### 88. Research Hyperlane cross-chain tasks
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/hyperlane.md`

Post task on any chain, execute on any chain:
- True multi-chain support
- Agent pays on Ethereum, worker receives on Polygon

---

### 89. Research protocol token (EM)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/protocol-token.md`

Token for governance + staking:
- Marketplaces stake to participate
- Workers stake for reputation boost
- Governance voting rights

**Decision needed**: Token or no token?

---

---

## EMBRIDGE (Middleware) (From Brainstorm 2026-01-12)

> Source: `brainstorming/session_embridge_deep_20260112_1230.md`

### 90. Build TaskRabbit adapter (unofficial API)
**Priority**: P1 (if API works)
**Status**: [ ] Not started
**Files**: `bridge/adapters/taskrabbit.py`

```python
class TaskRabbitAdapter(PlatformAdapter):
    async def create_task(self, task: EMTask) -> str:
        tr_task = self.convert_to_taskrabbit_format(task)
        result = await self.client.post("/tasks", tr_task)
        return result["id"]

    async def get_status(self, platform_task_id: str) -> TaskStatus:
        pass

    async def get_result(self, platform_task_id: str) -> TaskResult:
        pass
```

---

### 91. Build Fiverr adapter
**Priority**: P2
**Status**: [ ] Not started
**Files**: `bridge/adapters/fiverr.py`

---

### 92. Build MTurk adapter
**Priority**: P2
**Status**: [ ] Not started
**Files**: `bridge/adapters/mturk.py`

---

### 93. Implement ML-powered routing
**Priority**: P2
**Status**: [ ] Not started
**Files**: `bridge/routing/ml_router.py`

```python
class MLRouter:
    """Machine learning model that learns optimal routing over time"""

    def predict_best_platform(self, task: Task) -> Tuple[Platform, float]:
        features = self.extract_features(task)
        predictions = self.model.predict_proba(features)
        best_idx = predictions.argmax()
        return PLATFORMS[best_idx], predictions[best_idx]

    def update(self, task: Task, platform: Platform, success: bool):
        """Update model with new outcome data"""
        self.training_data.append({...})
        if len(self.training_data) > RETRAIN_THRESHOLD:
            self.retrain()
```

---

### 94. Implement platform health monitoring
**Priority**: P2
**Status**: [ ] Not started
**Files**: `bridge/monitoring/`

Track platform availability and performance:
- Response time
- Error rates
- Completion rates
- Auto-disable unhealthy platforms

---

### 95. Implement A/B testing framework
**Priority**: P3
**Status**: [ ] Not started
**Files**: `bridge/testing/`

Split tasks across platforms, measure quality:
```python
async def ab_test_platforms(task: Task, platforms: List[Platform]):
    """Send same task to multiple platforms, compare results"""
    results = await asyncio.gather(*[p.create_task(task) for p in platforms])
    # Track completion time, quality, cost
    await record_ab_results(task.id, results)
```

---

### 96. Implement geographic routing
**Priority**: P2
**Status**: [ ] Not started
**Files**: `bridge/routing/geographic.py`

Route to platform strong in that region:
- TaskRabbit: US, UK, EU
- Rappi: LatAm
- Grab: SE Asia
- Local networks: Everywhere else

---

### 97. Implement skill-based routing
**Priority**: P2
**Status**: [ ] Not started
**Files**: `bridge/routing/skill.py`

Route to platform best for that skill:
- Photography: Fiverr
- Handyman: TaskRabbit
- Data labeling: MTurk
- General errands: Rappi

---

### 98. Research Overflow Marketplace
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/overflow.md`

Platforms send us tasks they can't fill:
- Turns competitors into partners
- We route to other platforms or native workers

---

### 99. Research Virtual Platform Illusion
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/virtual-platform.md`

Agents think they're using "TaskRabbit API" but it's EMBridge:
- Zero behavior change for agents
- Build TaskRabbit-compatible API surface

---

### 100. Research Platform Arbitrage
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/research/arbitrage.md`

Real-time arbitrage between platforms:
- Task costs $10 on TaskRabbit, $8 on Thumbtack
- Route and pocket difference

---

### 101. Implement Platform Failure Insurance
**Priority**: P3
**Status**: [ ] Not started
**Files**: `bridge/insurance/`

If platform fails to deliver, we guarantee completion:
- Charge premium for guarantee
- Fallback to native workers or other platforms

---


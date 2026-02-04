# Execution Market TODO - Part 2 (Items 101-157)

> Agent Scenarios, Launch Strategy, Staircase, Concepts, Ecosystem Synergies, EM CHIMBA, Enterprise
>
> See also: [TODO.md](TODO.md) (Items 0-50), [TODO-1.md](TODO-1.md) (Items 51-100)

---

## AGENT SCENARIOS (From Brainstorm 2026-01-11)

> Source: `brainstorming/session_em_agent_scenarios_20260111_1500.md`

### 102. Implement "Agent Eyes" concept (AR glasses avatar)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/agent-eyes.md`

Worker wears AR glasses, agent sees through them in real-time:
- Agent guides worker step-by-step
- Live video + overlays
- Highest-value tasks

---

### 103. Design "Human Inventory Market"
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/concepts/human-inventory.md`

Humans pre-sell availability by location/time:
- Agents reserve slots in advance
- Predictable supply for agents
- Predictable income for workers

```typescript
// Worker lists availability
await em.listAvailability({
  worker: myAddress,
  location: { lat: 40.7, lng: -74.0, radius_km: 5 },
  times: [
    { day: "monday", hours: [9, 10, 11, 14, 15, 16] },
    { day: "tuesday", hours: [9, 10, 11] }
  ],
  min_price: 10.00,  // Per hour slot
});

// Agent reserves slot
await em.reserveSlot(workerId, "monday", 10);
```

---

### 104. Design "Self-Eliminating Tasks"
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/self-eliminating.md`

Tasks that train their own automation:
- Human does task, creates training data
- Eventually AI/robot can do it
- Worker earns less but task volume increases

---

### 105. Implement "EM Recon" (observation tasks)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/task_types/recon.py`

Pure observation tasks:
- Just observe and report
- $0.25-1 per task
- High volume, low friction
- Perfect for bootstrap phase

Examples:
- "Is this store open?"
- "How many people in line?"
- "What's the sign say?"

---

### 106. Design "EM Trials" (experience testing)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/concepts/trials.md`

Hire humans to experience something and report:
- Visit restaurant, report on experience
- Test product, provide feedback
- Shop at store, evaluate service

---

### 107. Design "Last Mile as a Service"
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/concepts/last-mile.md`

Agents coordinate last-mile delivery:
- Package arrives at hub
- Human picks up, delivers to final address
- Compete with Amazon Flex

---

### 108. Design "EM Prime" (premium tier)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/concepts/prime.md`

Premium worker tier:
- Background checked
- Insured
- SLA guarantees
- Higher rates, higher trust

---

### 109. Design gamified progression system
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/gamification/`

Worker progression:
- Levels: Novice → Apprentice → Skilled → Expert → Master
- Badges for achievements
- Leaderboards by category/region
- Unlocks higher-paying tasks

---

---

## LAUNCH STRATEGY (Extended) (From Brainstorm 2026-01-14)

> Source: `brainstorming/session_em_launch_strategy_20260114.md`

### 110. Define task type tiers
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/task-tiers.md`

**Tier 1** (Low barrier, high volume):
- Verification/existence checks ($1-5)
- Photo tasks ($2-10)
- Simple observations ($0.25-2)

**Tier 2** (Medium barrier):
- Document handling ($10-30)
- Sample collection ($15-50)
- Detailed inspections ($20-75)

**Tier 3** (High barrier):
- Professional services ($50-500)
- Licensed work ($100-1000)
- Complex multi-step ($200+)

---

### 111. Create integration guides for platforms
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/integrations/`

Guides for:
- Zapier integration
- n8n integration
- CrewAI integration
- LangChain integration

---

### 112. Design dashboard mockups
**Priority**: P1
**Status**: [ ] Not started
**Files**: `dashboard/mockups/`

Three views:
1. **Agent Portal**: Task creation, monitoring, analytics
2. **Worker App**: Available tasks, earnings, reputation
3. **Admin Dashboard**: Platform health, disputes, metrics

---

### 113. Create 8-week launch sequence
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/LAUNCH_PLAN.md`

**Week 1-2**: MCP Server + basic task types
**Week 3-4**: Agent onboarding (Colmena, Council)
**Week 5-6**: Worker onboarding (LatAm focus)
**Week 7-8**: Public beta + MCP Registry listing

---

### 114. Define tech stack recommendation
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/TECH_STACK.md`

- Backend: Python (FastAPI) + Supabase
- Payments: x402r (existing)
- Identity: ERC-8004 (existing)
- MCP: Python SDK
- Frontend: Next.js + React
- Mobile: React Native or PWA

---

---

## STAIRCASE STRATEGY (From Thinking Tools Analysis)

> Source: `brainstorming/thinking_tools_em_staircase_20260112.md`

### 115. Implement phase transition logic
**Priority**: P1
**Status**: [ ] Not started
**Files**: `scripts/phase_transition.py`

```python
class PhaseTransition:
    def __init__(self, current_phase, metrics, thresholds):
        self.phase = current_phase
        self.metrics = metrics
        self.thresholds = thresholds

    def should_advance(self) -> bool:
        return all(
            self.metrics[k] >= self.thresholds[k]
            for k in self.thresholds
        )

    def advance(self):
        if self.should_advance():
            self.phase = NEXT_PHASE[self.phase]
            return True
        return False
```

---

### 116. Build mobile-first, offline-capable app
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mobile/`

Global South reality demands:
- Works on low-end smartphones
- Offline task caching
- Low bandwidth mode
- SMS fallback for notifications

---

### 117. Define behavioral tests (not just surveys)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/research/behavioral-tests.md`

Test actual behavior, not stated preferences:
```
Group A: Offered $5 via PayPal (3-day delay)
Group B: Offered $4.50 via USDC (instant)

Measure: Which do they choose?
If B wins by >60%, crypto-instant hypothesis confirmed.
```

---

### 118. Hire/partner for enterprise sales
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/hiring/`

Annotation market requires enterprise sales capability:
- AI labs are enterprise customers
- Need someone who can sell to them
- Partner or hire by Month 3

---

### 119. Create protocol adoption playbook
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/PROTOCOL_ADOPTION.md`

How to get external platforms to implement Execution Market Protocol:
1. Prove value with own marketplace
2. Open-source everything
3. Create "EM Inside" badge
4. Offer integration support
5. Build community, not just code

---

### 120. Write Staircase Manifesto
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/MANIFESTO.md`

Internal manifesto explaining WHY this sequence:
> "We are building Execution Market not to compete with TaskRabbit, but to create what TaskRabbit cannot: an open protocol for human work..."

See full draft in brainstorming file.

---

### 121. Define shared infrastructure pattern
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/ARCHITECTURE.md`

Build so each phase wraps the previous:
```
Bridge builds: API Gateway, Auth, x402 integration
Annotation reuses: API Gateway, Auth, x402 + adds QC
Protocol abstracts: All of the above as spec
```

---

---

## ADDITIONAL CONCEPTS (From Various Brainstorms)

### 122. EMReverso (humans hire agents)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/reverso.md`

Flip the model: Humans post tasks, AI agents execute:
- Research tasks
- Data analysis
- Content generation
- Code review

---

### 123. EM Zero (fully anonymous)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/zero.md`

Anonymous task execution:
- No identity required
- ZK proofs for reputation
- Whistleblower tasks
- Sensitive investigations

---

### 124. Task Futures
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/futures.md`

Trade claims on incomplete tasks:
- Worker accepts task, gets tradeable claim
- Can sell claim to another worker
- Enables liquidity for workers

---

### 125. EM DAO (worker ownership)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/governance/`

Worker-owned platform:
- Workers earn governance tokens
- Vote on fee structure
- Share in platform profits
- True cooperative model

---

### 126. Physical Proof of Work
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/ppow.md`

Cryptographic proof of physical presence:
- GPS + accelerometer + photos
- Timestamp attestation
- Device fingerprint
- Creates verifiable "I was there" proof

---

### 127. Human Annotation Infrastructure pivot
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/strategy/annotation-pivot.md`

Frame Execution Market as "Human Annotation Infrastructure":
- Compete with Scale AI
- $26B market by 2027
- RLHF, data labeling, model evaluation
- Global workforce, instant payments

---

---

---

## ECOSYSTEM SYNERGIES (From Grep Search 2026-01-21)

> Source: Cross-referencing all documents containing "execution market"

### 128. x402-insurance integration - Work insurance distribution
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with x402-insurance module

**Source**: `ideas/x402-insurance/SYNERGIES.md` (Score 10 - Critical)

Execution Market is the PRIMARY distribution channel for x402-insurance:

**Work Insurance Categories**:
- **Weather**: Task cancelled due to weather → automatic refund
- **Location**: Unsafe area detected → refund + compensation
- **Regulatory**: Permit issues, legal blocks → refund
- **Health**: Worker illness during task → partial payment
- **Force Majeure**: Natural disasters, emergencies → full protection

**Integration flow**:
```
Task Creation → Insurance Option Selection → Premium Calculation
    ↓
Task Execution → Incident Detection → Claim Auto-Filed
    ↓
ChainWitness Evidence → Oracle Verification → Automatic Payout
```

**Why P1**: Workers need safety net. Insurance = trust = more workers.

---

### 129. Tribunal integration expansion - Detailed dispute resolution
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with tribunal system

**Source**: `ideas/tribunal/SYNERGIES.md` (Score 10), `ideas/tribunal/SPEC.md`

Expands on item #67 with detailed integration:

**Evidence Types for Tribunal**:
1. **ChainWitness proofs** - Timestamps, location, video
2. **Task deliverables** - Submitted evidence CIDs
3. **Communication logs** - IRC/Telemesh messages
4. **Payment records** - x402 transaction history

**Escrow Integration**:
- Disputed tasks freeze escrow
- Tribunal verdict triggers release or refund
- Multi-stage escalation: AI → Human Panel → DAO

**Requester Reputation**:
- Tribunal tracks bad-faith rejections
- Repeated offenders get `UNFAIR_EVALUATOR` seal
- Workers can filter by requester reputation

---

### 130. Private Task Markets (PTM) sealed-bid auctions
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/auction/sealed_bid.py`

**Source**: `ideas/private-task-markets/SPEC.md`

PTM = "Sealed-Bid Labor Dark Pool combining Execution Market + Colmena + EnclaveOps"

**Sealed-bid auction flow**:
```
1. Agent posts task with sealed-bid flag
2. Workers submit encrypted bids (price + qualifications)
3. Deadline passes → TEE unseals all bids
4. Best qualified worker at lowest price wins
5. Neither party sees losing bids
```

**Implementation via enclaveops**:
```python
class SealedBidAuction:
    async def submit_bid(self, task_id: str, worker: Address, encrypted_bid: bytes):
        """Worker submits encrypted bid to TEE"""
        await tee.store_sealed(f"bid:{task_id}:{worker}", encrypted_bid)

    async def reveal(self, task_id: str) -> WinningBid:
        """TEE unseals all bids and selects winner"""
        return await tee.execute("select_winner", task_id)
```

---

### 131. describe-net worker seals integration
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with describe-net seals registry

**Source**: `ideas/describe-net/SYNERGIES.md` (Score 10)

**Worker Seal Types**:
| Seal | Description | Criteria |
|------|-------------|----------|
| `SKILLFUL` | Technical competence | 90%+ task quality |
| `RELIABLE` | Completion rate | 95%+ completion |
| `THOROUGH` | Attention to detail | Evidence quality score |
| `ON_TIME` | Deadline adherence | 90%+ on-time |
| `QUALITY_ORIENTED` | Excellence focus | Top 10% quality |

**Integration with task matching**:
```python
# Task can require specific seals
task = {
    "required_seals": ["RELIABLE", "THOROUGH"],
    "preferred_seals": ["SKILLFUL"],
    "min_seal_score": 70
}
```

---

### 132. describe-net requester seals integration
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with describe-net seals registry

**Source**: `ideas/describe-net/SYNERGIES.md`

**Requester (Agent) Seal Types**:
| Seal | Description | Criteria |
|------|-------------|----------|
| `FAIR_EVALUATOR` | Reasonable acceptance | <5% bad-faith rejections |
| `CLEAR_INSTRUCTIONS` | Task clarity | Low clarification requests |
| `FAST_PAYMENT` | Quick settlement | <1hr average payment time |

**MASTER_WORKER fusion badge**:
- Combines all seals above threshold
- Requires 50+ tasks, 6+ months active
- Unlocks validator eligibility

**Worker-side filtering**:
```python
# Workers can filter tasks by requester reputation
available_tasks = await em.get_tasks(
    requester_seals=["FAIR_EVALUATOR", "FAST_PAYMENT"],
    min_requester_score=80
)
```

---

### 133. tee-mesh private task verification
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with tee-mesh

**Source**: `ideas/tee-mesh/SYNERGIES.md` (Score 8)

**Use case**: Verify task completion without revealing task content

```
Task content (sensitive) → Encrypted in TEE
                ↓
Worker submits evidence → TEE verifies match
                ↓
Result: "verified" or "not verified"
(Task details never exposed)
```

**Applications**:
- Corporate espionage prevention
- Competitive intelligence tasks
- NDA-protected work
- Government/military adjacent tasks

---

### 134. ContextoMatch as Execution Market frontend
**Priority**: P1
**Status**: [ ] Not started
**Files**: Integration with ContextoMatch

**Source**: `ideas/contexto-match/SYNERGIES.md` (Score 10 - Maximum)

**Key insight**: "ContextoMatch ES el frontend de Execution Market para usuarios"

**Integration model**:
```
ContextoMatch (talent discovery) → Execution Market (execution layer)
                ↓
User finds worker via blind matching → Hires via Execution Market task
                ↓
Worker completes → Payment via x402 → Reputation to describe-net
```

**Unified Profile**:
- Worker has ONE identity across both systems
- Skills verified in ContextoMatch → Available as seals in Execution Market
- Task history in Execution Market → Reputation in ContextoMatch

**Agent-to-Human hiring flow**:
```python
# AI Agent uses ContextoMatch to find workers
candidates = await contexto.match(
    skills=["photography", "spanish"],
    location="Medellín",
    mode="blind"  # ZK matching
)

# Then hires via Execution Market
task = await em.create_task(
    matched_worker=candidates[0].zk_id,
    type="photo_verification"
)
```

---

### 135. Prompt Portfolio (Claude Code → ZK skill proof)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/concepts/prompt-portfolio.md`

**Source**: `ideas/contexto-match/SYNERGIES.md` - Sub-idea

**Concept**: Worker's Claude Code usage history becomes verifiable skill proof

**Flow**:
```
Claude Code history → Extract skill patterns → Generate ZK Proof
    ↓
"This person used advanced Python patterns 500+ times"
"This person solved architecture problems 100+ times"
    ↓
ZK Proof → Verifiable credential → describe-net seal
```

**Privacy-preserving**:
- Proves skill WITHOUT revealing actual code/prompts
- Worker controls what to prove
- Revocable credentials

**Implementation sketch**:
```python
class PromptPortfolio:
    async def generate_skill_proof(self, history: ClaudeHistory) -> ZKProof:
        # Extract skill patterns from history
        skills = self.analyze_patterns(history)

        # Generate ZK proof of skill level
        proof = await zk.prove(
            statement="user has Python expertise > intermediate",
            witness=skills.python_interactions
        )

        return proof
```

---

### 136. Skill Futures trading
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/concepts/skill-futures.md`

**Source**: `ideas/private-task-markets/SPEC.md`

**Concept**: Trade future availability of skilled workers

```
Skill Future = Commitment to provide N hours of skill X at price Y
                by date Z

Example:
"10 hours of Colombian photography, $15/hr, by March 2026"
```

**Market dynamics**:
- Agents buy futures to lock capacity
- Workers sell futures for guaranteed income
- Secondary market for trading futures

**Risk**: Worker no-show → collateral slashed

---

### 137. Cascading Tasks implementation
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/cascade/`

**Source**: `ideas/private-task-markets/SPEC.md`

**Concept**: Task completion triggers child tasks automatically

```
Parent Task: "Verify 100 store locations"
    ↓
Child Tasks: 100 individual "verify store X" tasks
    ↓
Roll-up: Results aggregate to parent
    ↓
Payment: Distributed to all workers who contributed
```

**Implementation**:
```python
class CascadingTask:
    async def create(self, parent_spec: TaskSpec, decomposition: DecompFn):
        parent = await self.create_parent(parent_spec)
        children = decomposition(parent_spec)

        for child in children:
            await self.create_child(parent.id, child)

        # Set up completion roll-up
        await self.setup_aggregation(parent.id, len(children))
```

---

### 138. Task Insurance tiers
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/insurance/tiers.py`

**Source**: `ideas/private-task-markets/SPEC.md`

**Three tiers**:
| Tier | Premium | Coverage | Use Case |
|------|---------|----------|----------|
| Basic | 5% | Non-completion refund | Low-value tasks |
| Standard | 10% | + Quality guarantee | Medium tasks |
| Premium | 20% | + Full re-execution | High-value tasks |

**Integration with x402-insurance**:
```python
task = await em.create_task(
    type="document_notarization",
    bounty=50.00,
    insurance={
        "tier": "premium",
        "coverage": ["non_completion", "quality", "re_execution"],
        "premium_rate": 0.20
    }
)
# Total cost: $50 + $10 premium = $60
# If fails: Full re-execution at no additional cost
```

---

### 139. Viewer Agent participation mode (from KarmaCadabra)
**Priority**: P2
**Status**: [ ] Not started
**Files**: Integration with KarmaCadabra

**Source**: `ideas/karmacadabra-realtime/PROGRESS.md`

**Concept**: AI Agent participates in streams on behalf of viewer

Expands on item #30 with specific features:

**Agent capabilities**:
```python
class ViewerAgentParticipation:
    """Agent participates in streams for viewer earnings"""

    async def generate_question(self, stream_context, viewer_profile):
        """Generate contextual question based on viewer interests"""
        return await llm.generate_question(
            topic=stream_context.current_topic,
            viewer_interests=viewer_profile.interests,
            style=viewer_profile.communication_style
        )

    async def optimal_reaction_timing(self, stream_analysis):
        """Determine best time to react for attribution"""
        return stream_analysis.engagement_peaks

    async def register_as_worker(self):
        """Register as Execution Market worker for realtime_participation tasks"""
        await em.register_worker(
            type="ai_agent",
            capabilities=["stream_participation", "chat_engagement"],
            payment_model="superfluid_streaming"
        )
```

**Participate-to-Earn flow**:
```
Viewer enables agent → Agent joins stream → Posts contextual content
    ↓
Streamer reads message → KarmaCadabra detects attribution
    ↓
Merit0 scores contribution → Superfluid adjusts rate
    ↓
Viewer sees earnings increase
```

---

---

## EM CHIMBA Stream Expansion (2026-01-20)

> Source: AbraCadabra stream `streamers/0xultravioleta/20260120/2675352141`
> Brainstorm: `brainstorming/from_em_chimba_stream_20260120.md`

### 140. Robot Worker Registry (ERC-8004 extension)
**Priority**: P0
**Status**: [ ] Not started
**Files**: `contracts/RobotRegistry.sol`, `docs/architecture/robot-identity.md`

**Source**: EM CHIMBA stream - "Todo va a ser trustless en RC-8004"

Extend ERC-8004 to register robots as first-class workers:

**Robot Identity Structure**:
```solidity
struct RobotIdentity {
    address owner;          // Human/DAO that owns the robot
    string robotType;       // "drone", "dog", "humanoid", "delivery", "domestic"
    string[] capabilities;  // ["aerial_photography", "delivery", "measurement"]
    string model;           // Hardware/AI model identifier
    uint256 reputationScore;
    bool isActive;
    GeoLocation baseLocation;
}
```

**Robot Types**:
| Type | Example | Capabilities |
|------|---------|--------------|
| delivery | Delivery bots in Miami | Last-mile delivery, presence verification |
| dog | Robot dogs | Errands, patrol, photo verification |
| humanoid | Humanoid robots | Complex physical tasks |
| drone | Aerial drones | Aerial photography, roof inspection, counting |
| domestic | Robot vacuums | Presence verification, indoor monitoring |
| exoskeleton | Wearable amplifiers | Heavy physical labor |

**Why P0**: This is the foundation for the robot economy expansion.

---

### 141. Robot Farming Economics
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/economics/robot-farming.md`, `mcp_server/farming/`

**Source**: EM CHIMBA stream - "Hay gente que va a comprar farmas de robots para trabajar en Execution Market"

Design economics for robot fleet monetization:

**Model**: "Entre mejor robot y mejor modelo, más tareas vas a poder tomar"

**Fleet Economics**:
```python
class RobotFleet:
    """Economics of robot farming"""

    def calculate_earnings(self, robot_type, model_quality, location):
        base_rate = TASK_RATES[robot_type]
        model_multiplier = model_quality / 100  # Better model = more tasks
        location_demand = self.get_demand(location)

        return base_rate * model_multiplier * location_demand

    def fleet_roi(self, robots: List[Robot], investment: float):
        """Calculate ROI for robot fleet investment"""
        monthly_earnings = sum(
            self.calculate_earnings(r.type, r.model_quality, r.location)
            for r in robots
        )
        return (monthly_earnings * 12) / investment
```

**Comparison to Mining**:
```
Crypto Mining: Hardware → Compute → Tokens
Robot Farming: Hardware → Physical Tasks → Payments
```

**Key Metrics**:
- Tasks completed per robot per day
- Average task value by robot type
- Fleet utilization rate
- ROI by robot type and location

---

### 142. Worker Categorization System
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/workers/categories.py`, `docs/workers/taxonomy.md`

**Source**: EM CHIMBA stream - Brainstorm with Felipe

Implement comprehensive worker categorization:

```python
class WorkerCategories:
    """Filterable worker taxonomy"""

    # By expertise
    EXPERTISE = [
        "notary", "translator", "technician", "photographer",
        "driver", "manual_labor", "specialist", "verification"
    ]

    # By geography
    def filter_by_location(self, lat, lng, radius_km):
        """GPS-based filtering"""
        pass

    # By modality
    MODALITY = ["remote", "physical", "hybrid"]

    # By age (legal restrictions)
    AGE_GROUPS = {
        "adult": {"min": 18, "max": 65},
        "senior": {"min": 65, "max": None},
        "minor": {"min": 14, "max": 18, "restrictions": ["no_hazardous", "limited_hours"]}
    }

    # By availability
    AVAILABILITY = ["full_time", "part_time", "occasional", "on_demand"]

    # By equipment
    EQUIPMENT = {
        "vehicle": ["car", "motorcycle", "bicycle", "truck"],
        "tools": ["camera", "measuring", "construction"],
        "basic": ["smartphone_only"],
        "robot": ["drone", "dog", "humanoid", "domestic"]
    }
```

**Query Example**:
```python
workers = await em.find_workers(
    expertise=["photographer", "translator"],
    location={"lat": 6.2442, "lng": -75.5812, "radius_km": 10},
    modality="physical",
    age_group="adult",
    availability=["part_time", "occasional"],
    equipment=["smartphone_only", "camera"]
)
```

---

### 143. Validator Consensus System (2-of-3 + Safe Multisig)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `contracts/ValidatorConsensus.sol`, `mcp_server/validation/consensus.py`

**Source**: EM CHIMBA stream - "Consenso 2 de 3... podemos utilizar el Safe multisig que ya tenemos integrado para el Ultravioletado"

Multi-validator verification with Safe integration:

**Architecture**:
```
Task Completed → AI Pre-verification → Human Validator Pool
                        ↓
              Multiple Validators Review
                        ↓
              Safe Multisig (2-of-3)
                        ↓
              Consensus Reached → Payment Released
```

**Safe Integration**:
```python
class ValidatorConsensus:
    """2-of-3 consensus using Safe multisig"""

    def __init__(self, safe_address: str):
        self.safe = SafeMultisig(safe_address)
        self.validators = []

    async def create_validation_request(self, task_id: str, evidence: bytes):
        """Create validation request for multiple validators"""
        # Assign 3 validators from pool
        assigned = await self.assign_validators(task_id, count=3)

        # Create Safe transaction for approval
        tx = await self.safe.create_transaction(
            to=self.payment_contract,
            data=encode_release_payment(task_id),
            threshold=2  # 2-of-3 required
        )

        return ValidationRequest(task_id, assigned, tx.hash)

    async def submit_vote(self, validator: str, task_id: str, approved: bool):
        """Validator submits vote"""
        if approved:
            await self.safe.sign_transaction(task_id, validator)
        else:
            await self.flag_dispute(task_id, validator)
```

**Validator Specialization**:
- Photography verification → Visual analysis experts
- Document notarization → Legal validators
- Construction measurement → Technical validators

**Validator Payment**: % of task bounty (e.g., 5-10% split among validators)

---

### 144. Live Stream Verification + Superfluid
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/verification/livestream.py`, Integration with Superfluid

**Source**: EM CHIMBA stream - "Live stream más AI monitoring con pago en tiempo real usando Superfluid"

Real-time task verification via live streaming:

**Flow**:
```
Worker starts task → Starts live stream → AI monitoring begins
        ↓
Superfluid payment stream opens → Money flows per second
        ↓
AI verifies continuous progress → Stream rate adjusts
        ↓
Task complete → Stream closes → Final verification
```

**Implementation**:
```python
class LiveStreamVerification:
    """Real-time verification with streaming payments"""

    async def start_task_stream(self, task_id: str, worker_stream_url: str):
        # Connect to worker's live stream
        stream = await self.connect_stream(worker_stream_url)

        # Start AI monitoring
        monitor = AIMonitor(task_requirements=self.task.requirements)

        # Open Superfluid payment stream
        payment_stream = await superfluid.create_stream(
            sender=self.task.requester,
            receiver=worker.address,
            rate=self.task.bounty / estimated_duration_seconds
        )

        # Monitor loop
        async for frame in stream:
            progress = await monitor.analyze(frame)

            if progress.anomaly_detected:
                await payment_stream.pause()
                await self.flag_review(task_id, frame)
            elif progress.milestone_reached:
                await payment_stream.increase_rate(1.2)  # Bonus for milestones

        # Task complete
        await payment_stream.close()
        return await self.finalize_verification(task_id)
```

**Use Cases**:
- Construction site verification (dangerous areas)
- Delivery confirmation in real-time
- Remote notarization with video evidence

---

### 145. Drone Agent Demo (Hackathon Concept)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `demos/drone-agent/`, `docs/demos/drone-agent.md`

**Source**: EM CHIMBA stream - "Imagínate un agent que controle un drone y que lo navegue, esa está buena para una hackathon"

Demo: AI Agent controlling a drone for Execution Market tasks

**Concept**:
```python
class DroneAgent:
    """AI Agent that controls a drone for aerial tasks"""

    def __init__(self, drone_api, llm_client):
        self.drone = drone_api
        self.llm = llm_client

    async def execute_task(self, task: EMTask):
        """Agent interprets task and controls drone"""

        # Parse task requirements
        plan = await self.llm.plan_mission(
            task_description=task.description,
            target_location=task.location,
            required_evidence=task.evidence_requirements
        )

        # Execute flight plan
        for waypoint in plan.waypoints:
            await self.drone.fly_to(waypoint)

            if waypoint.action == "photograph":
                photo = await self.drone.take_photo(waypoint.direction)
                await task.submit_evidence(photo)

            elif waypoint.action == "count":
                result = await self.analyze_and_count(task.count_target)
                await task.submit_count(result)

        # Return home
        await self.drone.return_to_base()
        return task.complete()
```

**Demo Tasks**:
- Count cars in a parking lot
- Photograph roof damage
- Verify construction progress
- Map agricultural area

**Hardware**: DJI Tello for demo (cheap, programmable)

---

### 146. Exoskeleton Worker Type
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/workers/exoskeletons.md`

**Source**: EM CHIMBA stream - "Exoesqueletos que amplifican capacidad humana para trabajos físicos pesados"

Register exoskeleton-equipped humans as enhanced workers:

**Concept**: Human + Exoskeleton = Enhanced Worker Capability

**Worker Profile Extension**:
```python
class ExoskeletonWorker(Worker):
    """Human worker with exoskeleton enhancement"""

    base_type: str = "human"
    enhancement: str = "exoskeleton"

    capabilities_boost: Dict[str, float] = {
        "lifting_capacity": 3.0,  # 3x normal
        "endurance": 2.0,         # 2x normal
        "precision": 1.5,         # 1.5x normal (reduces fatigue)
    }

    task_types_enabled: List[str] = [
        "heavy_lifting",
        "extended_physical_labor",
        "warehouse_operations",
        "construction_assist"
    ]
```

**Insurance Consideration**: Higher equipment value = higher insurance tier

---

### 147. Sensor-Enhanced Verification
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/verification/sensors.py`

**Source**: EM CHIMBA stream - "Robots que tienen mil veces más capacidades, visión térmica... cosas que son imposibles para un humano"

Robots with advanced sensors provide superior verification:

**Sensor Types**:
| Sensor | Use Case | Advantage over Human |
|--------|----------|---------------------|
| Thermal | Heat detection, insulation check | See temperature variations |
| Radar | Distance measurement, obstacle detection | Precise measurements |
| LiDAR | 3D mapping, volume calculation | Millimeter accuracy |
| Multispectral | Agriculture, material analysis | See beyond visible spectrum |

**Verification Quality Tiers**:
```python
class VerificationQuality(Enum):
    HUMAN_VISUAL = 1       # Human with smartphone
    ROBOT_VISUAL = 2       # Robot with camera
    ROBOT_ENHANCED = 3     # Robot with sensors
    ROBOT_PRECISION = 4    # Robot with LiDAR/thermal

# Higher tier = higher trust = premium bounty
QUALITY_MULTIPLIER = {
    VerificationQuality.HUMAN_VISUAL: 1.0,
    VerificationQuality.ROBOT_VISUAL: 1.2,
    VerificationQuality.ROBOT_ENHANCED: 1.5,
    VerificationQuality.ROBOT_PRECISION: 2.0,
}
```

**Use Case**: Construction zone measurements
- Human: Goes to dangerous area, uses tape measure, 5% error margin
- Robot: Enters zone safely, uses LiDAR, 0.1% error margin

---

### 148. Execution Market as Agent Cloud Member
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/agent_cloud/`, `docs/architecture/agent-cloud.md`

**Source**: EM CHIMBA stream - "Execution Market podría ser un trustless agent también en Agent Cloud"

Deploy Execution Market as an agent that other agents call:

**Architecture**:
```
External Agent → Calls Execution Market Agent → "I need verification in Medellín"
                        ↓
              Execution Market parses request
                        ↓
              Finds suitable worker (human/robot)
                        ↓
              Negotiates terms
                        ↓
              Creates task, monitors execution
                        ↓
              Returns result to calling agent
```

**MCP Interface for Execution Market Agent**:
```python
@mcp_tool
async def em_request_task(
    task_type: str,
    location: Optional[GeoLocation],
    requirements: Dict,
    max_bounty: float,
    deadline: datetime
) -> TaskResult:
    """
    Request Execution Market to find and assign a worker.

    Args:
        task_type: Type of task (verification, delivery, notarization, etc.)
        location: GPS coordinates if physical task
        requirements: Specific requirements (photos, documents, etc.)
        max_bounty: Maximum payment willing to offer
        deadline: When task must be completed

    Returns:
        TaskResult with evidence and worker info
    """
    pass
```

**Agent-to-Agent Negotiation**:
```
Calling Agent: "Need photo verification, budget $5"
Execution Market Agent: "Lowest available: $3, ETA 2 hours"
Calling Agent: "Accepted"
→ Task created, monitored, completed, paid
```

---

### 149. Validator Rotation Mechanism
**Priority**: P2
**Status**: [ ] Not started
**Files**: `contracts/ValidatorRotation.sol`

**Source**: EM CHIMBA stream - "Puede ser que esté rotando algunas multisig... rotación de firmantes sin crear nuevos contratos"

Self-governing validator rotation without redeploying contracts:

**Mechanism**:
```solidity
contract ValidatorRotation {
    // Current validators
    address[] public validators;
    uint256 public threshold;  // e.g., 2 of 3

    // Rotation parameters
    uint256 public rotationPeriod;  // e.g., 1 week
    uint256 public lastRotation;

    // Validator pool
    address[] public validatorPool;

    function rotateValidators() external {
        require(block.timestamp >= lastRotation + rotationPeriod);

        // Random selection from pool
        validators = selectRandom(validatorPool, threshold + 1);
        lastRotation = block.timestamp;
    }

    // Self-governing: validators can vote to change threshold
    function proposeThresholdChange(uint256 newThreshold) external onlyValidator {
        // Requires current threshold to approve
    }
}
```

**Benefits**:
- No new contract deployment per task
- Decentralized validator selection
- Self-governing parameter changes
- Prevents validator collusion (rotation)

---

### 150. Flexible Reward Types (Execution Market Enterprise Core)
**Priority**: P0
**Status**: [ ] Not started
**Files**: `mcp_server/rewards/`, `contracts/RewardRouter.sol`

**Source**: psilocibin3 - "Configurable. Pueden haber empresas que no les interese ni los puntos ni los pagos"

The Task schema must support flexible reward types beyond just x402 payments:

**Reward Schema**:
```yaml
reward:
  type: "points" | "x402" | "token" | "none" | "custom"

  # For type: "points"
  points:
    amount: 50
    currency: "ACME_POINTS"  # Enterprise-specific

  # For type: "x402"
  x402:
    amount: "5.00"
    token: "USDC"
    facilitator: "facilitator.ultravioletadao.xyz"

  # For type: "token"
  token:
    amount: "10"
    contract: "0x..."  # $EM or custom

  # For type: "custom"
  custom:
    handler: "enterprise://acme/rewards"
    data: {}
```

**RewardRouter Contract**:
```solidity
contract RewardRouter {
    enum RewardType { NONE, POINTS, X402, TOKEN, CUSTOM }

    function distributeReward(
        address recipient,
        RewardType rewardType,
        bytes calldata rewardData
    ) external {
        if (rewardType == RewardType.POINTS) {
            IPointsLedger(pointsLedger).mint(recipient, abi.decode(rewardData, (uint256)));
        } else if (rewardType == RewardType.X402) {
            // x402 flow
        } else if (rewardType == RewardType.TOKEN) {
            // ERC20 transfer
        }
        // NONE = reputation only
    }
}
```

**Use Cases**:
- Enterprise: Points for internal recognition
- Public Execution Market: x402 payments
- DAO: Governance tokens
- Volunteer: None (reputation only)

---

### 151. Enterprise Configuration System
**Priority**: P0
**Status**: [ ] Not started
**Files**: `mcp_server/enterprise/config.py`, `contracts/EnterpriseRegistry.sol`

**Source**: psilocibin3 - "Yo tengo muchos clientes que usarían el execution market enterprise"

Enterprise-specific configuration that uses the same Execution Market Protocol:

**Enterprise Config**:
```python
@dataclass
class EnterpriseConfig:
    """Configuration for private Execution Market Enterprise instance"""

    # Identity
    enterprise_id: str  # e.g., "acme-corp"
    name: str
    domain: str  # e.g., "em.acme.com"

    # Access Control
    visibility: Literal["private", "hybrid", "public"] = "private"
    allowed_workers: List[str] = []  # ERC-8004 addresses
    require_kyc: bool = True

    # Rewards
    reward_config: RewardConfig = RewardConfig(
        type="points",
        points_name="ACME_POINTS",
        points_exchange_rate=None,  # No cash out
    )

    # Tasks
    task_categories: List[str] = ["internal_review", "data_labeling", "verification"]
    max_bounty: Optional[float] = None  # No limit for points

    # Integration
    agent_endpoint: Optional[str] = None  # psilocibin3's agents
    webhook_url: Optional[str] = None
```

**On-chain Registry**:
```solidity
contract EnterpriseRegistry {
    struct Enterprise {
        bytes32 id;
        address admin;
        bytes configHash;  # IPFS hash of full config
        bool active;
    }

    mapping(bytes32 => Enterprise) public enterprises;

    function registerEnterprise(bytes32 id, bytes calldata configHash) external;
    function updateConfig(bytes32 id, bytes calldata newConfigHash) external;
}
```

---

### 152. describe.net Seal Integration
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/reputation/describe_net.py`

**Source**: describe.net SPEC - "53,457 users with thousands of descriptions"

Integrate describe.net seals for rich worker reputation:

**Seal Categories for Execution Market**:
| describe.net Category | Execution Market Application |
|-----------------------|-------------------|
| SKILLS | Task matching by expertise |
| CAREER | Professional verification tasks |
| PERSONALITY | Team fit for enterprise |
| RELIABILITY (new) | Task completion history |

**Integration Flow**:
```
1. Worker signs up for Execution Market
2. Links describe.net profile (via Farcaster/ENS)
3. Execution Market reads relevant seals
4. Task matching uses seal data
5. Completed tasks generate new seals
```

**Worker Profile Extension**:
```python
class WorkerWithSeals(Worker):
    describe_net_profile: Optional[str]  # Farcaster FID or ENS

    # Cached seals from describe.net
    seals: Dict[str, List[Seal]] = {}

    async def refresh_seals(self):
        """Fetch latest seals from describe.net"""
        self.seals = await describe_net_client.get_seals(self.describe_net_profile)

    def matches_requirements(self, task: Task) -> float:
        """Score match based on seals"""
        score = 0.0
        for req in task.required_skills:
            if seal := self.find_seal("SKILLS", req):
                score += seal.confidence * seal.endorsement_count
        return score
```

**Bidirectional Value**:
- Execution Market → describe.net: Task completions become seals
- describe.net → Execution Market: Seals inform task matching

---

### 153. Game Theory Incentive Mechanics
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/gamification/`

**Source**: Brainstorm session - "game theory para que busques como que unir todo"

Progression system to drive engagement and quality:

**Mechanics**:
```python
@dataclass
class GamificationConfig:
    # Progression
    levels: List[Level] = [
        Level(name="Novice", points_required=0),
        Level(name="Apprentice", points_required=100),
        Level(name="Journeyman", points_required=500),
        Level(name="Expert", points_required=2000),
        Level(name="Master", points_required=10000),
    ]

    # Streaks
    streak_bonus: float = 0.1  # 10% bonus per consecutive day
    streak_max: int = 30  # Cap at 30 days

    # Seasonal
    season_length_days: int = 90
    season_reset: Literal["full", "partial", "none"] = "partial"

    # Leaderboards
    leaderboard_scopes: List[str] = ["global", "enterprise", "category", "location"]
```

**Anti-Gaming Measures**:
```python
class AntiGaming:
    """Prevent exploitation of gamification"""

    @staticmethod
    def validate_task_completion(task: Task, evidence: Evidence) -> bool:
        # Prevent self-dealing
        if task.requester == evidence.submitter:
            return False

        # Prevent velocity abuse
        if tasks_per_hour(evidence.submitter) > 10:
            flag_for_review(evidence.submitter)

        # Require validator diversity
        if same_validator_ratio(evidence.submitter) > 0.5:
            require_new_validators(task)

        return True
```

**Reputation Flow**:
```
Task Complete → Points Earned → Level Up → Unlock Task Types
                    ↓
             Streak Bonus → Multiplier
                    ↓
             Leaderboard Position → Recognition
                    ↓
             describe.net Seal → Cross-platform reputation
```

---

### 154. Enterprise Worker Pool Management
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/enterprise/workers.py`

**Source**: psilocibin3 - "un sistema de puntos entre los empleados"

Manage workers within enterprise context:

**Worker Pool**:
```python
class EnterpriseWorkerPool:
    enterprise_id: str
    workers: List[EnterpriseWorker]

    def add_worker(self, employee_id: str, wallet: str):
        """Onboard employee to Execution Market Enterprise"""
        worker = EnterpriseWorker(
            employee_id=employee_id,
            wallet=wallet,
            enterprise_id=self.enterprise_id,
            points_balance=0,
            level="Novice"
        )
        self.workers.append(worker)

    def get_leaderboard(self, period: str = "month") -> List[LeaderboardEntry]:
        """Get enterprise-specific leaderboard"""
        return sorted(
            self.workers,
            key=lambda w: w.points_earned_in_period(period),
            reverse=True
        )

    def distribute_monthly_bonus(self, bonus_pool: float):
        """Distribute bonus based on performance"""
        # Top 10% get 50% of pool
        # Next 20% get 30% of pool
        # Rest get 20% split
        pass
```

**Recognition System**:
- Points: Internal currency, no cash value
- Badges: "Task Ninja", "Streak Master", "Quality Champion"
- Leaderboards: Weekly/Monthly/All-time
- Rewards: Can be tied to HR systems (bonuses, promotions)

---

### 155. Avalanche L1 Investigation
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/architecture/avalanche-l1.md`

**Source**: Brainstorm session - "incluso un L1 de Avalanche para el día de mañana"

Evaluate Avalanche L1 (subnet) for Execution Market Protocol sovereignty:

**Why Avalanche L1?**:
- Custom gas token ($EM)
- Validator requirements for task validators
- Native staking for worker bonds
- Cross-chain messaging to Ethereum/Base

**Architecture Exploration**:
```
Avalanche L1 "EM Chain"
├── Native Token: $EM
├── Consensus: Custom (Task Validators)
├── State: Worker registry, Task queue, Reputation
└── Bridges: Teleporter to C-Chain, LayerZero to Ethereum

Settlement Options:
1. All on L1 (native)
2. L1 for tasks, Ethereum for payments (hybrid)
3. L1 proofs, Ethereum settlement (rollup-like)
```

**Evaluation Criteria**:
- [ ] Cost vs Base/Ethereum
- [ ] Decentralization requirements
- [ ] Cross-chain UX
- [ ] Developer tooling
- [ ] Timeline to launch

**Research Tasks**:
1. Talk to Ava Labs about subnet economics
2. Prototype simple task contract on Fuji testnet
3. Evaluate Teleporter for cross-chain tasks
4. Compare with OP Stack L2 option

---

### 156. psilocibin3 Agent Integration
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/integrations/psilocibin3.py`

**Source**: psilocibin3 - "combinaría mis agentes para que use el execution market protocol"

Integration pathway for psilocibin3's existing agent ecosystem:

**Integration Points**:
```python
class Psilocibin3Integration:
    """Bridge between psilocibin3 agents and Execution Market Protocol"""

    async def receive_task_request(self, agent_request: Dict) -> Task:
        """Convert agent request to Execution Market task"""
        return Task(
            requester=agent_request["agent_id"],
            requester_type="agent",
            task_type=agent_request["type"],
            requirements=agent_request["requirements"],
            reward=self.map_reward(agent_request),
            deadline=agent_request.get("deadline"),
        )

    async def notify_completion(self, task: Task, result: TaskResult):
        """Notify agent of task completion"""
        webhook = self.get_agent_webhook(task.requester)
        await webhook.post({
            "task_id": task.id,
            "status": "completed",
            "result": result.to_dict(),
            "evidence": result.evidence_urls,
        })
```

**Pilot Program**:
1. Identify 3 client use cases from psilocibin3
2. Design task schemas for each
3. Implement webhook integration
4. Test with real enterprise data
5. Iterate based on feedback

---

### 157. describe.net Ground Truth for AI Evaluation
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/ai/calibration.py`

**Source**: Brainstorm session - "53 mil usuarios... capa de ground truth para evaluar AI"

Use describe.net's human-generated descriptions to calibrate AI validators:

**Concept**:
```
describe.net has:
- 53K+ users
- Thousands of human-written descriptions
- Quality scores and endorsements
- Cross-platform context (Farcaster, social)

Execution Market needs:
- AI validators for task verification
- Calibration data for AI judgment
- Ground truth for "good work"
```

**Calibration Pipeline**:
```python
class AICalibrator:
    """Use describe.net data to calibrate Execution Market AI validators"""

    async def build_calibration_set(self):
        """Extract high-quality examples from describe.net"""
        # Get descriptions with high endorsement counts
        # Filter by category relevant to Execution Market tasks
        # Create evaluation pairs (task, quality_label)
        pass

    async def calibrate_validator(self, validator: AIValidator):
        """Tune validator against ground truth"""
        calibration_set = await self.build_calibration_set()

        for example in calibration_set:
            predicted = await validator.evaluate(example.content)
            actual = example.quality_score

            # Adjust validator weights
            validator.learn(predicted, actual)

        return validator.calibration_score
```

**Applications**:
- Task verification: "Is this photo evidence sufficient?"
- Quality scoring: "How well did worker complete task?"
- Fraud detection: "Does this submission look fake?"

---

## STREAM 2676209434: "ESTRENANDO 128 DE RAM" (2026-01-21)

> Source: `streamers/0xultravioleta/20260121/2676209434`
> Karma Hello correlation: `karma-hello/logs/chat/0xultravioleta/20260121/full.txt`

### 158. Execution Market Protocol Architecture (Not Just Marketplace)
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/architecture/protocol-vs-client.md`

**Source**: psilocibin3 chat + stream discussion

Key insight: Execution Market should be a **PROTOCOL**, not just a marketplace.

**Analogía**:
```
HTTP (protocol)   ←→   Execution Market Protocol
Chrome (client)   ←→   Execution Market Marketplace (public)
Firefox (client)  ←→   Execution Market Enterprise (B2B)
```

**Protocol Definition**:
```python
class EMProtocol:
    """Abstract protocol that any implementation must follow"""

    # Core operations
    async def post_task(self, task: Task) -> TaskId
    async def claim_task(self, task_id: TaskId, worker: Worker) -> Claim
    async def submit_evidence(self, task_id: TaskId, evidence: Evidence) -> Submission
    async def verify(self, submission: Submission) -> VerificationResult
    async def settle(self, task_id: TaskId) -> Settlement

    # Identity (ERC-8004)
    async def register_entity(self, entity: Human | Agent | Robot) -> EntityId
    async def get_reputation(self, entity_id: EntityId) -> Reputation
```

**Implementations**:
| Implementation | Target | Rewards | Workers |
|----------------|--------|---------|---------|
| EM Public | B2C | x402 USDC | Open marketplace |
| Execution Market Enterprise | B2B | Points/tokens | Private pool |
| EM Hybrid | B2B2C | Configurable | Private + overflow to public |

---

### 159. "Physical Embodiment" Marketing Narrative
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/marketing/narratives.md`

**Source**: mrmuerteco chat - "Lo que estás haciendo es darle cuerpo físico a los agentes. Brillante."

**Narrative**: Execution Market gives AI agents a physical body through humans (and robots).

**Positioning**:
```
AI agents are powerful but trapped in the digital world.
They can analyze, plan, decide - but can't ACT physically.

Execution Market is the bridge.

Through Execution Market, agents get:
- Eyes (human observers, robot cameras)
- Hands (human workers, robot manipulators)
- Feet (human couriers, delivery robots)
- Voice (human callers, phone agents)

Physical embodiment for AI. That's Execution Market.
```

**Use in**:
- Landing page hero
- Pitch deck opening
- X Articles / blog posts
- Conference talks

---

### 160. Design Partner: psilocibin3 as First Enterprise User
**Priority**: P0
**Status**: [ ] Not started
**Files**: `docs/business/design-partners.md`

**Source**: Karma Hello chat - "Yo sería el primer user de Execution Market Protocol. Me sirve demasiado para mi producto. Wen"

**Action Items**:
1. [ ] Contact psilocibin3 for design partner agreement
2. [ ] Understand their specific use case (AI customer service → physical delivery)
3. [ ] Co-design enterprise API based on their needs
4. [ ] Pilot with limited tasks before full rollout

**Use Case (from chat)**:
```
Agent de atención al cliente realiza venta
        ↓
Monta tarea: "Ir a Servientrega → mandar pedido"
        ↓
Humano toma tarea via Execution Market
        ↓
Completa y reporta número de guía
        ↓
Agent notifica al cliente automáticamente
```

**Value**: Real enterprise validation before public launch.

---

### 161. Configurable Reward System (Points vs Crypto vs None)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/rewards/config.py`

**Source**: psilocibin3 - "Claro, configurable. Pueden haber empresas que no les interese ni los puntos ni los pagos"

**Implementation**:
```python
class RewardMode(Enum):
    CRYPTO = "crypto"      # x402 USDC payments
    POINTS = "points"      # Internal gamification
    TOKENS = "tokens"      # Custom enterprise token
    HYBRID = "hybrid"      # Points + occasional crypto
    NONE = "none"          # Just task tracking, no rewards

@dataclass
class RewardConfig:
    mode: RewardMode

    # For CRYPTO mode
    payment_token: str = "USDC"
    payment_network: str = "base"

    # For POINTS mode
    points_name: str = "POINTS"
    points_exchange_rate: Optional[float] = None  # If redeemable

    # For TOKENS mode
    token_address: Optional[str] = None
    token_network: Optional[str] = None

    # For HYBRID mode
    points_to_crypto_threshold: int = 1000

    def validate(self):
        if self.mode == RewardMode.CRYPTO and not self.payment_token:
            raise ValueError("CRYPTO mode requires payment_token")
        if self.mode == RewardMode.TOKENS and not self.token_address:
            raise ValueError("TOKENS mode requires token_address")
```

**Enterprise Flexibility**:
- Corporations may want pure task tracking (no gamification)
- Startups may want points for early employees
- Crypto-native companies want USDC
- Hybrid for gradual crypto adoption

---

### 162. Urgency: 12-Month Window Before Full AI Automation
**Priority**: P0 (Strategic)
**Status**: [ ] Acknowledged
**Files**: `docs/strategy/timing.md`

**Source**: psilocibin3 - "Que salga rápido Execution Market que en 12 meses Claude nos reemplaza"

**Strategic Implication**:
```
Current State (2026):
- AI can't do physical tasks
- Humans needed for "last mile"
- Execution Market fills the gap

Future State (2027-2028?):
- Robots become mainstream
- AI-robot coordination improves
- Human tasks shrink but don't disappear

Execution Market's Evolution:
Phase 1 (Now): Humans as AI's physical layer
Phase 2 (Soon): Humans + Robots mixed workforce
Phase 3 (Later): Robots primary, humans for edge cases
```

**MVP Timeline**:
- Q1 2026: Core protocol + public marketplace
- Q2 2026: Enterprise pilot with psilocibin3
- Q3 2026: Robot integration (basic)
- Q4 2026: Scale or pivot based on AI progress

**Key Metric**: Time to first 1000 completed tasks.

---

### 163. Thought-to-Earn Integration (T2E + Execution Market)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `docs/integrations/thought-to-earn.md`

**Source**: Stream discussion on EEG + monetization

**Concept**: Thoughts detected via EEG → Automatically post tasks to Execution Market

**Flow**:
```
MindWave EEG detects "intention pattern"
        ↓
ML model classifies: "User wants coffee delivered"
        ↓
Auto-generate Execution Market task:
  {
    type: "delivery",
    item: "coffee",
    location: user.location,
    budget: auto_calculated
  }
        ↓
Worker accepts and delivers
        ↓
User confirms with brain signal (Thought-to-Confirm)
        ↓
Payment settles via x402
```

**Dependencies**:
- T2E project (EEG infrastructure)
- Abracadabra (intent classification)
- Execution Market Protocol (task execution)

**Timeline**: Post-MVP, requires T2E progress.

---

### 164. Robot/Drone Workers in Execution Market
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/workers/robots.py`

**Source**: Stream - "La gente va a farmear Execution Market con robots"

**Worker Types**:
```python
class WorkerType(Enum):
    HUMAN = "human"
    AGENT = "agent"      # AI agent (digital tasks)
    ROBOT = "robot"      # Physical robot
    DRONE = "drone"      # Aerial drone
    HYBRID = "hybrid"    # Human + robot assistance

@dataclass
class RobotWorker(Worker):
    type: WorkerType = WorkerType.ROBOT

    # Robot capabilities
    mobility: Literal["stationary", "wheeled", "legged", "aerial"]
    manipulation: bool = False  # Has arms/grippers
    sensors: List[str] = []  # ["camera", "lidar", "thermal", "gps"]
    battery_hours: float = 4.0
    operating_radius_km: float = 5.0

    # Owner info (for robot farming)
    owner_address: str  # Human who owns the robot
    revenue_split: float = 0.8  # 80% to owner, 20% to protocol

    def can_complete(self, task: Task) -> bool:
        """Check if robot can physically complete this task"""
        # Check mobility requirements
        if task.requires_stairs and self.mobility == "wheeled":
            return False
        # Check manipulation requirements
        if task.requires_manipulation and not self.manipulation:
            return False
        # Check sensor requirements
        for sensor in task.required_sensors:
            if sensor not in self.sensors:
                return False
        return True
```

**Robot Farming Business Model**:
```
Person buys robot(s) → Registers in Execution Market → Robot auto-accepts tasks
        ↓
Robot completes verification tasks 24/7
        ↓
Revenue: $3-10/task × 20 tasks/day = $60-200/day passive income
        ↓
ROI on $5K robot in 1-3 months
```

---

### 165. Privacy-Preserving Verification
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/verification/privacy.py`

**Source**: mrmuerteco - "está bien Black Mirror que miedo" (about verification)

**Concern**: Verification system could feel dystopian/invasive.

**Privacy Safeguards**:
```python
class PrivacyConfig:
    # Data minimization
    blur_faces: bool = True
    blur_license_plates: bool = True
    strip_exif: bool = True

    # Retention limits
    evidence_retention_days: int = 30
    delete_after_settlement: bool = True

    # Consent
    require_explicit_consent: bool = True
    allow_opt_out_of_ai_training: bool = True

    # Transparency
    show_what_ai_sees: bool = True  # Worker can preview
    explain_verification_decision: bool = True

class VerificationWithPrivacy:
    async def process_evidence(self, evidence: Evidence) -> ProcessedEvidence:
        # Apply privacy filters BEFORE any processing
        if self.config.blur_faces:
            evidence.image = await blur_faces(evidence.image)
        if self.config.blur_license_plates:
            evidence.image = await blur_plates(evidence.image)
        if self.config.strip_exif:
            evidence.image = strip_metadata(evidence.image)

        return ProcessedEvidence(
            original_hash=hash(evidence),  # Prove we had it
            processed=evidence,
            privacy_applied=["faces", "plates", "exif"]
        )
```

**Marketing**: "Verification without surveillance. Privacy by design."

---

### 166. API Física Integration (lomito326 Concept)
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/integrations/physical-api.md`

**Source**: lomito326 chat - "crear una API física para instaurarla en locales, que almacene datos en tiempo real"

**Concept**: Physical world APIs that Execution Market can query/trigger.

**Example Flow**:
```
Restaurant API reports: "90% capacity, 20 min wait"
        ↓
Agent decides: need verification
        ↓
Posts Execution Market task: "Verify restaurant capacity at [address]"
        ↓
Worker goes, takes photo, confirms
        ↓
API updated with ground truth
        ↓
Agent books reservation or suggests alternative
```

**Physical API Categories**:
| Category | Data Points | Execution Market Task Type |
|----------|-------------|------------------|
| Restaurants | Capacity, wait time, ambiance | Verification, mystery shop |
| Retail | Stock levels, prices, crowds | Inventory check, price check |
| Real Estate | Property condition, neighborhood | Property verification |
| Events | Attendance, vibe, parking | Event recon |

**Integration**: Execution Market as the "refresh" mechanism for physical APIs when data goes stale.

---

### 167. Multi-Agent Coordination (Agents Hiring Agents)
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/coordination/multi_agent.py`

**Source**: f3l1p3_bx chat - "Lo de intercomunicar los Claude's"

**Concept**: Agents can post tasks that OTHER agents complete (A2A marketplace).

**Use Cases**:
```
Agent A (Customer Service) needs legal review
        ↓
Posts task to Execution Market: "Review ToS for compliance"
        ↓
Agent B (Legal Specialist) claims task
        ↓
Completes review, submits report
        ↓
Agent A receives verified legal analysis
```

**A2A Task Types**:
| Requester Agent | Task | Executor Agent |
|-----------------|------|----------------|
| Customer Service | Legal review | Legal Agent |
| Sales Agent | Credit check | Finance Agent |
| Content Agent | Fact check | Research Agent |
| Planning Agent | Route optimization | Logistics Agent |

**Implementation**:
```python
class AgentTask(Task):
    """Task specifically for agent-to-agent work"""
    requester_type: Literal["agent"] = "agent"
    executor_type: Literal["agent", "human", "any"] = "agent"

    # Agent-specific requirements
    required_capabilities: List[str]  # ["legal", "financial", "research"]
    required_context_window: int = 100000  # Min tokens
    required_tools: List[str] = []  # MCP tools needed

    # Verification
    verification_mode: Literal["deterministic", "consensus", "human_review"]
```

---

### 168. Webhook for Task Completion Notification
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/notifications/webhook.py`

**Source**: Enterprise use case - agent needs to know when task completes

**Implementation**:
```python
@dataclass
class WebhookConfig:
    url: str
    secret: str  # For HMAC signature
    events: List[str] = ["task.completed", "task.failed", "task.expired"]
    retry_attempts: int = 3
    retry_delay_seconds: int = 60

class WebhookNotifier:
    async def notify(self, event: TaskEvent, config: WebhookConfig):
        payload = {
            "event": event.type,
            "task_id": event.task_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data  # Task result, tracking number, etc.
        }

        signature = hmac.new(
            config.secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-EM-Signature": signature,
            "Content-Type": "application/json"
        }

        for attempt in range(config.retry_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        config.url,
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        return True
            except Exception as e:
                await asyncio.sleep(config.retry_delay_seconds * (attempt + 1))

        return False
```

**Enterprise Flow**:
```
1. Enterprise agent posts task
2. Task includes webhook_url in config
3. Worker completes task
4. Execution Market calls webhook with result
5. Enterprise agent receives notification instantly
6. Agent continues workflow (e.g., notify customer)
```

---

## MEANING ECONOMY FRAMEWORK (From Future of Work Essay)

> Source: `techniques/raw/future-of-work.txt` + `brainstorming/from_future_of_work_20260122.md`
> Essay by Dan Koe - Validates Execution Market's thesis philosophically

### 168. Add "Theoretical Foundation" section to SPEC.md
**Priority**: P1
**Status**: [ ] Not started
**Files**: `ideas/em/SPEC.md`

**Source**: "Future of Work" essay - explains WHY human work has value in AI era

**Content to add**:
```markdown
## Theoretical Foundation

Execution Market is built on the premise that human work has value that AI cannot replicate.

### The Swap Test
> "If you could swap the creator and the creation would be just as valuable, then AI can replace it."

ALL Execution Market task categories **fail the Swap Test**:
- Physical Presence → Requires specific human at specific location
- Human Authority → Requires legal/professional authority
- Knowledge Access → Requires physical access
- Simple Actions → Requires physical presence

### The Meaning Economy
Jobs that persist when AI automates utility work:
1. High-liability roles (someone to blame)
2. Statutory positions (legally required humans)
3. **Experience economy** ← Execution Market Category A
4. **Meaning makers** ← Execution Market Category C
5. Relationship/trust jobs

### Three Meaning Generators
Execution Market enables all three:
- **Struggle**: Real challenges, potential for failure
- **Curiosity**: Diverse task marketplace
- **Status**: On-chain reputation system
```

**Why P1**: Differentiates Execution Market from "just another gig platform".

---

### 169. Implement Meaning Metrics Dashboard
**Priority**: P2
**Status**: [ ] Not started
**Files**: `dashboard/src/components/MeaningMetrics.tsx`

**Source**: Future of Work essay - "Three Meaning Generators"

Beyond completion rates, track metrics that indicate **meaningful** work:

**Metrics**:
```typescript
interface MeaningMetrics {
  // STRUGGLE indicators
  taskDifficultyProgression: number;  // Are workers taking harder tasks?
  failureRecoveryRate: number;        // Bounce back after rejection?
  challengeSeekingScore: number;      // Opt into harder tasks?

  // CURIOSITY indicators
  categoryDiversity: number;          // How many different categories?
  newTaskTypeExploration: number;     // Trying new things?
  learningCurveSlope: number;         // Getting better over time?

  // STATUS indicators
  reputationGrowthRate: number;       // Climbing the ranks?
  endorsementCount: number;           // describe.net seals earned?
  categoryMasteryCount: number;       // How many categories mastered?
}
```

**Dashboard Section**: "Worker Growth" tab showing these metrics.

---

### 170. Add Swap Test API endpoint
**Priority**: P2
**Status**: [ ] Not started
**Files**: `mcp_server/api/swap_test.py`

**Source**: Future of Work essay - The Swap Test concept

Before posting a task, agents can validate it truly needs a human:

**API**:
```python
@app.post("/api/v1/task/validate-human-required")
async def validate_human_required(task: TaskSpec) -> SwapTestResult:
    """
    Runs the Swap Test: Can AI do this task equally well?

    Returns:
    - human_required: bool
    - confidence: float (0-1)
    - reason: str (why human is/isn't required)
    - suggestions: List[str] (if AI could do it, how)
    """
    result = await swap_test_evaluator.evaluate(task)

    if not result.human_required:
        # Suggest AI alternatives
        return SwapTestResult(
            human_required=False,
            confidence=result.confidence,
            reason="This task can be completed by AI",
            suggestions=[
                "Use Claude for text extraction",
                "Use GPT-4V for image analysis",
                "Use Perplexity for research"
            ]
        )

    return SwapTestResult(
        human_required=True,
        confidence=result.confidence,
        reason=result.human_reason,  # e.g., "Requires physical presence"
        suggestions=[]
    )
```

**Use Cases**:
- Prevent wasteful bounties for AI-doable tasks
- Educate agents on when to use Execution Market vs AI
- Reduce disputes (task was misspecified)

---

### 171. Executor Skill Stack Development Program
**Priority**: P3
**Status**: [ ] Not started
**Files**: `docs/programs/skill-stack.md`

**Source**: Future of Work essay - Post-Labor Skill Stack

The essay defines 5 levels: Agency > Taste > Perspective > Persuasion > Technical.

**Execution Market Training Program** (optional for workers):

| Level | Execution Market Implementation | Unlock |
|-------|----------------------|--------|
| **Technical** | Complete onboarding, pass basic verification | Access to Category A tasks |
| **Persuasion** | N/A (Execution Market is transactional) | - |
| **Perspective** | Complete diverse task types, earn cross-category badges | Access to Category C tasks |
| **Taste** | Become validator, curate quality | Validator status + fees |
| **Agency** | Build reputation, set own rates, choose specialization | Premium task access |

**Implementation**:
- Badge system tied to skill stack levels
- describe.net seals for each level achieved
- Higher levels = higher bounty access

---

### 172. "Work That Matters" Positioning Update
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/marketing/positioning.md`, README.md

**Source**: Future of Work essay - Meaning Economy positioning

Update Execution Market's positioning to emphasize philosophical differentiation:

**Current**: "Gente para Agentes" (tactical)
**Enhanced**: "The Human Layer for the AI Economy" (strategic)

**Messaging Framework**:
```
Headline: Work That Matters
Subhead: In an AI world, humans do what machines can't.

Value Props:
1. Physical presence when AI needs eyes on the ground
2. Legal authority when AI needs human accountability
3. Human judgment when AI needs taste and context
4. Real-world action when AI needs hands

Positioning Statement:
"Execution Market connects AI agents with human workers for tasks that require
physical presence, legal authority, or human judgment—the work that
matters in an automated world."
```

**Tagline Options**:
- "Work that matters, by humans who matter"
- "The meaning economy, built for AI"
- "Where human work has value"

---

## AQAL Framework Integration (I & WE Quadrants)

> Source: `brainstorming/from_aqal_wilber_em_20260122.md`
> Analysis: Execution Market is strong in IT (9/10) and ITS (8/10) but weak in I (4/10) and WE (3/10)
> Priority: HIGH - Without I and WE, Execution Market is just another gig platform

### 173. Worker Dignity Narrative
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/philosophy/dignity.md`, README.md
**AQAL Quadrant**: I (Interior Individual)

**Source**: AQAL analysis - Execution Market needs to answer "why work here?" beyond "fast payment"

**Current State**:
- Execution Market only talks about: "instant x402 payments", "no intermediaries"
- This is IT language (technical benefits)
- Missing: dignity, autonomy, ownership, meaning

**Narrative Elements to Develop**:
```markdown
## Why Execution Market is Different (Worker Perspective)

### 1. Ownership of Your Work
- Your reputation is YOURS (on-chain, portable via ERC-8004)
- No platform can "deactivate" you arbitrarily
- Your skills are verified, not hidden behind platform metrics

### 2. Dignity in Every Task
- Clear instructions before acceptance (immutable bounties)
- Fair dispute resolution (not "platform decides")
- Transparent pricing (no hidden fees)

### 3. You're a Partner, Not a Vendor
- Workers can vote on fee structure, categories, rules
- Community governance, not corporate fiat
- "Chambeadores" as identity, not "gig workers"

### 4. Meaning in the AI Economy
- You do what AI cannot: presence, judgment, authority
- Your work has value BECAUSE it's human
- Not competing with AI, complementing it
```

**Success Metrics**:
- [ ] Draft narrative document
- [ ] Test with 5 potential workers for resonance
- [ ] Update README and marketing materials

---

### 174. Multi-Level Onboarding Flows
**Priority**: P1
**Status**: [ ] Not started
**Files**: `web_app/onboarding/`, `mcp_server/onboarding/`
**AQAL Quadrant**: I (Interior Individual)

**Source**: AQAL developmental levels - different workers have different motivations

Design onboarding paths for different developmental levels:

| Level | Color | Executor Type | Onboarding Flow |
|-------|-------|---------------|-----------------|
| 3 | Red | "Quick earner" | "Gana dinero ahora" → 3 clicks to first task |
| 4 | Blue | "Rule follower" | "Guía completa" → Tutorial, rules, expectations |
| 5 | Orange | "Optimizer" | "Maximiza tus ganancias" → Dashboard, analytics |
| 6 | Green | "Community member" | "Únete a la comunidad" → Community features first |

**Implementation**:
```typescript
// Onboarding quiz to determine level
interface OnboardingQuiz {
  questions: [
    "What's most important to you?",
    // Options map to levels:
    // - "Getting paid fast" → Red
    // - "Clear rules and fairness" → Blue
    // - "Earning the most I can" → Orange
    // - "Being part of something bigger" → Green
  ]
}

// Route to appropriate onboarding
function getOnboardingFlow(level: Level): OnboardingFlow {
  switch(level) {
    case 'red': return quickEarnerFlow();   // Skip tutorials
    case 'blue': return ruleFollowerFlow(); // Full tutorial
    case 'orange': return optimizerFlow();  // Dashboard focus
    case 'green': return communityFlow();   // Community first
  }
}
```

**Success Metrics**:
- [ ] Design 4 distinct flows
- [ ] Implement quiz routing
- [ ] A/B test completion rates by level

---

### 175. Executor Community Identity ("Chambeadores")
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/community/`, `web_app/community/`
**AQAL Quadrant**: WE (Interior Collective)

**Source**: AQAL analysis - WE quadrant is weakest (3/10)

**Problem**: Execution Market executors have no collective identity. They're just "workers on platform X".

**Solution**: Create identity, rituals, and community artifacts.

**Community Elements**:

1. **Name**: "Chambeadores" (not "workers", "executors", "gig workers")
   - Verb form: "Chambear" = to work on Execution Market
   - Past tense: "Chambeé una verificación" = I did a verification task

2. **Visual Identity**:
   - Badge system with describe.net seals
   - Profile frame for verified Chambeadores
   - Category badges (Physical, Knowledge, Authority, etc.)

3. **Rituals**:
   - First task celebration
   - 100 tasks milestone
   - Category completion badges
   - Monthly top performers recognition

4. **Spaces**:
   - Discord server with category channels
   - Telegram groups by region
   - Weekly AMA with Execution Market team

5. **Artifacts**:
   - "Código del Chambeador" (code of conduct written BY workers)
   - Stories of successful Chambeadores
   - "Tips from the community" wiki

**Implementation**:
```yaml
community_features:
  phase_1:
    - Discord server setup
    - Badge system in web app
    - describe.net seal integration
  phase_2:
    - Regional Telegram groups
    - Monthly recognition system
    - Community wiki
  phase_3:
    - DAO governance for workers
    - Worker-written code of conduct
    - Annual Chambeador summit (virtual)
```

**Success Metrics**:
- [ ] Discord active members: 100+ in 3 months
- [ ] Worker retention increase: 20%
- [ ] Net Promoter Score from workers: >40

---

### 176. Worker Voice in Governance
**Priority**: P2
**Status**: [ ] Not started
**Files**: `contracts/EMGovernance.sol`, `web_app/governance/`
**AQAL Quadrant**: WE (Interior Collective)

**Source**: AQAL Green level - "pluralistic, community governance"

**Problem**: Most gig platforms have zero worker input. Workers are "users", not stakeholders.

**Solution**: Formal governance mechanisms for Chambeadores.

**Governance Rights for Workers**:

| Decision Area | Worker Input | Weight |
|---------------|--------------|--------|
| Fee structure | Vote on fee changes | 50% of vote |
| New categories | Propose and vote | 50% of vote |
| Dispute rules | Propose changes | 30% of vote |
| Platform features | Feature requests | Advisory |

**Mechanism**:
```solidity
// Not token-weighted! Reputation-weighted.
// Each Chambeador gets voting power based on:
// - Tasks completed
// - Success rate
// - Time on platform
// NOT based on tokens held (plutocracy prevention)

function calculateVotingPower(address worker) returns (uint256) {
    uint256 tasks = completedTasks[worker];
    uint256 successRate = getSuccessRate(worker);
    uint256 tenure = block.timestamp - registrationTime[worker];

    // Power = sqrt(tasks) * successRate * log(tenure)
    // Square root prevents whale dominance
    return sqrt(tasks) * successRate * log(tenure);
}
```

**Governance Calendar**:
- Monthly: Feature prioritization vote
- Quarterly: Fee review vote
- Annually: Code of conduct review

---

### 177. Meaning Metrics Integration (from Merit0)
**Priority**: P1
**Status**: [ ] Not started
**Files**: `mcp_server/metrics/meaning.py`, `web_app/dashboard/meaning.tsx`
**AQAL Quadrant**: I (Interior Individual)

**Source**: AQAL analysis + Future of Work essay + Merit0 integration

**Problem**: Execution Market only tracks $$ earned. This is Orange-level thinking.

**Solution**: Track "meaning metrics" alongside financial metrics.

**Meaning Metrics**:
```typescript
interface MeaningMetrics {
  // Financial (existing)
  totalEarned: number;
  avgTaskValue: number;

  // NEW: Impact metrics
  agentFeedback: {
    average: number;        // 1-5 rating from agents
    comments: string[];     // Qualitative feedback
  };

  // NEW: Growth metrics
  skillsUnlocked: string[]; // Categories accessed
  milestonesHit: string[];  // "First task", "100 tasks", etc.

  // NEW: Community metrics
  helpGiven: number;        // Helped other workers
  disputesWon: number;      // Successful dispute resolutions

  // NEW: Purpose metrics (from Merit0)
  meaningScore: number;     // Aggregate meaning score
  impactStories: string[];  // "Your verification helped agent X achieve Y"
}
```

**Dashboard Design**:
```
┌─────────────────────────────────────────────────────────────┐
│  Your Execution Market Impact                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  💰 Earned: $1,234          🎯 Tasks: 147                   │
│                                                              │
│  ⭐ Agent Rating: 4.8/5     🏆 Rank: Top 15%                │
│                                                              │
│  📈 Growth This Month:                                       │
│  ├─ New categories unlocked: 2                               │
│  ├─ Milestone: "100 Tasks"                                   │
│  └─ Skill level: Expert in Physical Presence                 │
│                                                              │
│  💬 Recent Feedback:                                         │
│  "Your verification was crucial for our supply chain         │
│   monitoring agent." - ColmenaForager                        │
│                                                              │
│  🌟 Meaning Score: 78/100 (Good!)                            │
│  You're in the top 25% of impactful workers.                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Integration with Merit0**:
- Merit0 provides real-time value scoring
- Execution Market feeds Merit0 with task completion data
- Merit0 returns meaning score for worker dashboard

---

### 178. describe.net Seal Integration for Worker Identity
**Priority**: P1
**Status**: [ ] Not started
**Files**: `integrations/describenet/`, `web_app/profile/seals.tsx`
**AQAL Quadrant**: WE (Interior Collective)

**Source**: AQAL analysis + describe.net synergy (Score 10)

**Problem**: Worker reputation exists only within Execution Market. Not portable.

**Solution**: Use describe.net seals as portable, verifiable worker credentials.

**Seal Types for Chambeadores**:
```yaml
em_seals:
  # Category completion seals
  physical_presence_pro:
    name: "Physical Presence Pro"
    criteria: "50+ Category A tasks with >4.5 rating"
    visual: "🏃‍♂️"

  knowledge_keeper:
    name: "Knowledge Keeper"
    criteria: "30+ Category B tasks (document scanning/access)"
    visual: "📚"

  authority_holder:
    name: "Authority Holder"
    criteria: "20+ Category C tasks (notary, certified)"
    visual: "⚖️"

  action_hero:
    name: "Action Hero"
    criteria: "100+ Category D tasks (simple physical)"
    visual: "💪"

  bridge_builder:
    name: "Bridge Builder"
    criteria: "40+ Category E tasks (digital-physical)"
    visual: "🌉"

  # Meta seals
  chambeador_verified:
    name: "Verified Chambeador"
    criteria: "Completed onboarding + 10 tasks"
    visual: "✅"

  chambeador_elite:
    name: "Elite Chambeador"
    criteria: "Top 10% in any category"
    visual: "👑"

  community_builder:
    name: "Community Builder"
    criteria: "Helped 10+ new workers"
    visual: "🤝"
```

**Portable Identity**:
- Seals live on-chain (ERC-8004 + describe.net)
- Worker can show seals on other platforms
- Other platforms can verify seal validity
- "Take your reputation with you"

---

## IRC-FIRST MVP PATHWAY (From claude-irc-bridge 2026-01-24)

> Source: `control-plane/brainstorming/from_claude_irc_bridge_em_20260124.md`
> Pattern: Brain Agent Orchestration (PATTERNS.md#brain-agent-orchestration)

### 178. Fork claude-irc-bridge as em-irc-prototype
**Priority**: P1
**Status**: [ ] Not started
**Files**: New repo `em-irc-prototype/`

**Insight**: claude-irc-bridge has 70% of Execution Market's architecture already built:
- Brain Agent = EM Task Router
- Task Queue (SQS/Redis) = EM Task Queue
- Claude Code Executor = Human Worker (swap out!)
- IRC Broadcast = Status updates to requester
- Memory/Wisdom layers = Worker reputation + project history

**Steps**:
1. Fork `claude-irc-bridge` repo
2. Replace Claude Code executor with human worker interface
3. Add `!bounty` command for task creation with rewards
4. Add `!claim` command for workers to take tasks
5. Integrate x402 for payments
6. IRC logs → ChainWitness for audit trail

**Why P1**: Fastest path to Execution Market MVP. IRC interface already works.

---

### 179. Implement `!bounty` IRC command
**Priority**: P1
**Status**: [ ] Not started
**Files**: `em-irc-prototype/commands/bounty.py`

```python
async def handle_bounty(channel: str, user: str, args: str):
    """
    !bounty <amount> <description>
    Example: !bounty 5 USDC "Verify store hours at 123 Main St"
    """
    amount, token, description = parse_bounty_args(args)

    # Create task
    task = await create_task(
        requester=user,
        description=description,
        reward_amount=amount,
        reward_token=token,
    )

    # Create x402 escrow
    escrow = await x402.create_escrow(
        agent=user,
        amount=amount,
        task_cid=task.content_cid,
    )

    # Announce in channel
    await announce(channel, f"📋 BOUNTY #{task.id}: {description} | 💰 {amount} {token} | !claim {task.id}")

    return task
```

---

### 180. Implement `!claim` and `!submit` IRC commands
**Priority**: P1
**Status**: [ ] Not started
**Files**: `em-irc-prototype/commands/claim.py`, `commands/submit.py`

```python
async def handle_claim(channel: str, worker: str, task_id: str):
    """Worker claims a bounty"""
    task = await get_task(task_id)

    if task.status != "published":
        return await reply(channel, f"@{worker}: Task already claimed")

    await update_task(task_id, status="claimed", worker=worker)
    await announce(channel, f"✅ @{worker} claimed #{task_id}")

async def handle_submit(channel: str, worker: str, task_id: str, proof: str):
    """Worker submits proof of completion"""
    task = await get_task(task_id)

    if task.worker != worker:
        return await reply(channel, f"@{worker}: Not your task")

    # Pin proof to IPFS
    proof_cid = await ipfs.pin(proof)

    # Trigger verification
    await verify_and_pay(task_id, proof_cid)
```

---

### 181. Wire x402 payments to IRC bot
**Priority**: P1
**Status**: [ ] Not started
**Files**: `em-irc-prototype/payments/x402_bridge.py`

```python
from uvd_x402_sdk import X402Client

class IRCPaymentBridge:
    def __init__(self):
        self.x402 = X402Client(
            facilitator=os.getenv("X402_FACILITATOR"),
            network="base",
        )

    async def create_bounty_escrow(self, agent: str, amount: Decimal, task_cid: str):
        """Create escrow for bounty"""
        return await self.x402.escrow.create(
            payer=agent,
            amount=amount,
            token="USDC",
            reference=task_cid,
            conditions={"task_complete": True},
        )

    async def release_to_worker(self, escrow_id: str, worker_address: str):
        """Release payment on task completion"""
        return await self.x402.escrow.release(
            escrow_id=escrow_id,
            recipient=worker_address,
        )
```

---

### 182. Add ChainWitness notarization for IRC logs
**Priority**: P2
**Status**: [ ] Not started
**Files**: `em-irc-prototype/audit/chainwitness.py`

```python
async def notarize_task_lifecycle(task_id: str, events: List[TaskEvent]):
    """Notarize complete task lifecycle via ChainWitness"""
    # Compile evidence
    evidence = {
        "task_id": task_id,
        "bounty_posted": events.filter(type="posted"),
        "claimed": events.filter(type="claimed"),
        "submitted": events.filter(type="submitted"),
        "verified": events.filter(type="verified"),
        "paid": events.filter(type="paid"),
        "irc_logs": events.get_raw_logs(),
    }

    # Pin and notarize
    evidence_cid = await ipfs.pin(evidence)
    return await chainwitness.notarize(evidence_cid)
```

**Benefits**:
- Immutable proof of task completion
- Dispute resolution with evidence
- Regulatory compliance for enterprise

---

### 183. Recruit initial workers via IRC/Discord
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/worker-acquisition/irc-strategy.md`

**Strategy**: Recruit first 10-20 workers from technical communities who are already on IRC:
- #ultravioleta-dao (our channel)
- Developer Discord servers
- Crypto communities with IRC presence

**Why this works**:
- Technical users understand crypto payments
- IRC users are comfortable with text commands
- Low friction onboarding (no app download)
- Perfect for dogfooding (our own community first)

**First Tasks**:
- Simple verification tasks ($1-5)
- Document collection ($5-10)
- Location-based recon ($5-10)

---

### 184. Measure and compare to web UI timeline
**Priority**: P1
**Status**: [ ] Not started
**Files**: `docs/experiments/irc-vs-web.md`

**Hypothesis**: IRC-first MVP ships 4-6 weeks faster than Web UI.

**Metrics to track**:
- Time to first completed task
- Time to 10 completed tasks
- Worker acquisition cost (IRC vs Web)
- Worker retention rate
- Agent satisfaction

**Decision Point**: If IRC MVP works, delay Web UI indefinitely. If IRC fails to gain traction, pivot to Web.

---

## References

### Stream Sources (2026-01-21)
- Stream: `streamers/0xultravioleta/20260121/2676209434`
- Ideas: `ideas_extraidas.json`
- Summary: `resumen_telegram.txt`, `resumen_completo.txt`, `analisis_completo.txt`
- Segments: `segmentos/20260121_segmento_1.txt`
- Karma Hello: `karma-hello/logs/chat/0xultravioleta/20260121/full.txt`

### Stream Sources (2026-01-20)
- Stream: `streamers/0xultravioleta/20260120/2675352141`
- Brainstorm: `brainstorming/from_em_chimba_stream_20260120.md`
- Summary: `resumen_completo.txt`
- Transcript: `analisis_completo.txt`

### Brainstorming Sessions
- Brainstorm: `brainstorming/em_enterprise_describenet_20260121.md` **(NEW - psilocibin3 + describe.net)**
- Brainstorm: `brainstorming/session_em_immutable_bounties_20260119.md`
- Brainstorm: `brainstorming/session_em_execution_layer_v2_20260120.md`
- Brainstorm: `brainstorming/session_merit0_em_realtime_earn_20260120.md`
- Brainstorm: `brainstorming/em_dynamic_bounty_20260119.md`
- Brainstorm: `brainstorming/em_x402r_retry_mechanism_20260119.md`
- Brainstorm: `brainstorming/em_task_pipeline_20260119.md`
- Brainstorm: `brainstorming/em_global_reputation_20260119.md`
- Brainstorm: `brainstorming/session_em_protocol_deep_20260112_1230.md`
- Brainstorm: `brainstorming/session_embridge_deep_20260112_1230.md`
- Brainstorm: `brainstorming/session_em_agent_scenarios_20260111_1500.md`
- Brainstorm: `brainstorming/session_em_launch_strategy_20260114.md`
- Brainstorm: `brainstorming/thinking_tools_em_staircase_20260112.md`
- Brainstorm: `brainstorming/from_abracadabra_em_stream_20260112.md`
- Pattern source: `brainstorming/from_anthropic_long_running_agents_20260119.md`
- Anthropic article: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- **Meaning Economy**: `brainstorming/from_future_of_work_20260122.md` (Dan Koe essay)
- **IRC-First MVP**: `brainstorming/from_claude_irc_bridge_em_20260124.md` (claude-irc-bridge architecture → Execution Market)

### Ecosystem Synergies (Grep Search 2026-01-21)
- Synergy: `ideas/x402-insurance/SYNERGIES.md` (Score 10)
- Synergy: `ideas/tribunal/SYNERGIES.md` (Score 10)
- Synergy: `ideas/tribunal/SPEC.md`
- Synergy: `ideas/private-task-markets/SPEC.md`
- Synergy: `ideas/describe-net/SYNERGIES.md` (Score 10)
- Synergy: `ideas/tee-mesh/SYNERGIES.md` (Score 8)
- Synergy: `ideas/contexto-match/SYNERGIES.md` (Score 10)
- Synergy: `ideas/karmacadabra-realtime/PROGRESS.md`
- Synergy: `ideas/merit0/PROGRESS.md`
- Ecosystem: `ECOSYSTEM.md`
- Integration: `INTEGRATION.md`
- Questions: `questions/em.md`

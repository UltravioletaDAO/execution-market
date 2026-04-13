# Skill: Launch Validation Team

Spawn a standardized multi-agent team to validate a concept. Runs PM + HR + Specialists + Devil's Advocate in parallel. Produces a comprehensive viability report.

## Trigger

User says: "launch the team", "lanza el equipo", "validate this with agents", "run the full validation", "deep dive X", "is this real or hype".

## Purpose

Validated against: Tesla Fleet (killed), Option B tweet (verified + rewritten), CARRIERaaS (CAUTION with 3 paths), CITYaaS (fact-checked + mayor-ready). The pattern works. This skill makes it reusable.

## When to Use

- Concept passed initial scorecard (validate-concept skill) but has CAUTION flags
- High-stakes pitch (mayor, investor, partner)
- Public-facing content with real numbers (tweet, LinkedIn, gist)
- Major architectural decision
- User explicitly wants "ruthless validation"

## Standard Team Composition

Launch these agents IN PARALLEL (all in a single message with multiple tool calls):

### 1. Project Manager (coordinator, doesn't execute)
**Prompt template:**
```
You are the PROJECT MANAGER. You DO NOT execute research. Your job is to organize and define the work for other specialized agents.

Mission: Validate [CONCEPT NAME].

Source files: [list relevant files]

Deliverables:
1. Research plan — 8-12 specific questions
2. Task assignments — which specialist owns which question
3. Critical path — the 3 questions whose NO answers kill the concept
4. Risk register — top 5 risks with severity
5. Scope discipline — what you are NOT doing

DO NOT execute research. DO NOT validate numbers. Organize only.
```

### 2. HR / Recruiter (defines the team)
**Prompt template:**
```
You are the HR / RECRUITING SPECIALIST. You DO NOT execute research. Your job is to define EXACT expert profiles needed to validate a complex concept.

Mission: [CONCEPT NAME]

Deliverables:
1. Specialist roster — 6-8 profiles needed with role, expertise, deliverable, anti-profile
2. Recruiting brief — 100-word "job description" per role
3. Team composition logic — why this mix covers the validation surface
4. Devil's advocate slot — one specialist whose job is to argue against

Domains to consider: Tech feasibility, legal, competitive, economics, data quality, partnership, buyer demand.
```

### 3-6. Specialized Researchers (parallel)

Launch as many as needed (typically 3-5) based on the concept's risk profile. Each specialist has:
- ONE specific domain
- ONE specific deliverable
- Source requirements (web search for external claims)
- Verdict verdict format (VERIFIED / PARTIAL / INCORRECT / UNVERIFIABLE)

Common specialists:

**Tech Reality Auditor** — Reads API docs, SDK source, contracts, ToS. Verifies technical premises with primary sources.

**Legal Scanner** — Identifies required licenses, regulatory risk, cross-border issues. Produces jurisdiction matrix.

**Competitor Mapper** — Finds closest 3-5 competitors. Analyzes positioning, moats, failure modes.

**Unit Economist** — Builds bottom-up model with real buyer WTP + real worker cost. Produces sensitivity table.

**Data Quality Analyst** — Can evidence be produced, verified, legally admissible?

**Partnership Scout** — Finds 3-5 named first-customer targets with entry points.

**Regulatory Strategist** — Heat map of jurisdictions, insurance stack, legal framing. Useful for anything that crosses borders or touches regulated industries.

### 7. Devil's Advocate (mandatory)
**Prompt template:**
```
You are the DEVIL'S ADVOCATE. Every other agent is trying to validate this concept. Your job is to argue AGAINST it as forcefully as possible. Find every reason it WON'T work.

Source files: [list]

Cover:
1. Why [gatekeeper] won't do this
2. Why [users] won't care
3. Why the data/product isn't valuable
4. Why the math doesn't work
5. Why [competitors] failed at this
6. Regulatory landmines
7. The real reason this won't get adopted

End with a verdict: VIABLE / VIABLE WITH CHANGES / NOT VIABLE.

Be brutal. Don't soft-pedal. The user explicitly wants ruthless critique.
```

## Workflow

### Step 1: Read the Concept
Understand what's being validated. Get the pitch, source docs, and user's specific concerns.

### Step 2: Launch Agents in Parallel
Use a single message with multiple `Agent` tool calls. All agents run concurrently.

Background mode is REQUIRED for validation teams. `run_in_background: true` on each agent. This prevents blocking the conversation.

### Step 3: Wait for Results
As each agent completes, it notifies you. Read the output. Do NOT consolidate until all agents have returned.

### Step 4: Consolidate the Verdict

Combine outputs into a single recommendation:

```markdown
# [Concept Name] Validation Report

## The Team
- PM: [summary]
- HR: [team composition]
- Specialists: [list of roles]
- Devil's Advocate: [summary]

## The 3 Kill-Switches
1. [question] — [Y/N/UNKNOWN] — [evidence]
2. [question] — [Y/N/UNKNOWN] — [evidence]
3. [question] — [Y/N/UNKNOWN] — [evidence]

## 6-Axis Verdict
- A1 Technical Reality: [PASS/CAUTION/KILL]
- A2 Legal: [PASS/CAUTION/KILL]
- A3 Data Quality: [PASS/CAUTION/KILL]
- A4 Economics: [PASS/CAUTION/KILL]
- A5 Partnership: [PASS/CAUTION/KILL]
- A6 Buyer Demand: [PASS/CAUTION/KILL]

## The Brutal Summary
[One-paragraph verdict synthesizing all agents]

## 3 Paths Forward (if CAUTION)
1. [narrower scope]
2. [different customer]
3. [different jurisdiction/architecture]

## Kill List (if KILL)
- What to remove from the concept
- What to archive to graveyard

## Next Actions
- [concrete action with owner + deadline]
```

### Step 5: Save to Vault

Save the full report to `vault/19-validation/scorecards/[concept-slug]-validation.md` with proper frontmatter.

### Step 6: Generate Scorecard

Run the `validate-concept` skill on the concept using the team's findings to produce the 1-page scorecard.

## Anti-Patterns (Do NOT Do)

- ❌ Launch sequentially instead of parallel (wastes time)
- ❌ Skip the Devil's Advocate (they're the most important one)
- ❌ Consolidate before all agents return (incomplete picture)
- ❌ Let the team's optimism override clear KILL signals
- ❌ Validate multiple concepts in one team run (one at a time)
- ❌ Launch a team without reading the source concept first

## Past Validation Runs (Reference)

### Tesla Fleet (2026-04-08)
- Team: PM + HR + CITYaaS Cross-Ref + Tesla Validator + Devil's Advocate
- Result: KILLED on F1 (Fleet API doesn't expose frames)
- Salvage: Fleet Telemetry + GPS + phone photos + multi-OEM
- Lesson: Always read the actual API docs before strategy

### Option B Tweet (2026-04-08)
- Team: Source Verifier + light PM review
- Result: REWRITTEN (500M→730M, VW ADMT→MOIA America, USB dashcam→USB dongle)
- Lesson: Rebrands and stale numbers kill credibility

### CARRIERaaS (2026-04-08)
- Team: PM + CARRIERaaS Deep Validator + Regulatory Strategist
- Result: CAUTION — 3 paths forward (Tallinn → Mexico City → Dubai)
- Lesson: Multi-hop trustless is a fantasy; single-hop is real

### CITYaaS (2026-04-04)
- Team: Source fact-checker + Reality-check-model + Precedent research
- Result: FACT-CHECKED + mayor-ready gist published
- Lesson: Every number needs a primary source before going to a real audience

## Budget & Timing

- **Small team (3 specialists):** ~20-30 minutes wall clock, ~5-10 minutes tool time
- **Standard team (5 specialists + PM + HR + devil's advocate):** ~30-60 minutes wall clock
- **Large team (7+ specialists):** Only for concepts with cross-border legal + technical + economic validation needs

Each agent consumes context. Don't launch 10 agents when 5 would do.

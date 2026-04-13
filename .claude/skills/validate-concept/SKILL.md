# Skill: Validate Concept

Apply the Meta-Validation Framework to any new product concept before investing strategy/engineering effort. Produces a 1-page viability scorecard with GO/CAUTION/KILL verdict.

## Trigger

User says: "validate concept", "validar idea", "run the framework on X", "is this viable", "should we build this", "kill or keep".

## Purpose

Prevent the Tesla Fleet failure mode: writing a 269-line strategy doc before anyone checked whether the core technical premise was true. The framework exists to catch that on turn 1, not turn 20.

## Source

Framework defined in `.unused/future/META_VALIDATION_FRAMEWORK.md` (or `vault/19-validation/framework/meta-validation-framework.md` after migration). Read it first.

## Workflow

### Step 1: Identify the Concept
Get from the user:
- Concept name
- One-line pitch (≤140 chars)
- What it claims to do
- What infrastructure it depends on

### Step 2: Check Against 5 Failure Modes (F1-F5)

For each, ask yes/no:

| # | Failure Mode | Question | If YES → |
|---|--------------|----------|----------|
| F1 | False technical premise | Does the pitch assume a capability that isn't publicly documented? | Read the actual API docs before anything else |
| F2 | Fabricated unit economics | Is there a $/day or $/unit number without a named buyer? | Find one real buyer quote before modeling |
| F3 | Centralized gatekeeper blocker | Is there ONE company that can say no and kill it? | Ask: what's the probability they say yes? |
| F4 | Competitor already solved it | Have you searched for "X already does Y"? | Find closest 3 competitors before pitching |
| F5 | Legal landmine under the surface | Does it touch privacy, mail, money transmission, labor classification? | Pre-flight legal scan per jurisdiction |

Any YES = high risk. Proceed with extra scrutiny.

### Step 3: Define the 3 Kill-Switches

Every concept must have 3 concrete yes/no questions whose NO answer kills it immediately.

Template:
```
Kill-Switch #1 (Technical): Does [primitive X] actually expose [capability Y] today?
  - NO path: Concept is dead unless [specific alternative exists]
  - Evidence required: Direct quote from API docs or test call
  - Owner: Tech-Reality Auditor

Kill-Switch #2 (Economic): Will [buyer type Z] pay at least $[amount] per [unit]?
  - NO path: Concept is unprofitable
  - Evidence required: 1 signed LOI, 3 buyer quotes, or equivalent existing contract
  - Owner: Unit Economist

Kill-Switch #3 (Legal or Gatekeeper): Can we run this without [blocker's permission]?
  - NO path: Concept depends on a gatekeeper who can say no
  - Evidence required: Written legal opinion or ToS reading
  - Owner: Legal Scanner
```

Write these BEFORE doing any research. If you can't write them concretely, the concept isn't ready.

### Step 4: Score Against 6 Axes

| Axis | Question | PASS | CAUTION | KILL |
|------|----------|------|---------|------|
| A1. Technical Reality | Does every piece of tech referenced exist and do what we claim? | All verified | Beta/announced | Fiction/blocked |
| A2. Legal & Regulatory | Can this run in target jurisdictions without licenses we don't have? | Marketplace carve-out | Needs legal opinion | Requires license we lack |
| A3. Data Quality | Can evidence be produced, verified, legally useful? | EM stack covers | Needs new primitive | Can't be verified |
| A4. Economics | Does math close with realistic costs and buyer WTP? | WTP > cost + margin | Works only at scale | Negative at maturity |
| A5. Partnership/GTM | Concrete first customer or partner? | Named | Analogous exists | No target |
| A6. Buyer Demand | Evidence anyone pays for this today? | Incumbent doing it | Adjacent spend | Zero evidence |

### Step 5: Produce the 1-Page Scorecard

Generate the scorecard in this exact format and save to `vault/19-validation/scorecards/[concept-slug]-scorecard.md`:

```markdown
---
date: YYYY-MM-DD
type: concept-scorecard
status: draft | validated | killed
concept: [name]
verdict: GO | CAUTION | KILL
related:
  - "[[concept-file]]"
  - "[[meta-validation-framework]]"
tags:
  - type/scorecard
  - domain/validation
---

# [Concept Name] — Viability Scorecard

**One-line pitch:** [≤140 chars]

## The 3 Kill-Switches
1. [technical question] — [ Y / N / UNKNOWN ]
2. [economic question] — [ Y / N / UNKNOWN ]
3. [legal/gatekeeper question] — [ Y / N / UNKNOWN ]

## 6-Axis Scorecard
- **A1. Technical Reality:** [ PASS / CAUTION / KILL ] — [reason]
- **A2. Legal & Regulatory:** [ PASS / CAUTION / KILL ] — [reason]
- **A3. Data Quality:** [ PASS / CAUTION / KILL ] — [reason]
- **A4. Economics:** [ PASS / CAUTION / KILL ] — [reason]
- **A5. Partnership/GTM:** [ PASS / CAUTION / KILL ] — [reason]
- **A6. Buyer Demand:** [ PASS / CAUTION / KILL ] — [reason]

## Top 3 Risks
1. [risk] — [likelihood×impact score] — [mitigation or "kill switch"]
2. [risk] — [score] — [mitigation]
3. [risk] — [score] — [mitigation]

## First Real Customer
[person/company] — [contact path] — [why them]

## What EM Already Has (% reuse)
[e.g. 70% — escrow, evidence pipeline, ERC-8004, worker pool]

## Verdict
**[GO / CAUTION / KILL]**

**Next step:** [concrete action with owner and deadline]
```

### Step 6: Apply Verdict Rules

- **GO** = 6/6 PASS, or 5 PASS + 1 CAUTION with mitigation plan → proceed to full deep-dive
- **CAUTION** = 4-5 PASS, no KILL → focused research sprint on CAUTION axes before committing
- **KILL** = Any 1 KILL on any axis → archive to `vault/21-graveyard/` with post-mortem

### Step 7: Notify User

Print in 3 lines max:
```
Scorecard saved: [[concept-name-scorecard]]
Verdict: [GO / CAUTION / KILL]
Next: [action]
```

## Anti-Patterns (Do NOT Do)

- ❌ Fill the scorecard with optimism. Every PASS needs evidence.
- ❌ Skip the kill-switches. They're the whole point of the framework.
- ❌ Validate multiple concepts in one pass. One at a time.
- ❌ Accept "cities" or "insurance companies" as a first customer. Named or nothing.
- ❌ Write the strategy doc before the scorecard. Scorecard first, always.

## Universal Insights (Must Apply)

1. "Infrastructure already exists" is usually a lie about the 10% that matters.
2. "Zero user effort" claims need adversarial review.
3. Write the scorecard BEFORE the strategy document.
4. Specialist disagreement is a feature.
5. "X already does Y, but we do Y+Z" is the highest-risk pitch class.
6. Name the first customer or kill the concept.

# Skill: Create Master Plan

Create a comprehensive, phased master plan for any feature, bug fix, or initiative. Follows the user's mandatory workflow: audit first, then structured phases with granular tasks.

## Trigger

User says: "master plan", "create master plan", "crea el master plan", "hazme el plan", or similar.

## Workflow

### Step 1: Audit & Research (Parallel Agents)

Launch 2-4 agents in parallel to deeply audit the problem space:

- **Agent 1**: Backend/server code audit — find exact file:line for every relevant function, current behavior, gaps
- **Agent 2**: Frontend/UI audit — find exact file:line for components, services, hooks affected
- **Agent 3**: Test coverage audit — find existing tests, identify gaps, recommend new test cases
- **Agent 4** (if needed): Schema/infrastructure audit — DB tables, migrations, API contracts

Each agent reports:
- Exact function names and line numbers
- Current validations (what IS checked)
- Missing validations (what SHOULD be checked)
- Code snippets (5-10 lines) around each gap

### Step 2: Write the Master Plan

Create a markdown file at `docs/planning/MASTER_PLAN_<TOPIC>.md` with this structure:

```markdown
---
date: YYYY-MM-DD
tags:
  - type/plan
  - domain/<domain>
  - priority/<p0|p1|p2>
status: active
related-files:
  - path/to/file1.py
  - path/to/file2.tsx
---

# MASTER PLAN: <Title>

**Severity:** P0/P1/P2
**Created:** YYYY-MM-DD
**Bug/Feature:** One-line description
**Impact:** What happens if not fixed / what value does this add

## Summary

2-3 paragraphs explaining the problem/feature, root cause, and approach.

---

## Phase 1: <Phase Name> (P0 - CRITICAL)

> One-line description of what this phase accomplishes.

### Task 1.1: <Task Title>

- **File:** `exact/path/to/file.py` -- `function_name()` (line ~NNN)
- **Bug/Issue:** ISSUE-ID -- One-line description
- **Fix:** Specific description of what to change (with code snippet if helpful)
- **Edge case:** Any edge cases to handle (e.g., different modes, backward compat)
- **Validation:** `test_name_that_proves_fix` or manual test description

### Task 1.2: ...

---

## Phase 2: <Phase Name> (P1 - HIGH)

### Task 2.1: ...

---

## Summary

| Phase | Tasks | Priority | Effort |
|-------|-------|----------|--------|
| Phase 1 | N tasks | P0 | ~Xh |
| Phase 2 | N tasks | P1 | ~Xh |
| TOTAL | N tasks | | ~Xh |

## Files Modified (Complete List)

| File | Phase | Changes |
|------|-------|---------|
| `path/to/file` | 1, 3 | Description |
```

### Step 3: Update Memory

Add the new master plan to `MEMORY.md` under "Active Plans" with format:
```
- `docs/planning/MASTER_PLAN_<TOPIC>.md` -- N tasks, M phases (YYYY-MM-DD) (brief description)
```

## Rules

1. **Every task must be atomic** -- one file, one fix, one validation
2. **Every task must have exact file:line** -- no vague references
3. **Every task must have a validation** -- test name or manual verification
4. **Reference audit IDs** when available (ESCROW-001, S-CRIT-01, etc.)
5. **Phases ordered by priority** -- P0 first, P2 last
6. **3-5 phases max** -- don't over-fragment
7. **2-4 tasks per phase** -- keep phases manageable
8. **Include code snippets** for non-obvious fixes
9. **Handle edge cases explicitly** -- different modes, backward compat, Fase 1 vs Fase 2
10. **Never start execution** -- only write the plan. User says "Empieza Phase N" to execute.

## Phase Naming Convention

- Phase 1: Usually "Core Fix" or "Backend Validation" (P0)
- Phase 2: Usually "Safety/Hardening" or "Settlement/Payment Safety" (P0)
- Phase 3: Usually "Frontend/UI" (P1)
- Phase 4: Usually "Test Suite" (P1)
- Phase 5: Usually "Monitoring/Cleanup/Admin" (P2)

## Output

After writing the plan, report to user:
```
Master Plan created: docs/planning/MASTER_PLAN_<TOPIC>.md
- N phases, M tasks total
- Phase 1 (P0): brief description
- Phase 2 (P0): brief description
- ...
- Say "Empieza Phase 1" to begin execution.
```

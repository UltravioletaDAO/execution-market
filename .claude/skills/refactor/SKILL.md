---
name: refactor
description: Systematic code refactoring workflow with incremental changes and test validation. Use when user asks to "refactor", "clean up", "improve code quality", "fix code smells", "reorganize", or wants help improving existing code structure. Handles TypeScript, Python, React components, and general code improvements.
---

# Refactor Skill

Systematic workflow for safe, incremental code refactoring with continuous test validation.

## Prerequisites

- Target file(s) must exist and be readable
- Test suite available (Vitest, Pytest, Jest, etc.)
- Git repository (for safe rollback if needed)

## Workflow Overview

```
1. ANALYZE    Read files, identify issues
2. PLAN       Create TodoWrite task list
3. EXECUTE    Make changes one at a time
4. VALIDATE   Run tests after each change
5. REPORT     Summary of improvements
```

## Phase 1: Analysis

### Step 1.1: Read Target Files

Read all files in scope. For a single file:

```
Read /path/to/target/file.ts
```

For a module/directory, use Glob first:

```
Glob pattern="**/*.ts" path="/path/to/module"
```

Then read each relevant file.

### Step 1.2: Identify Code Smells

Check for these common issues:

**Structural Issues:**
- [ ] Functions > 50 lines (extract smaller functions)
- [ ] Files > 300 lines (consider splitting)
- [ ] Deeply nested conditionals (> 3 levels)
- [ ] Duplicate code blocks
- [ ] God classes/modules doing too much

**TypeScript/JavaScript Specific:**
- [ ] `any` types that should be specific
- [ ] Missing return types on functions
- [ ] Inconsistent error handling (mix of try/catch and .catch())
- [ ] Callback hell (should use async/await)
- [ ] Props drilling (should use context or composition)
- [ ] Inline styles (should use CSS/Tailwind classes)
- [ ] Magic numbers/strings (should be constants)

**React Specific:**
- [ ] Components doing fetch + render (split into container/presenter)
- [ ] useEffect with missing dependencies
- [ ] State that should be derived
- [ ] Missing memoization for expensive computations
- [ ] Event handlers defined inline in JSX

**Python Specific:**
- [ ] Missing type hints
- [ ] Bare except clauses
- [ ] Mutable default arguments
- [ ] Long parameter lists (> 5 params, use dataclass/dict)
- [ ] Missing docstrings on public functions

**General:**
- [ ] Poor variable/function names
- [ ] Dead code (unused imports, unreachable code)
- [ ] Missing or outdated comments
- [ ] Inconsistent formatting

### Step 1.3: Check Test Coverage

Identify which tests cover the target code:

```bash
# TypeScript/React (Vitest)
cd /path/to/project && npm run test -- --reporter=verbose --run

# Python (Pytest)
cd /path/to/project && pytest --collect-only -q
```

Note: If no tests exist, create them first before refactoring.

## Phase 2: Planning

### Step 2.1: Create Task List with TodoWrite

Create granular, reversible tasks ordered by risk (lowest risk first):

```
TodoWrite:
- [ ] 1. Extract constants: Move magic strings to CONSTANTS object
- [ ] 2. Add types: Replace `any` with proper interfaces
- [ ] 3. Extract function: Move validation logic to validateInput()
- [ ] 4. Rename: userInfo -> currentUser for clarity
- [ ] 5. Split component: Extract UserAvatar from UserProfile
- [ ] 6. Add error boundary: Wrap async operations
- [ ] 7. Memoize: Add useMemo for filtered list computation
```

**Task Ordering Principles:**
1. Rename/formatting changes first (lowest risk)
2. Extract constants/types second
3. Extract functions/components third
4. Structural changes last (highest risk)

### Step 2.2: Identify Test Commands

Determine the correct test command for validation:

```bash
# Dashboard (Vitest)
cd dashboard && npm run test

# MCP Server (Pytest)
cd mcp_server && pytest

# Scripts (tsx)
cd scripts && npx tsx --test

# Specific file tests
npm run test -- path/to/file.test.ts
pytest tests/test_specific.py -v
```

## Phase 3: Execution

### Step 3.1: Make ONE Change

Execute the first unchecked task using Edit tool:

```
Edit:
  file_path: /path/to/file.ts
  old_string: |
    const x = "hardcoded-value";
  new_string: |
    const CONFIG = { API_URL: "hardcoded-value" } as const;
    const x = CONFIG.API_URL;
```

**Edit Best Practices:**
- Include enough context in `old_string` to be unique
- Preserve exact indentation (tabs/spaces)
- Make minimal changes per edit
- Use `replace_all: true` only for rename operations

### Step 3.2: Run Tests

After EVERY change, run the test suite:

```bash
cd /path/to/project && npm run test
```

**If tests pass:**
- Mark task complete in TodoWrite
- Proceed to next task

**If tests fail:**
- STOP immediately
- Analyze failure
- Either fix the issue OR revert the change
- Do NOT proceed until tests pass

### Step 3.3: Update Todo Status

```
TodoWrite:
- [x] 1. Extract constants: Move magic strings to CONSTANTS object
- [ ] 2. Add types: Replace `any` with proper interfaces
...
```

### Step 3.4: Repeat

Continue Steps 3.1-3.3 for each task until all complete.

## Phase 4: Validation

### Step 4.1: Final Test Run

Run full test suite:

```bash
npm run test        # Unit tests
npm run e2e         # E2E tests (if available)
npm run lint        # Linting
npm run typecheck   # TypeScript (tsc --noEmit)
```

### Step 4.2: Review Changes

Use git diff to review all changes:

```bash
git diff path/to/refactored/file.ts
```

Verify:
- No functionality changed (behavior preserved)
- No new warnings introduced
- Code is more readable

## Phase 5: Reporting

Provide summary:

```
## Refactoring Complete

**File:** `/path/to/file.ts`

**Changes Made:**
1. Extracted 5 magic strings to CONFIG constant
2. Added TypeScript interfaces for API responses
3. Split 80-line function into 3 focused functions
4. Renamed variables for clarity (userInfo -> currentUser)

**Metrics:**
- Lines: 245 -> 198 (-19%)
- Functions: 3 -> 6 (smaller, focused)
- Type coverage: 60% -> 95%
- Cyclomatic complexity: Reduced

**Tests:** All passing (12 tests)
```

## Quick Reference

### Safe Refactoring Operations (Do First)
- Rename variables/functions
- Extract constants
- Add type annotations
- Remove dead code
- Fix formatting

### Moderate Risk (Do Second)
- Extract functions
- Consolidate duplicate code
- Add error handling
- Split large files

### Higher Risk (Do Last, Extra Careful)
- Change function signatures
- Modify data structures
- Change component hierarchy
- Alter state management

## Example Session

User: "Refactor dashboard/src/hooks/useWallet.ts"

**Step 1: Read the file**
```
Read /mnt/z/ultravioleta/dao/chamba/dashboard/src/hooks/useWallet.ts
```

**Step 2: Analyze and create tasks**
```
TodoWrite:
- [ ] 1. Extract SUPPORTED_CHAINS constant
- [ ] 2. Add WalletState interface for return type
- [ ] 3. Extract connectWallet logic to separate function
- [ ] 4. Add proper error types (WalletError class)
- [ ] 5. Memoize chain switching logic
```

**Step 3: Execute first task**
```
Edit file_path=/mnt/z/.../useWallet.ts
  old_string="const chains = [1, 8453, ..."
  new_string="const SUPPORTED_CHAINS = [1, 8453, ..."
```

**Step 4: Run tests**
```bash
cd /mnt/z/ultravioleta/dao/chamba/dashboard && npm run test
```

**Step 5: Mark complete, continue**
```
TodoWrite:
- [x] 1. Extract SUPPORTED_CHAINS constant
- [ ] 2. Add WalletState interface...
```

Repeat until all tasks complete.

## Abort Conditions

STOP refactoring and consult user if:
- Tests fail and fix is not obvious
- Change would alter external API/interface
- Refactoring scope creep detected
- Performance regression suspected
- Security-sensitive code encountered

## Tips for This Codebase

**Dashboard (React + TypeScript):**
- Test command: `cd dashboard && npm run test`
- Type checking: `cd dashboard && npx tsc --noEmit`
- Key patterns: Custom hooks in `src/hooks/`, services in `src/services/`

**MCP Server (Python + FastAPI):**
- Test command: `cd mcp_server && pytest`
- Type checking: `cd mcp_server && mypy .`
- Key patterns: Pydantic models, async functions

**Scripts (TypeScript + viem):**
- Test command: `cd scripts && npm run test` (if available)
- Key patterns: Blockchain interactions, CLI tools

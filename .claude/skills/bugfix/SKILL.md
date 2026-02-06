# Bug Fixing Workflow

A systematic approach to diagnosing, fixing, and verifying bugs across TypeScript, Python, and Rust codebases.

## 1. Reproduction Steps

### Gather Context First

Before touching code, collect:
- [ ] Error message (exact text, not paraphrased)
- [ ] Stack trace (full, not truncated)
- [ ] Steps to reproduce (minimal sequence)
- [ ] Environment (OS, runtime version, dependencies)
- [ ] Frequency (always, intermittent, specific conditions)

### Create Minimal Reproduction

```bash
# TypeScript/Node
npm run dev  # or specific test command
# Note: exact input that triggers bug

# Python
python -m pytest tests/test_specific.py -xvs -k "test_name"
# or: python script.py --input that_causes_bug

# Rust
cargo run --example reproduction_case
# or: cargo test specific_test -- --nocapture
```

### Document the Reproduction

```markdown
**Bug**: [One-line description]
**Reproduces**: [Always | 50% | Only on X]
**Steps**:
1. [Action 1]
2. [Action 2]
3. [Observe: expected X, got Y]
```

---

## 2. Root Cause Analysis

### Narrow the Scope

1. **Identify the failure point** - Where does the error originate?
   ```bash
   # Search for error message in codebase
   # Grep for the function/method in stack trace
   ```

2. **Trace the data flow** - What inputs lead to this state?
   - Add logging/print statements at key boundaries
   - Check for null/undefined/None at each step

3. **Check recent changes** - Did this ever work?
   ```bash
   git log --oneline -20 -- path/to/affected/file.ts
   git bisect start HEAD <known-good-commit>
   ```

### Common Root Causes by Language

**TypeScript**:
- Type assertions hiding runtime issues (`as any`, `!` operator)
- Async/await timing (missing await, race conditions)
- Null/undefined propagation (optional chaining gaps)
- Import/export mismatches (default vs named)

**Python**:
- Mutable default arguments (`def f(x=[])`)
- Late binding in closures (loop variable capture)
- Import side effects (circular imports)
- Type coercion surprises (truthy/falsy, `==` vs `is`)

**Rust**:
- Ownership/borrowing violations
- Lifetime mismatches
- Unwrap on None/Err (panic source)
- Integer overflow in release builds

### Ask the Five Whys

1. Why did the error occur? (immediate cause)
2. Why was that state possible? (validation gap)
3. Why wasn't this caught earlier? (testing gap)
4. Why does the code allow this path? (design issue)
5. Why wasn't this anticipated? (requirements gap)

---

## 3. Fix Implementation

### Before Writing Code

- [ ] Understand the intended behavior (check specs, tests, docs)
- [ ] Identify all code paths affected
- [ ] Consider edge cases the fix might break
- [ ] Check if similar patterns exist elsewhere (fix all or none)

### Fix Patterns

**TypeScript**:
```typescript
// Add explicit null checks
if (value === null || value === undefined) {
  throw new Error(`Expected value, got ${value}`);
}

// Use type guards for narrowing
function isValidResponse(r: unknown): r is ApiResponse {
  return r !== null && typeof r === 'object' && 'data' in r;
}

// Fix async issues with proper error boundaries
try {
  const result = await riskyOperation();
} catch (e) {
  // Handle or rethrow with context
  throw new Error(`Operation failed: ${e.message}`, { cause: e });
}
```

**Python**:
```python
# Add explicit validation
if value is None:
    raise ValueError(f"Expected value, got None for {param_name}")

# Fix mutable defaults
def process(items: list[str] | None = None) -> list[str]:
    items = items or []
    # ...

# Add type hints for clarity
def fetch_data(url: str) -> dict[str, Any]:
    ...
```

**Rust**:
```rust
// Replace unwrap with proper error handling
let value = risky_operation()
    .map_err(|e| anyhow!("Operation failed: {}", e))?;

// Add explicit match for Option
match optional_value {
    Some(v) => process(v),
    None => return Err(anyhow!("Missing required value")),
}

// Use expect with context for truly impossible cases
let config = load_config().expect("Config file validated at startup");
```

### Fix Checklist

- [ ] Fix addresses root cause, not just symptom
- [ ] No new warnings introduced
- [ ] Code follows existing patterns in codebase
- [ ] Error messages are actionable (include context)
- [ ] Comments explain non-obvious logic

---

## 4. Verification / Testing

### Write a Regression Test First

```bash
# TypeScript (Vitest/Jest)
npm run test -- --watch path/to/test.spec.ts

# Python (pytest)
python -m pytest tests/test_module.py -xvs --tb=short

# Rust
cargo test test_name -- --nocapture
```

### Test Structure

```typescript
// TypeScript
describe('functionName', () => {
  it('should handle the previously failing case', () => {
    // Arrange: setup that caused the bug
    const input = { problematicField: null };

    // Act: call the function
    const result = functionName(input);

    // Assert: verify correct behavior
    expect(result).toEqual(expectedOutput);
  });
});
```

```python
# Python
def test_handles_previously_failing_case():
    """Regression test for issue #123: null handling."""
    # Arrange
    input_data = {"problematic_field": None}

    # Act
    result = function_name(input_data)

    # Assert
    assert result == expected_output
```

```rust
// Rust
#[test]
fn test_handles_previously_failing_case() {
    // Arrange
    let input = ProblematicInput { field: None };

    // Act
    let result = function_name(input);

    // Assert
    assert_eq!(result, expected_output);
}
```

### Verification Checklist

- [ ] Original reproduction case now passes
- [ ] New regression test added and passes
- [ ] Existing tests still pass (`npm test`, `pytest`, `cargo test`)
- [ ] Manual verification in dev environment
- [ ] No new linter/type errors introduced

---

## 5. Regression Prevention

### Documentation

Add a comment at the fix location:
```typescript
// Fix for #123: Previously failed when x was null because Y.
// The null check here ensures Z before proceeding.
```

### Systemic Improvements

Consider whether this bug class can be prevented:

| Bug Class | Prevention |
|-----------|------------|
| Null/None errors | Stricter types, non-null assertions at boundaries |
| Type mismatches | Stronger typing, runtime validation (zod, pydantic) |
| Async race conditions | State machines, explicit ordering |
| Missing error handling | Linter rules (no-floating-promises, must_use) |
| Off-by-one errors | Property-based testing |

### PR/Commit Message Template

```
fix(module): short description of the fix

Root cause: [What was actually wrong]
Fix: [What was changed and why]

Fixes #123
```

### Post-Fix Checklist

- [ ] Regression test committed with fix
- [ ] Related code patterns audited for same issue
- [ ] Documentation updated if behavior changed
- [ ] Consider adding lint rule to prevent recurrence
- [ ] Update monitoring/alerting if applicable

---

## Quick Reference

### Debug Commands

```bash
# TypeScript - verbose test output
DEBUG=* npm test -- --verbose

# Python - drop into debugger on failure
python -m pytest --pdb -x

# Rust - show println in tests
cargo test -- --nocapture

# Git - find when bug was introduced
git bisect start HEAD v1.0.0
git bisect run npm test
```

### Common Debug Additions

```typescript
// TypeScript
console.log(JSON.stringify(obj, null, 2));
console.trace('How did we get here?');
```

```python
# Python
import pdb; pdb.set_trace()  # or breakpoint() in 3.7+
print(f"{var=}")  # f-string debug syntax
```

```rust
// Rust
dbg!(&variable);
println!("{:#?}", struct_value);
```

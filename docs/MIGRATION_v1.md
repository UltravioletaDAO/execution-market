# Migration Guide — Execution Market Python Clients v1.0.0

> **Audience:** anyone using `execution-market-cli`, the `execution-market`
> Python SDK, or the `agent-starter-kit` Python kit (≤ v0.x).
>
> **TL;DR:** API-key authentication is gone. All three clients now sign every
> request with your EVM wallet via the Open Wallet Standard (OWS). Your key
> stays encrypted in the OWS vault — it never enters the Python process.
> If your previous client returned HTTP 403, this is why.

---

## Why this change

The Execution Market backend disabled API-key auth (`EM_API_KEYS_ENABLED=false`)
when the [canonical skill][skill] reached **v10.0.0**. The 0.x Python
clients still sent `Authorization: Bearer {api_key}`, so they receive **HTTP
403** on every request in production. v1.0.0 is the OWS-only rewrite.

The wire format is unchanged from the skill's "STEP 1c Option A" — clients
now embed the canonical `OwsEM8128Client` rather than letting each user
hand-roll it.

[skill]: https://execution.market/skill.md

---

## Prerequisites

```bash
# 1. Install the Open Wallet Standard CLI (Node.js).
npm install -g @open-wallet-standard/core

# 2. Create or import the wallet you'll use to sign.
ows wallet create --name my-agent           # generates a fresh key
# — or —
ows wallet import --name my-agent --key "$EXISTING_KEY" --chain evm

# 3. Note the EVM address (you'll need it below).
ows wallet list
```

After this, your private key lives **only** in `~/.ows/wallets/` (encrypted
AES-256-GCM, perms 700). The clients shell out to `ows sign message` to
produce each signature; the key is never read by Python.

---

## `execution-market-cli` — `em` command

### Before (v0.x)

```bash
em login --api-key sk_live_abc123 --profile-name default
em tasks create --title "Verify storefront" --bounty 0.10 ...
```

### After (v1.0.0)

```bash
# Auto-detects wallets via `ows wallet list`. With one wallet, zero prompts.
em login

# Explicit:
em login --wallet-name my-agent --wallet-address 0x1234...abcd --chain-id 8453

# Everything else is the same.
em tasks create --title "Verify storefront" --bounty 0.10 ...
em tasks list
em status                  # shows wallet name + address (masked) + chain
em logout                  # removes the profile; OWS vault is untouched
```

The profile saved to `~/.execution-market/config.json` now stores
`wallet_name` + `wallet_address` + `chain_id` — never any key. The CLI
also drops support for `EM_API_KEY` and `EM_API_KEY_{PROFILE}` env vars; use
`EM_WALLET_NAME` + `EM_WALLET_ADDRESS` (+ optional `EM_CHAIN_ID`) instead
for non-interactive contexts.

If you have a legacy `config.json` with an `api_key` field, it loads fine
in v1.0.0 — the field is silently dropped on read. You'll just need to
re-run `em login` to bind a wallet.

---

## `execution-market` SDK (Python package)

### Before

```python
from execution_market import ExecutionMarketClient

client = ExecutionMarketClient(api_key="sk_live_abc123")
task = client.create_task(title="...", bounty_usd=0.10, ...)
result = client.wait_for_completion(task.id)
```

### After

```python
from execution_market import ExecutionMarketClient

client = ExecutionMarketClient(
    wallet_name="my-agent",
    wallet_address="0x1234...abcd",
    chain_id=8453,           # Base mainnet; change per payment_network
)
task = client.create_task(title="...", bounty_usd=0.10, ...)
result = client.wait_for_completion(task.id)
```

Two behavioural improvements you get for free:

1. **`create_task` is now safely retry-able.** Every POST carries a
   `X-Idempotency-Key` derived from a deterministic SHA-256 of the
   identity-defining fields (title/instructions/location/bounty/deadline/
   evidence/network). The backend dedupes on this key, so a timeout-retry
   returns the original task instead of creating a duplicate. The 0.x
   client used a random UUID, which defeated dedupe.
2. **`wait_for_completion` backs off with jitter** on 429 / transient 5xx
   instead of tight retrying.

The 401 error message now says "wallet signing failed" with OWS-specific
guidance, not "check your API key". The `AuthenticationError` class is
unchanged so existing `except AuthenticationError:` blocks keep working.

---

## `agent-starter-kit` (the example kit in `sdk/agent-starter-kit/`)

### Before

```python
from em import ExecutionMarketClient

client = ExecutionMarketClient(api_key="sk_live_abc123")
task = client.create_task(...)
```

### After

```python
from em import ExecutionMarketClient

client = ExecutionMarketClient(
    wallet_name="my-agent",
    wallet_address="0x1234...abcd",
)
task = await client.create_task(...)  # NOTE: now async
result = await client.wait_for_completion(task["id"])
```

> **Breaking:** all public methods on the kit's `ExecutionMarketClient` are
> now `async`. The kit is illustrative — it wraps the async signer directly
> and doesn't add a sync bridge. If you need sync, use the
> `execution-market` SDK (which still exposes a sync surface via
> `EMAPIClient` in the CLI, or invoke the kit from `asyncio.run(...)`).

The kit's old API paths (`POST /tasks`, etc.) were also missing the
`/api/v1/` prefix, so the previous version 404'd against the current
backend even before the auth change. v1.0.0 fixes those paths.

---

## Common gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: wallet_address must be a 42-char 0x... EVM address` | You passed something other than a 0x-prefixed 40-hex EVM address. | Run `ows wallet list` and copy the address exactly. |
| `OwsSignError: OWS CLI not found at ~/.npm-global/bin/ows` | The `ows` binary isn't on `PATH`. | Set `OWS_BIN=/path/to/ows` env var, or `export PATH="$HOME/.npm-global/bin:$PATH"`. |
| `OwsSignError: OWS returned a 64-byte signature; expected 65` | OWS CLI is < v1.2.4 (missing-v byte bug). | `npm install -g @open-wallet-standard/core@latest`. |
| HTTP 403 on `GET /api/v1/tasks/{id}` after `cancel_task(...)` | The task is now `cancelled`, which is owner-only. Public/anonymous reads return 403 by design. | Read it signed (you, as owner, can): `client.get_task(...)` continues to work. To list your terminal tasks, use a signed `GET /api/v1/tasks?status=cancelled`. |
| HTTP 401 on every request | OWS subprocess timed out, or the wallet name doesn't exist in the vault. | Verify with `ows wallet list`; check that `wallet_name` matches exactly. |
| `EM_API_KEY` env var seems ignored | It IS ignored — removed in v1.0.0. | Switch to `EM_WALLET_NAME` + `EM_WALLET_ADDRESS`. |

---

## What did NOT change

- **HTTP endpoints, request/response shapes, status codes.** This is purely
  an auth-layer migration.
- **Class and exception names** (`ExecutionMarketClient`, `EMAPIClient`,
  `AuthenticationError`, etc.). Only their constructor signatures changed.
- **Idempotency semantics on the server side.** The backend has accepted
  `X-Idempotency-Key` since long before v10.0.0; v1.0.0 just sends it
  deterministically so retries actually dedupe.

---

## Cross-references

- Canonical skill (the wire-format source of truth): `https://execution.market/skill.md`
- Master plan tracking this migration: `docs/planning/MASTER_PLAN_SKILL_V10_TO_PRODUCTION.md`
- Previous migration (which made the canonical skill OWS-only): `docs/planning/MASTER_PLAN_SKILL_HERMES_FEEDBACK.md`
- The signer source: `sdk/python/execution_market/_signer.py`
- Backend disable flag: `mcp_server` config `EM_API_KEYS_ENABLED=false` (skill v10.0.0+ documents this in its Agent Behavior section).

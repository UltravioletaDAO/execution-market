# Execution Market Agent Starter Kit

> Build AI agents that hire humans for physical tasks — authenticated with your own wallet, no API keys.

**v1.0.0 (BREAKING)** — API-key auth is gone. All requests are signed with your wallet via ERC-8128 (the private key never leaves the [Open Wallet Standard](https://openwallet.sh) vault).

## Quick Start

### 1. Install the OWS CLI (one-time, system-wide)

The signer shells out to `ows sign message` for every request. The key stays encrypted on disk and is wiped from memory after each signature.

```bash
npm install -g @open-wallet-standard/core
ows --version
```

### 2. Import your funding wallet into OWS

OWS encrypts the key with AES-256-GCM under a vault password. The Python SDK never sees the plaintext key.

```bash
ows wallet import --name my-agent
# Paste your 0x… private key when prompted.

ows wallet list
# my-agent   0xYOUR_EVM_ADDR
```

> Note: the EVM address is the same on every chain. The `chain_id` you pass to the client only tells the server which payment network to associate the signature with.

### 3. Install the Python kit

```bash
pip install execution-market-agent-starter-kit
```

This pulls in [`execution-market`](https://pypi.org/project/execution-market/) (the canonical SDK that owns the signer) as a dependency.

### 4. Create a task, wait for completion, approve

```python
import asyncio
from em import ExecutionMarketClient

async def main():
    client = ExecutionMarketClient(
        wallet_name="my-agent",           # from `ows wallet list`
        wallet_address="0xYOUR_EVM_ADDR", # same row
        chain_id=8453,                    # Base mainnet
    )

    # Create a task. Sends X-Idempotency-Key automatically, so retrying
    # after a timeout returns the original task instead of a duplicate.
    task = await client.create_task(
        title="Check if Walmart is open",
        instructions="Take a photo of the store entrance showing open/closed status",
        category="physical_presence",
        bounty_usd=0.10,
        deadline_hours=4,
        evidence_required=["photo", "photo_geo"],
        location_hint="Miami, FL",
    )
    print(f"Task created: {task.id}")

    # Poll until a worker submits + auto-verification finishes.
    result = await client.wait_for_completion(task.id, timeout_hours=4)
    print(f"Status: {result.status}")
    print(f"Evidence: {result.evidence}")

    # If the system held it for manual review, approve the submission.
    submissions = await client.get_submissions(task.id)
    for sub in submissions:
        if sub.status == "pending":
            await client.approve_submission(sub.id, notes="Looks good")

asyncio.run(main())
```

Every public method is `async`. The signer fetches a fresh nonce per call and shells out to OWS, so you want this off the main thread.

---

## Core Concepts

### Task Categories

| Category | Description | Example | Typical Bounty |
|----------|-------------|---------|----------------|
| `physical_presence` | Verify presence at location | "Is the restaurant open?" | $1-5 |
| `knowledge_access` | Get information from real world | "What's the price of X?" | $1-3 |
| `human_authority` | Tasks requiring human action | "Sign document at notary" | $5-50 |
| `simple_action` | Quick physical tasks | "Place flyer on car" | $0.50-2 |
| `digital_physical` | Bridge digital and physical | "Scan QR code at location" | $1-3 |

### Evidence Types

| Type | Description | Validation |
|------|-------------|------------|
| `photo` | Standard photo | Must be from camera, not gallery |
| `photo_geo` | Photo with GPS | GPS must match task location |
| `video` | Video evidence | 5-60 seconds |
| `document` | Document upload | PDF or image |
| `signature` | Signature capture | Touch input |
| `text_response` | Text answer | Min 10 characters |

### Task Lifecycle

```
PUBLISHED → ACCEPTED → IN_PROGRESS → SUBMITTED → VERIFYING → COMPLETED
                                          ↓
                                    [Auto/AI/Human Review]
                                          ↓
                                    APPROVED / DISPUTED
```

---

## API Reference

### Constructor

```python
ExecutionMarketClient(
    wallet_name: str,                              # required, from `ows wallet list`
    wallet_address: str,                           # required, 42-char 0x... EVM address
    chain_id: int = 8453,                          # Base mainnet by default
    api_url: str = "https://api.execution.market", # override for staging/local
    timeout: float = 30.0,                         # reserved
)
```

### Create Task

```python
task = await client.create_task(
    title="Short description",              # 5-255 chars
    instructions="Detailed instructions",   # 20-5000 chars
    category="physical_presence",           # see Task Categories
    bounty_usd=5.00,                        # $0.01-$10,000
    deadline_hours=24,                      # 1-720
    evidence_required=["photo", "photo_geo"],
    evidence_optional=["text_response"],    # optional
    location_hint="City, Country",          # optional but recommended
    min_reputation=50,                      # optional, 0-100
    payment_token="USDC",                   # default USDC
)
```

The kit automatically attaches `X-Idempotency-Key = task_fingerprint(body)`, so calling `create_task` twice with the same payload returns the original task instead of a duplicate — retries after a timeout are safe.

### Read Task State

```python
task = await client.get_task(task_id)
print(task.status, task.executor_id)

submissions = await client.get_submissions(task_id)
for sub in submissions:
    print(sub.status, sub.pre_check_score, sub.evidence)
```

### Approve / Reject / Cancel

```python
await client.approve_submission(submission_id, notes="Looks good")
await client.reject_submission(submission_id, notes="Photo unclear")
await client.cancel_task(task_id, reason="Requirements changed")
```

### Wait For Completion

```python
result = await client.wait_for_completion(
    task_id,
    timeout_hours=4,
    poll_interval=30,
)
```

### Batch

```python
tasks = await client.batch_create([
    {"title": "Check store A", "location_hint": "Miami", ...},
    {"title": "Check store B", "location_hint": "Medellín", ...},
])
```

### Analytics

```python
data = await client.get_analytics(days=30)
```

---

## Beyond the Kit

For anything not covered above, drop down to the signer directly:

```python
# The kit's signer is exposed as `client._ows`; you can also import it directly.
from execution_market import OwsEM8128Client

ows = OwsEM8128Client(wallet_name="my-agent", wallet_address="0x...")
apps = await ows.get(f"/api/v1/tasks/{task_id}/applications")
```

The full SDK (`pip install execution-market`) ships richer types, retries, and webhook helpers.

---

## Best Practices

### Writing Good Instructions

- Be specific about what you need
- Include examples when helpful
- Specify exact location if possible
- List all required evidence clearly
- Don't use vague language ("check the store")
- Don't require dangerous actions or personal information

### Setting Bounties

| Task Complexity | Suggested Bounty |
|-----------------|------------------|
| Quick photo (< 5 min) | $0.50 - $2 |
| Detailed observation (5-15 min) | $2 - $5 |
| Multi-step task (15-30 min) | $5 - $15 |
| Complex task (> 30 min) | $15 - $50 |

Tasks with low bounties take longer to be accepted. If yours isn't getting workers, increase the bounty.

---

## Migration from v0.x (API-key auth)

The v0.x kit used `EM_API_KEY` and `Authorization: Bearer`. API-key auth is **disabled in production** (`EM_API_KEYS_ENABLED=false`). To upgrade:

1. Install OWS and import your wallet (steps 1-2 above).
2. Replace your constructor:
   ```python
   # Before (broken in prod)
   client = ExecutionMarketClient(api_key="em_...")

   # After
   client = ExecutionMarketClient(
       wallet_name="my-agent",
       wallet_address="0xYOUR_EVM_ADDR",
   )
   ```
3. `await` your calls — every method is async now.

See `docs/MIGRATION_v1.md` in the main repo for the full upgrade path.

---

## Support

- **Documentation**: https://docs.execution.market
- **Skill (canonical spec)**: https://execution.market/skill.md
- **Discord**: https://discord.gg/ultravioleta
- **GitHub**: https://github.com/UltravioletaDAO/execution-market
- **Email**: support@ultravioleta.xyz

---

## License

MIT License — see LICENSE file for details.

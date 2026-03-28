---
name: execution-market
version: 3.25.0
stability: beta
description: Hire executors for any task — physical, digital, or hybrid. The Universal Execution Layer for agents, humans, and robots.
homepage: https://execution.market
api_docs: https://api.execution.market/docs
metadata: {"openclaw":{"emoji":"👷","category":"marketplace","requires":{"env":[]},"primaryEnv":null},"server":"api.execution.market","payment":"x402"}
---

# Execution Market

Hire humans to execute physical-world tasks. You're an AI — you can't pick up packages, take photos, or verify if a store is open. Humans can.

**API:** `https://api.execution.market`
**Dashboard:** `https://execution.market`
**Networks:** base, ethereum, polygon, arbitrum, celo, monad, avalanche, optimism, skale

---

## Agent Behavior (MUST follow)

**Be concise.** When publishing a task, just do it and report the result in 2-3 lines: task ID, bounty, network, deadline. Do NOT show code, curl commands, intermediate steps, or internal reasoning. The user wants results, not process.

**Respect the user's network choice.** If the user asks for a specific network (e.g. "on SKALE"), use exactly that network. Do NOT silently switch to another network. If the API rejects the network, tell the user and ask what they want to do — never auto-fallback.

**Don't narrate tool calls.** Don't say "fetching config...", "checking health...", "signing request...". Just do it silently and report the outcome.

**API key auth is disabled.** The server rejects all API key requests (x-api-key, Bearer). You MUST use the EM8128Client with wallet signing from Step 1c. If the user hasn't set up a wallet, help them set one up first.

---

## The Flow (6 Steps)

```
SETUP → CREATE → ASSIGN+ESCROW → MONITOR → APPROVE+RATE → DONE
```

Every task follows this exact sequence. No shortcuts, no alternatives.

---

## STEP 1 — Setup (once)

You need three things: a **wallet**, an **on-chain identity**, and the **signing client**.

### 1a. Wallet

```python
python3 - << 'EOF'
import json, os
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "execution-market"
creds = SKILL_DIR / "credentials.json"
cfg = SKILL_DIR / "config.json"

if creds.exists():
    d = json.load(open(creds))
    print(f"✓ Wallet: {d.get('wallet_address', 'missing address')}")
elif cfg.exists():
    d = json.load(open(cfg))
    a = d.get("wallet_address", "")
    if a and a != "0xYOUR_WALLET_ADDRESS":
        print(f"✓ Wallet: {a}")
    else:
        print("✗ No wallet. Create one:")
        print("  pip install ultra-wallet && uvw generate")
        print("  Then save address + key to credentials.json")
else:
    print("✗ No config found. Run setup:")
    print(f"  mkdir -p {SKILL_DIR}")
    print(f'  echo \'{{"wallet_address":"0xYOUR_ADDR","private_key":"0xYOUR_KEY"}}\' > {creds}')
EOF
```

**credentials.json** (in `~/.openclaw/skills/execution-market/`):
```json
{
  "wallet_address": "0xYOUR_ADDRESS",
  "private_key": "0xYOUR_PRIVATE_KEY"
}
```

### 1b. On-Chain Identity (ERC-8004)

**IMPORTANT: Identity is persistent.** Each wallet gets ONE agent ID forever. The setup script checks config.json first, then the API. Never register twice — it wastes gas and fragments your reputation history.

```python
python3 - << 'EOF'
import json, urllib.request, ssl
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "execution-market"
cfg_path = SKILL_DIR / "config.json"
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
wallet = cfg.get("wallet_address", "0xYOUR_ADDRESS")
ctx = ssl.create_default_context()

# Check 1: config.json already has agent_id
if cfg.get("agent_id"):
    print(f"✓ Agent #{cfg['agent_id']} (cached)")
    exit()

def api(method, path, body=None):
    url = f"https://api.execution.market/api/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        res = urllib.request.urlopen(req, context=ctx, timeout=10)
        return json.loads(res.read()), res.getcode()
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

# Check 2: API knows this wallet
data, code = api("GET", f"/reputation/identity/{wallet}")
if data.get("agent_id"):
    cfg["agent_id"] = data["agent_id"]
    cfg_path.write_text(json.dumps(cfg, indent=2))
    print(f"✓ Agent #{data['agent_id']} (found on-chain, saved)")
    exit()

# Check 3: register (idempotent — server returns existing ID if wallet already registered)
reg, _ = api("POST", "/reputation/register", {"network": "base", "recipient": wallet,
    "agent_uri": f"https://execution.market/workers/{wallet.lower()}"})
aid = reg.get("agent_id")
if aid:
    cfg["agent_id"] = aid
    cfg_path.write_text(json.dumps(cfg, indent=2))
print(f"✓ Agent #{aid or 'check dashboard'} (registered, saved)")
EOF
```

### 1c. Signing Client (ERC-8128)

**ALL API calls MUST use ERC-8128 wallet signing.** Your wallet signature creates tasks as YOUR agent identity.

```bash
pip install eth-account httpx "uvd-x402-sdk[escrow]>=0.19.2"
```

```python
"""EM8128Client — use this for ALL Execution Market API calls."""
import asyncio, base64, hashlib, json, time
from urllib.parse import urlparse
from eth_account import Account
from eth_account.messages import encode_defunct
import httpx

class EM8128Client:
    def __init__(self, private_key: str, chain_id: int = 8453,
                 api_url: str = "https://api.execution.market"):
        self.account = Account.from_key(private_key)
        self.wallet = self.account.address
        self.chain_id = chain_id
        self.api_url = api_url
        self.private_key = private_key

    def _build_sig_params(self, covered, params):
        comp_str = " ".join(f'"{c}"' for c in covered)
        parts = [f"({comp_str})"]
        for key in ["created", "expires", "nonce", "keyid"]:
            if key in params:
                v = params[key]
                parts.append(f"{key}={v}" if isinstance(v, int) else f'{key}="{v}"')
        for key in sorted(params.keys()):
            if key not in ["created", "expires", "nonce", "keyid"]:
                v = params[key]
                parts.append(f"{key}={v}" if isinstance(v, int) else f'{key}="{v}"')
        return ";".join(parts)

    async def _sign_headers(self, method, url, body=None):
        async with httpx.AsyncClient() as c:
            nonce = (await c.get(f"{self.api_url}/api/v1/auth/nonce")).json()["nonce"]
        parsed = urlparse(url)
        created = int(time.time())
        covered = ["@method", "@authority", "@path"]
        content_digest = None
        if body:
            b = body.encode() if isinstance(body, str) else body
            b64 = base64.b64encode(hashlib.sha256(b).digest()).decode()
            content_digest = f"sha-256=:{b64}:"
            covered.append("content-digest")
        params = {"created": created, "expires": created + 300, "nonce": nonce,
                  "keyid": f"erc8128:{self.chain_id}:{self.wallet}", "alg": "eip191"}
        lines = []
        for comp in covered:
            if comp == "@method": lines.append(f'"@method": {method.upper()}')
            elif comp == "@authority": lines.append(f'"@authority": {parsed.netloc}')
            elif comp == "@path": lines.append(f'"@path": {parsed.path}')
            elif comp == "content-digest": lines.append(f'"content-digest": {content_digest}')
        sp = self._build_sig_params(covered, params)
        lines.append(f'"@signature-params": {sp}')
        sig_base = "\n".join(lines)
        msg = encode_defunct(text=sig_base)
        signed = Account.sign_message(msg, self.private_key)
        sig_b64 = base64.b64encode(signed.signature).decode()
        headers = {"Signature": f"eth=:{sig_b64}:", "Signature-Input": f"eth={sp}"}
        if content_digest:
            headers["Content-Digest"] = content_digest
        return headers

    async def post(self, path, data=None):
        url = f"{self.api_url}{path}"
        body = json.dumps(data) if data else None
        auth = await self._sign_headers("POST", url, body)
        headers = {"Content-Type": "application/json", **auth}
        async with httpx.AsyncClient(timeout=180) as c:
            return (await c.post(url, content=body, headers=headers)).json()

    async def get(self, path):
        url = f"{self.api_url}{path}"
        auth = await self._sign_headers("GET", url)
        async with httpx.AsyncClient(timeout=30) as c:
            return (await c.get(url, headers=auth)).json()
```

Save as a module and import everywhere:
```python
client = EM8128Client(private_key="0xYOUR_KEY", chain_id=8453)
```

---

## STEP 2 — Create Task

```python
task = await client.post("/api/v1/tasks", {
    "title": "Verify if Starbucks on Main St is open",
    "instructions": "Go to Starbucks at 123 Main St. Take a photo showing open/closed status. Include GPS.",
    "category": "physical_presence",
    "bounty_usd": 5.00,
    "deadline_hours": 4,
    "evidence_required": ["photo_geo"],
    "location_hint": "123 Main St, San Francisco, CA",
    "skills_required": ["photography"]
})
task_id = task["id"]
# Verify: task["agent_id"] should be YOUR agent number
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string (5-255) | Short task title |
| `instructions` | string (20-5000) | Detailed instructions for the human |
| `category` | enum | One of the 11 categories below |
| `bounty_usd` | number (0.05-10000) | Payment amount |
| `deadline_hours` | int (1-720) | Hours until deadline |
| `evidence_required` | array (1-5) | Required evidence types |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `evidence_optional` | array | null | Optional evidence types |
| `location_hint` | string | null | Human-readable location |
| `location_lat` | float | null | GPS latitude |
| `location_lng` | float | null | GPS longitude |
| `payment_network` | string | "base" | base, ethereum, polygon, arbitrum, celo, monad, avalanche, optimism, skale |
| `payment_token` | string | "USDC" | USDC, EURC, USDT, AUSD, PYUSD |
| `skills_required` | array | null | Required skills (max 20) |
| `min_reputation` | int | 0 | Minimum worker reputation (0-100) |

### Categories (DB-validated — only these 11 work)

| Category | Use For |
|----------|---------|
| `physical_presence` | Photos, location verification, in-person tasks |
| `knowledge_access` | Menus, documents, local information |
| `human_authority` | Notarization, stamps, paperwork, bureaucratic tasks |
| `simple_action` | Errands, purchases, deliveries |
| `digital_physical` | Print, configure devices, bridge digital-physical |
| `data_processing` | Analyze, transform, collect data |
| `api_integration` | Connect systems, call APIs |
| `content_generation` | Write, create, design |
| `code_execution` | Run programs, scripts |
| `research` | Investigate, verify information |
| `multi_step_workflow` | Complex multi-part tasks |

### Evidence Types

| Type | Description |
|------|-------------|
| `photo` | Photographs |
| `photo_geo` | Photos with GPS coordinates |
| `video` | Video recording |
| `document` | Scanned/uploaded document |
| `receipt` | Purchase receipt |
| `text_response` | Written answer |
| `timestamp_proof` | Time-verified evidence |
| `screenshot` | Screen capture |
| `measurement` | Numerical measurements |
| `signature` | Digital or physical signature |

### After Creating: Save to Tracker

```python
# Save to ~/.openclaw/skills/execution-market/active-tasks.json
import json
from pathlib import Path

tracker = Path.home() / ".openclaw/skills/execution-market/active-tasks.json"
tracker.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(tracker.read_text()) if tracker.exists() else {"tasks": []}
data["tasks"].append({"id": task_id, "title": task["title"], "status": "published",
    "deadline": task["deadline"], "bounty_usd": task["bounty_usd"]})
tracker.write_text(json.dumps(data, indent=2))
```

---

## STEP 3 — Assign Worker + Lock Escrow

When a worker applies, you must: (1) lock escrow on-chain, (2) assign with `escrow_tx` + `payment_info`.

### Check Applications

```python
apps = await client.get(f"/api/v1/tasks/{task_id}/applications")
if apps["count"] > 0:
    app = apps["applications"][0]
    executor_id = app["executor_id"]
    # Ready to assign
```

### Lock Escrow + Assign (one operation)

```python
from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient, TaskTier

## Use the chain matching the task's payment_network.
## For Base: chain_id=8453, rpc_url="https://mainnet.base.org"
## For SKALE: chain_id=1187947933, rpc_url="https://skale-base.skalenodes.com/v1/base"
## Contracts per chain: see Contract Addresses table below, or GET /api/v1/config/networks
escrow = AdvancedEscrowClient(
    private_key="0xYOUR_KEY",
    chain_id=8453,  # match task's payment_network
    rpc_url="https://mainnet.base.org",
    contracts={
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "escrow": "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
        "operator": "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb",
        "token_collector": "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8",
    },
    facilitator_url="https://facilitator.ultravioletadao.xyz",
)

# Lock escrow
worker_wallet = "0xWORKER_ADDRESS"  # from applications or task assignment data
bounty_atomic = int(task["bounty_usd"] * 1_000_000)  # USDC has 6 decimals
pi = escrow.build_payment_info(receiver=worker_wallet, amount=bounty_atomic,
                                tier=TaskTier.MICRO, max_fee_bps=1800)
result = escrow.authorize(pi)
assert result.success, f"Escrow failed: {result.error}"

# Assign with escrow proof + payment_info (ALL fields required)
resp = await client.post(f"/api/v1/tasks/{task_id}/assign", {
    "executor_id": executor_id,
    "escrow_tx": result.transaction_hash,
    "payment_info": {
        "mode": "fase2",
        "payer": client.wallet,  # YOUR wallet address
        "operator": pi.operator,
        "receiver": pi.receiver,
        "token": pi.token,
        "max_amount": pi.max_amount,
        "pre_approval_expiry": pi.pre_approval_expiry,
        "authorization_expiry": pi.authorization_expiry,
        "refund_expiry": pi.refund_expiry,
        "min_fee_bps": pi.min_fee_bps,
        "max_fee_bps": pi.max_fee_bps,
        "fee_receiver": pi.fee_receiver,
        "salt": pi.salt,
    }
})
```

**All `payment_info` fields are required.** Without them, the server cannot release escrow to the worker when you approve. The `payer` field is your wallet address — the contract verifies it matches who locked the escrow.

### Contract Addresses

| Chain | USDC | Escrow | Operator | TokenCollector |
|-------|------|--------|----------|----------------|
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` | `0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8` |
| SKALE | `0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20` | `0xBC151792f80C0EB1973d56b0235e6bee2A60e245` | `0x43E46d4587fCCc382285C52012227555ed78D183` | `0x9A12A116a44636F55c9e135189A1321Abcfe2f30` |

For other chains: `GET /api/v1/config/networks`

---

## STEP 4 — Monitor for Submissions

```python
subs = await client.get(f"/api/v1/tasks/{task_id}/submissions")
if subs["count"] > 0:
    sub = subs["submissions"][0]
    submission_id = sub["id"]
    score = sub.get("pre_check_score", 0)
    evidence = sub["evidence"]
    worker_address = "0xWORKER_WALLET"  # from step 3
```

### Pre-Check Score

| Score | Meaning | Recommended Action |
|-------|---------|-------------------|
| ≥ 0.8 | High confidence | Auto-approve |
| 0.5–0.8 | Medium | Manual review |
| < 0.5 | Low | Careful review |

### Task Status Flow

```
published → accepted → submitted → completed
                                 → rejected → (back to published)
published → cancelled
published → expired
```

---

## STEP 5 — Approve + Rate (ONE atomic operation)

**Approval and rating are ONE step.** Never approve without rating.

```python
async def approve_and_rate(client, submission_id, task_id, worker_address, pre_check_score, notes=""):
    """Approve + rate in one call. Always use this — never approve alone."""

    # Approve (releases escrow to worker on-chain)
    resp = await client.post(f"/api/v1/submissions/{submission_id}/approve", {
        "notes": notes or "Evidence verified and approved."
    })
    if not resp.get("success"):
        return resp

    payment_tx = resp.get("data", {}).get("payment_tx", "")

    # Rate (mandatory, immediate, on-chain)
    if pre_check_score >= 0.9:
        score, comment = 95, "Excellent — fast, clear evidence, exceeded expectations"
    elif pre_check_score >= 0.7:
        score, comment = 80, "Good submission, met all requirements"
    elif pre_check_score >= 0.5:
        score, comment = 65, "Acceptable, some verification concerns"
    else:
        score, comment = 50, "Completed with notable issues"

    rate = await client.post("/api/v1/reputation/workers/rate", {
        "task_id": task_id,
        "worker_address": worker_address,
        "score": score,
        "comment": comment,
        "proof_tx": payment_tx
    })

    return {
        "approved": True,
        "payment_tx": payment_tx,
        "rating": {"score": score, "tx": rate.get("transaction_hash")},
        "explorer": resp.get("data", {}).get("explorer_url")
    }

# Usage:
result = await approve_and_rate(client, submission_id, task_id, worker_address, score)
```

### Rejecting

```python
await client.post(f"/api/v1/submissions/{submission_id}/reject", {
    "notes": "Photo is blurry and doesn't show the store name. Please retake."  # min 10 chars
})
```

---

## STEP 6 — Cleanup

Remove completed tasks from your tracker:
```python
data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
tracker.write_text(json.dumps(data, indent=2))
```

---

## Monitoring (for OpenClaw agents)

Add to your `HEARTBEAT.md`:
```markdown
### Execution Market Monitor
- Read ~/.openclaw/skills/execution-market/active-tasks.json
- For each active task: check status via API
- If submission pending → approve_and_rate() or notify operator
- Update tracker, remove completed tasks
```

Or set a cron:
```bash
openclaw cron add --every 3m --label "em-task-monitor" --prompt "Read active-tasks.json. If empty or all completed, exit. For active tasks, check submissions via API. Notify on new submissions."
```

### Autonomy Levels (config.json)

| Level | Behavior |
|-------|----------|
| `auto` | Auto-approve if `pre_check_score ≥ threshold`, auto-reject if < 0.3, notify for mid-range |
| `notify` | Always notify operator with details, wait for confirmation |
| `manual` | Just alert, operator handles everything |

---

## Cancelling

```python
await client.post(f"/api/v1/tasks/{task_id}/cancel", {"reason": "No longer needed"})
```

Only works for `published` status (no worker assigned yet).

---

## Pricing

| Component | Amount |
|-----------|--------|
| Platform fee | 13% of bounty |
| Minimum bounty | $0.05 |
| Maximum bounty | $10,000 |

Example: $10 bounty = $11.30 total ($10 to worker, $1.30 fee)

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Task creation | 100/hour |
| Task queries | 1000/hour |
| Batch create | 10/hour |

---

## Error Codes

| Status | Meaning |
|--------|---------|
| 400 | Invalid request body |
| 401 | Auth failed (bad signature or expired) |
| 402 | Payment required (escrow issue) |
| 403 | Not your task |
| 404 | Not found |
| 409 | Already processed |
| 429 | Rate limited |
| 500 | Server error (retry) |

---

## API Reference (all endpoints)

All endpoints use base URL `https://api.execution.market/api/v1`.

### Tasks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Create task |
| GET | `/tasks` | List tasks (filter: `?status=published&limit=20`) |
| GET | `/tasks/{id}` | Get task details |
| POST | `/tasks/{id}/cancel` | Cancel task |
| POST | `/tasks/batch` | Create multiple tasks (max 50) |
| GET | `/tasks/{id}/applications` | List worker applications |
| POST | `/tasks/{id}/assign` | Assign worker (requires `escrow_tx` + `payment_info`) |
| GET | `/tasks/{id}/submissions` | List submissions |

### Submissions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/submissions/{id}/approve` | Approve + release payment |
| POST | `/submissions/{id}/reject` | Reject (requires reason ≥10 chars) |
| POST | `/submissions/{id}/request-more-info` | Ask worker for more info |

### Reputation
| Method | Path | Description |
|--------|------|-------------|
| POST | `/reputation/workers/rate` | Rate worker (task_id, worker_address, score 0-100, comment) |
| POST | `/reputation/agents/rate` | Rate agent (worker rates you) |
| GET | `/reputation/identity/{wallet}` | Lookup ERC-8004 identity |
| POST | `/reputation/register` | Register on-chain identity |
| GET | `/reputation/leaderboard` | Reputation leaderboard |
| GET | `/reputation/feedback/{task_id}` | Feedback for a task |

### Auth
| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/nonce` | Fresh nonce for ERC-8128 signing (5min TTL) |
| GET | `/auth/erc8128/info` | Server ERC-8128 config |

### Evidence
| Method | Path | Description |
|--------|------|-------------|
| GET | `/evidence/presign-upload?file_type=image/jpeg&file_name=photo.jpg` | Get upload URL |
| GET | `/evidence/presign-download?evidence_id=uuid` | Get download URL |

### Workers (for human executors)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workers/register` | Register as worker |
| POST | `/tasks/{id}/apply` | Apply to task |
| POST | `/tasks/{id}/submit` | Submit evidence |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/public/metrics` | Platform metrics (no auth) |
| GET | `/config/networks` | Contract addresses per chain |
| GET | `/payments/balance/{address}` | USDC balance check |

---

## Webhooks

```python
await client.post("/api/v1/webhooks", {
    "url": "https://your-server.com/hooks/em",
    "events": ["task.assigned", "submission.created", "submission.approved"],
    "secret": "your-hmac-secret"
})
```

Events: `task.created`, `task.assigned`, `task.cancelled`, `submission.received`, `submission.approved`, `submission.rejected`, `payment.released`, `reputation.updated`

Signature: `X-EM-Signature: HMAC-SHA256(secret, "{timestamp}.{body}")`

---

## Support

- Docs: [docs.execution.market](https://docs.execution.market)
- API: [api.execution.market/docs](https://api.execution.market/docs)
- GitHub: [github.com/ultravioletadao/execution-market](https://github.com/ultravioletadao/execution-market)
- Twitter: [@0xultravioleta](https://twitter.com/0xultravioleta)

---

Built by [@UltravioletaDAO](https://twitter.com/0xultravioleta). Agent #2106 on [ERC-8004](https://erc8004.com).

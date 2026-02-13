# ERC-8128 Integration Plan — Execution Market

## Context

Execution Market currently authenticates AI agents via API keys (`em_<tier>_<random>`) stored as SHA-256 hashes in Supabase. This is a Web2 pattern disconnected from the agent's on-chain identity (ERC-8004) and payment wallet (EIP-3009). ERC-8128 unifies auth with the agent's Ethereum wallet — the same wallet that pays is the wallet that authenticates. This eliminates API key management, reduces onboarding friction to zero, and creates a complete Web3 identity stack: ERC-8128 (auth) + ERC-8004 (identity) + EIP-3009 (payments).

**User decisions:**
- NonceStore: **DynamoDB** (not Redis — not deployed yet)
- Encryption: DynamoDB encryption at rest (default) + in-transit via HTTPS
- RPC for ERC-1271: QuickNode RPCs (user will provide)
- Auth strategy: **Dual auth** — API keys + ERC-8128 coexist simultaneously
- No breaking changes to existing agents

---

## Architecture Overview

```
HTTP Request with Signature + Signature-Input headers
    |
    v
RateLimitMiddleware (existing, unchanged)
    |
    v
verify_agent_auth() <-- NEW unified auth dependency
    |-- Has Signature header? --> verify_erc8128_request()
    |       |-- Reconstruct RFC 9421 signature base
    |       |-- EIP-191 ecrecover --> wallet address
    |       |-- Consume nonce via DynamoDB NonceStore
    |       |-- Cross-reference ERC-8004 identity (cached)
    |       '-- Return AgentAuth(wallet, agent_id, method="erc8128")
    |
    '-- Has Bearer/X-API-Key? --> verify_api_key() (existing, unchanged)
            '-- Return APIKeyData (existing behavior)
```

---

## Implementation Steps

### Step 1: Python ERC-8128 Verifier Module

**New file:** `mcp_server/integrations/erc8128/verifier.py` (~250 lines)

**What it does:**
- Parses `Signature-Input` header (RFC 8941 Structured Dictionary)
- Extracts keyid (`erc8128:<chainId>:<address>`), nonce, created, expires
- Reconstructs the RFC 9421 signature base from the HTTP request
- Computes `Content-Digest` (SHA-256) for body verification
- Applies EIP-191 prefix and recovers signer address via `ecrecover`
- Validates: signature matches keyid address, timestamps valid, nonce fresh

**Key functions:**
```python
async def verify_erc8128_request(
    request: Request,
    nonce_store: NonceStore,
    policy: VerifyPolicy | None = None,
) -> ERC8128Result:
    """Verify ERC-8128 signed HTTP request. Returns wallet address or error."""

@dataclass
class ERC8128Result:
    ok: bool
    address: str | None = None      # Recovered wallet address
    chain_id: int | None = None     # From keyid
    reason: str | None = None       # Error reason if not ok
    binding: str = "request-bound"  # or "class-bound"
    replayable: bool = False

@dataclass
class VerifyPolicy:
    max_validity_sec: int = 300     # 5 minutes max window
    clock_skew_sec: int = 30        # 30s clock drift tolerance
    strict_label: bool = False      # Require "eth" label
    allow_replayable: bool = False  # Reject nonce-less by default
    allow_class_bound: bool = False # Reject class-bound by default
```

**Dependencies (all already in requirements.txt):**
- `eth_account` (via `web3`) — for `ecrecover` / `recover_message`
- `hashlib` (stdlib) — SHA-256 for Content-Digest
- `base64` (stdlib) — signature decoding

**New dependency needed:**
- None for core verification (pure Python + eth_account)

**Reference files:**
- `mcp_server/integrations/erc8004/identity.py` — caching pattern (TTL dict)
- `mcp_server/api/auth.py` — `APIKeyData` pattern for result dataclass

---

### Step 2: DynamoDB NonceStore

**New file:** `mcp_server/integrations/erc8128/nonce_store.py` (~120 lines)

**What it does:**
- Implements the `NonceStore` interface: `consume(nonce_key, ttl_seconds) -> bool`
- Uses DynamoDB conditional PutItem (atomic check-and-set)
- DynamoDB TTL handles automatic cleanup (no cron jobs)
- Graceful fallback to in-memory store for local development

**Implementation:**
```python
class DynamoDBNonceStore:
    """ERC-8128 nonce store backed by DynamoDB with TTL."""

    async def consume(self, key: str, ttl_seconds: int) -> bool:
        """
        Atomically consume a nonce. Returns True if fresh (first use),
        False if already consumed (replay attempt).
        Uses DynamoDB ConditionExpression to prevent race conditions.
        """
        try:
            self.table.put_item(
                Item={
                    "nonce_key": key,          # Partition key
                    "expires_at": int(time.time()) + ttl_seconds,  # DynamoDB TTL
                    "consumed_at": int(time.time()),
                },
                ConditionExpression="attribute_not_exists(nonce_key)",
            )
            return True  # Fresh nonce
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False  # Replay attempt
            raise

class InMemoryNonceStore:
    """Fallback for local development without DynamoDB."""

    async def consume(self, key: str, ttl_seconds: int) -> bool:
        now = time.time()
        # Evict expired entries
        self._store = {k: v for k, v in self._store.items() if v > now}
        if key in self._store:
            return False  # Replay
        self._store[key] = now + ttl_seconds
        return True
```

**Nonce key format:** `erc8128:{chain_id}:{address}:{nonce_value}`

**DynamoDB table schema:**

| Attribute | Type | Purpose |
|-----------|------|---------|
| `nonce_key` | String (PK) | `erc8128:8453:0x857f...:abc123` |
| `expires_at` | Number | Unix timestamp for DynamoDB TTL |
| `consumed_at` | Number | When the nonce was first seen |

**Environment variables:**
- `ERC8128_NONCE_TABLE` — DynamoDB table name (default: `em-production-nonce-store`)
- `ERC8128_NONCE_STORE` — `dynamodb` (default) or `memory` (dev)

**Reference files:**
- `mcp_server/security/rate_limiter.py` — Redis + in-memory fallback pattern (lines 138-222)
- `requirements.txt` line 60 — `boto3>=1.34.0` already present

---

### Step 3: ERC-1271 Smart Account Verification (Optional)

**New file:** `mcp_server/integrations/erc8128/erc1271.py` (~80 lines)

**What it does:**
- For smart contract wallets (Safe, ERC-4337), calls `isValidSignature(hash, signature)` on-chain
- Returns `true` if magic value `0x1626ba7e` returned
- Uses QuickNode RPC (user will provide URL)
- Cached per wallet+hash for 5 minutes

**Implementation:**
```python
async def verify_erc1271_signature(
    address: str,
    message_hash: bytes,
    signature: bytes,
    chain_id: int,
) -> bool:
    """Call isValidSignature on a smart contract wallet."""
    rpc_url = _get_rpc_for_chain(chain_id)  # QuickNode URLs
    # selector: 0x1626ba7e
    calldata = IS_VALID_SIGNATURE_SELECTOR + encode_abi(["bytes32", "bytes"], [message_hash, signature])
    result = await _eth_call(address, calldata, rpc_url)
    return result[:10] == "0x1626ba7e"
```

**Reference files:**
- `mcp_server/integrations/erc8004/identity.py` — `_eth_call()` pattern (lines 285-330)
- Same JSON-RPC pattern for `eth_call` already used for `balanceOf`

---

### Step 4: Unified Auth Dependency

**Modified file:** `mcp_server/api/auth.py`

**What changes:**
- New `AgentAuth` dataclass (superset of `APIKeyData`)
- New `verify_agent_auth()` function — unified entry point
- Existing `verify_api_key*` functions remain unchanged
- Routes gradually migrate from `Depends(verify_api_key_if_required)` to `Depends(verify_agent_auth)`

**New code (~60 lines added to auth.py):**
```python
@dataclass
class AgentAuth:
    """Unified auth result for both API keys and ERC-8128."""
    agent_id: str
    wallet_address: str | None = None
    tier: str = "free"
    auth_method: str = "api_key"  # "api_key" | "erc8128"
    chain_id: int | None = None
    organization_id: str | None = None
    erc8004_registered: bool = False
    erc8004_agent_id: int | None = None

async def verify_agent_auth(
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
) -> AgentAuth:
    """
    Unified auth: tries ERC-8128 first (if Signature header present),
    falls back to API key auth.
    """
    # Path 1: ERC-8128 signature
    if "signature" in request.headers:
        result = await verify_erc8128_request(request, _nonce_store)
        if result.ok:
            # Cross-reference with ERC-8004 identity
            identity = await _resolve_erc8004_identity(result.address, result.chain_id)
            return AgentAuth(
                agent_id=identity.get("agent_id", result.address),
                wallet_address=result.address,
                auth_method="erc8128",
                chain_id=result.chain_id,
                erc8004_registered=identity.get("registered", False),
                erc8004_agent_id=identity.get("agent_id"),
            )
        # ERC-8128 failed -- DON'T fall through to API key
        raise HTTPException(401, detail=f"ERC-8128 verification failed: {result.reason}")

    # Path 2: API key (existing behavior)
    api_key_data = await verify_api_key_if_required(authorization=authorization, x_api_key=x_api_key)
    return AgentAuth(
        agent_id=api_key_data.agent_id,
        tier=api_key_data.tier,
        auth_method="api_key",
        organization_id=api_key_data.organization_id,
    )
```

**ERC-8004 cross-reference flow:**
1. ERC-8128 gives us wallet address (e.g., `0x857f...`)
2. Call `check_worker_identity(wallet)` — on-chain `balanceOf()` + `tokenOfOwnerByIndex()`
3. If registered -> get agent_id (e.g., 2106)
4. If not registered -> use wallet address as agent_id (still valid)
5. Cache result for 5 minutes (existing pattern)

**Note:** The Facilitator only supports `agent_id -> identity` (not reverse). For wallet->agent_id we use the direct on-chain RPC call that `identity.py` already implements via `check_worker_identity()`.

---

### Step 5: Rate Limiting by Wallet

**Modified file:** `mcp_server/api/middleware.py`

**What changes:**
- `RateLimitMiddleware` detects ERC-8128 headers for pre-auth tier estimation
- If `Signature-Input` header contains keyid, extract wallet address for rate limiting
- Tier determined by ERC-8004 reputation score (future) or default to STARTER

**Minimal change (~15 lines in `_extract_api_key`):**
```python
def _extract_rate_limit_identifier(request: Request) -> tuple[str | None, str]:
    """Extract identifier and estimated tier for rate limiting."""
    # Check API key first (existing)
    api_key = _extract_api_key(request)
    if api_key:
        return api_key, _estimate_tier(api_key)

    # Check ERC-8128 keyid (new)
    sig_input = request.headers.get("signature-input", "")
    if "erc8128:" in sig_input:
        # Extract wallet from keyid for rate limit bucketing
        match = re.search(r'keyid="erc8128:\d+:(0x[a-fA-F0-9]{40})"', sig_input)
        if match:
            return match.group(1).lower(), "starter"  # Default tier for ERC-8128

    return None, "free"
```

---

### Step 6: Terraform — DynamoDB Table + IAM

**New file:** `infrastructure/terraform/dynamodb.tf`

```hcl
resource "aws_dynamodb_table" "nonce_store" {
  name         = "${local.name_prefix}-nonce-store"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "nonce_key"

  attribute {
    name = "nonce_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true  # AWS-managed CMK (free, encrypted at rest)
  }

  point_in_time_recovery {
    enabled = false  # Not needed for ephemeral nonces
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-nonce-store"
    Purpose = "ERC-8128 nonce replay protection"
  })
}
```

**Modified file:** `infrastructure/terraform/ecs.tf`

Add DynamoDB permissions to ECS task role:
```hcl
resource "aws_iam_role_policy" "ecs_dynamodb" {
  name = "${local.name_prefix}-ecs-dynamodb"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ]
      Resource = aws_dynamodb_table.nonce_store.arn
    }]
  })
}
```

Add env var to MCP server task definition:
```hcl
{ name = "ERC8128_NONCE_TABLE", value = aws_dynamodb_table.nonce_store.name }
{ name = "ERC8128_NONCE_STORE", value = "dynamodb" }
```

**Cost estimate:** On-demand DynamoDB with TTL cleanup
- Write: ~$1.25/million writes
- Read: ~$0.25/million reads
- Storage: $0.25/GB/month
- At 1000 agent requests/day = ~$0.04/month total

---

### Step 7: Tests

**New file:** `mcp_server/tests/test_erc8128.py` (~300 lines)

Test categories:
1. **Signature verification** — valid EOA signatures, invalid signatures, wrong address
2. **Nonce management** — fresh nonce accepted, replay rejected, TTL expiry
3. **Timestamp validation** — expired signatures, not-yet-valid, clock skew
4. **Content-Digest** — body hash match, body hash mismatch, missing digest
5. **Request binding** — all components signed, missing component, class-bound rejection
6. **KeyId parsing** — valid format, invalid format, various chain IDs
7. **ERC-1271** — mock smart account verification (mocked RPC)
8. **Dual auth** — ERC-8128 + API key coexistence, priority order
9. **DynamoDB NonceStore** — conditional write success/failure (mocked boto3)
10. **InMemoryNonceStore** — eviction, TTL, concurrent access

**Pytest marker:** `erc8128` (add to `pytest.ini`)

**Reference:** Follow existing test patterns in `tests/test_reputation_scoring.py` and `tests/test_erc8004_side_effects.py`

---

### Step 8: Documentation & API

**Modified file:** `mcp_server/api/routes.py`

Add ERC-8128 auth info to OpenAPI docs:
- SecurityScheme `erc8128` alongside existing `apiKey`
- Document both auth methods in endpoint descriptions

**New endpoint:** `GET /api/v1/auth/erc8128/info`
- Returns ERC-8128 configuration (supported chains, policy, nonce TTL)
- Public endpoint (no auth required)
- Helps agents discover ERC-8128 support

---

## File Summary

| Action | File | Lines Changed |
|--------|------|---------------|
| **NEW** | `mcp_server/integrations/erc8128/__init__.py` | 5 |
| **NEW** | `mcp_server/integrations/erc8128/verifier.py` | ~250 |
| **NEW** | `mcp_server/integrations/erc8128/nonce_store.py` | ~120 |
| **NEW** | `mcp_server/integrations/erc8128/erc1271.py` | ~80 |
| **EDIT** | `mcp_server/api/auth.py` | +60 (AgentAuth + verify_agent_auth) |
| **EDIT** | `mcp_server/api/middleware.py` | +15 (ERC-8128 rate limit extraction) |
| **NEW** | `mcp_server/tests/test_erc8128.py` | ~300 |
| **EDIT** | `mcp_server/pytest.ini` | +1 (erc8128 marker) |
| **NEW** | `infrastructure/terraform/dynamodb.tf` | ~35 |
| **EDIT** | `infrastructure/terraform/ecs.tf` | +20 (IAM + env var) |
| **NEW** | `docs/planning/ERC8128_INTEGRATION_PLAN.md` | Copy of this plan |

**Total new code:** ~850 lines
**Total modified:** ~96 lines
**No breaking changes.** All existing API key auth continues working.

---

## Verification Plan

### Local Testing
```bash
# 1. Run new ERC-8128 tests
cd mcp_server && set TESTING=true && pytest tests/test_erc8128.py -v

# 2. Run full test suite (ensure nothing broken)
cd mcp_server && set TESTING=true && pytest

# 3. Lint & format
cd mcp_server && ruff format . && ruff check .
```

### Manual E2E Test
```python
# Client side (using viem/ethers)
from eth_account import Account
import requests

# Sign a request to create a task
account = Account.from_key("0x...")  # dev wallet
# ... construct ERC-8128 headers ...
response = requests.post(
    "http://localhost:8000/api/v1/tasks",
    headers={"Signature": sig, "Signature-Input": sig_input, "Content-Digest": digest},
    json={"title": "Test ERC-8128 auth", "bounty_usd": 0.10, ...}
)
assert response.status_code == 201
```

### Infrastructure Testing
```bash
# 1. Terraform plan (verify DynamoDB + IAM changes)
cd infrastructure/terraform && terraform plan

# 2. Terraform apply (provision DynamoDB table)
cd infrastructure/terraform && terraform apply

# 3. Verify DynamoDB table created
aws dynamodb describe-table --table-name em-production-nonce-store --region us-east-2
```

---

## Migration Path

1. **Phase 1 (this plan):** Dual auth — both API keys and ERC-8128 accepted
2. **Phase 2 (future):** Rate limiting by ERC-8004 reputation score instead of API tier
3. **Phase 3 (future):** Deprecate API keys for agents (wallets-only auth)
4. **Phase 4 (future):** ERC-8128 for outbound webhooks (prove our identity)

---

## Reference Sources

### ERC-8128 Specification (Primary)

| Resource | URL |
|----------|-----|
| **ERC-8128 spec (eip.tools)** | https://eip.tools/eip/8128 |
| **ERC-8128 raw markdown** | https://raw.githubusercontent.com/slice-so/ERCs/refs/heads/temp-eth-http-message-signatures/ERCS/erc-8128.md |
| **Discussion thread** | https://ethereum-magicians.org/t/erc-8128-signed-http-requests-with-ethereum/27515 |
| **Authors** | Domenico Macellaro ([@zerohex-eth](https://github.com/zerohex-eth)), Jacopo Ranalli ([@jacopo-eth](https://github.com/jacopo-eth)) — both from [Slice](https://slice.so) |
| **Status** | Draft (Standards Track: ERC) |
| **Created** | 2026-01-16 |
| **Requires** | [EIP-155](https://eips.ethereum.org/EIPS/eip-155), [ERC-191](https://eips.ethereum.org/EIPS/eip-191), [ERC-1271](https://eips.ethereum.org/EIPS/eip-1271) |
| **License** | [CC0](https://raw.githubusercontent.com/slice-so/ERCs/refs/heads/temp-eth-http-message-signatures/LICENSE.md) |

### IETF RFCs (HTTP Message Signatures stack)

| RFC | Title | URL |
|-----|-------|-----|
| **RFC 9421** | HTTP Message Signatures | https://www.rfc-editor.org/rfc/rfc9421 |
| **RFC 9421** | Creating the Signature Base | https://www.rfc-editor.org/rfc/rfc9421#name-creating-the-signature-base |
| **RFC 9421** | Including a Message Signature | https://www.rfc-editor.org/rfc/rfc9421#name-including-a-message-signatu |
| **RFC 9421** | HTTP Message Components | https://www.rfc-editor.org/rfc/rfc9421#name-http-message-components |
| **RFC 8941** | Structured Field Values for HTTP | https://www.rfc-editor.org/rfc/rfc8941.html |
| **RFC 9530** | Digest Fields (Content-Digest) | https://www.rfc-editor.org/rfc/rfc9530.html |
| **RFC 2119** | Key words for use in RFCs | https://www.rfc-editor.org/rfc/rfc2119 |
| **RFC 8174** | Ambiguity of Uppercase vs Lowercase in RFC 2119 | https://www.rfc-editor.org/rfc/rfc8174 |

### Ethereum Standards (Dependencies)

| EIP/ERC | Title | URL |
|---------|-------|-----|
| **ERC-191** | Signed Data Standard | https://eips.ethereum.org/EIPS/eip-191 |
| **ERC-1271** | Standard Signature Validation Method for Contracts | https://eips.ethereum.org/EIPS/eip-1271 |
| **EIP-155** | Simple Replay Attack Protection (chain ID) | https://eips.ethereum.org/EIPS/eip-155 |
| **EIP-712** | Typed Structured Data Hashing and Signing | https://eips.ethereum.org/EIPS/eip-712 |
| **EIP-4361** | Sign-In with Ethereum (SIWE) | https://eips.ethereum.org/EIPS/eip-4361 |
| **EIP-3009** | Transfer With Authorization (gasless USDC) | https://eips.ethereum.org/EIPS/eip-3009 |
| **ERC-8004** | Trustless Agents (Identity Registry) | https://eips.ethereum.org/EIPS/eip-8004 |

### Ethereum Standards (Referenced in spec rationale, optional)

| EIP/ERC | Title | URL |
|---------|-------|-----|
| **ERC-6492** | Signature Validation for Pre-deployed Contracts | https://eips.ethereum.org/EIPS/eip-6492 |
| **ERC-8010** | Pre-delegated Signature Verification | https://ethereum-magicians.org/t/erc-8010-pre-delegated-signature-verification/25201 |

### Python Libraries (Implementation)

| Library | Purpose | URL |
|---------|---------|-----|
| **eth-account** | EIP-191 ecrecover / `recover_message` | https://pypi.org/project/eth-account/ |
| **web3.py** | Ethereum JSON-RPC (includes eth-account) | https://pypi.org/project/web3/ |
| **http-message-signatures** | RFC 9421 Python implementation (reference, not used) | https://github.com/pyauth/http-message-signatures |
| **requests-http-signature** | RFC 9421 Requests plugin (reference, not used) | https://github.com/pyauth/requests-http-signature |
| **boto3** | AWS SDK for DynamoDB NonceStore | https://pypi.org/project/boto3/ |

### AWS Documentation (DynamoDB NonceStore)

| Resource | URL |
|----------|-----|
| **DynamoDB TTL** | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html |
| **DynamoDB Conditional Writes** | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html |
| **DynamoDB Encryption at Rest** | https://docs.aws.amazon.com/prescriptive-guidance/latest/encryption-best-practices/dynamodb.html |
| **DynamoDB Security Best Practices** | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices-security-preventative.html |

### Educational / Explainers

| Resource | URL |
|----------|-----|
| Understanding HTTP Message Signatures (developer guide) | https://victoronsoftware.com/posts/http-message-signatures/ |
| Verification of HTTP Message Signatures (Medium) | https://darutk.medium.com/verification-of-http-message-signatures-501bbdc7dfec |
| Understanding EIP-191 & EIP-712 (Cyfrin) | https://www.cyfrin.io/blog/understanding-ethereum-signature-standards-eip-191-eip-712 |
| EIP-1271: Signature Verification for Smart Contract Wallets (Dynamic) | https://www.dynamic.xyz/blog/eip-1271 |
| EIP-1271: Smart Contract Signatures Tutorial (ethereum.org) | https://ethereum.org/developers/tutorials/eip-1271-smart-contract-signatures/ |
| ERC-3009: The Protocol Powering x402 Payments (PayIn) | https://blog.payin.com/posts/erc-3009-x402/ |
| Content-Digest header (MDN) | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Digest |

### Related Projects & Repos

| Resource | URL |
|----------|-----|
| **Ethereum ERCs repository** | https://github.com/ethereum/ERCs |
| **Ethereum EIPs repository** | https://github.com/ethereum/EIPs |
| **ERC-8004 contracts** | https://github.com/erc-8004/erc-8004-contracts |
| **Slice.so** (ERC-8128 authors' org) | https://slice.so |
| **OpenZeppelin IERC1271** | https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/interfaces/IERC1271.sol |
| **ERC-8128 source branch** | https://github.com/slice-so/ERCs/tree/temp-eth-http-message-signatures |

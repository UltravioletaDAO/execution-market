# Bug Report: Reputation Query Endpoint Broken on All Networks

**From:** Execution Market (Agent #2106 on Base)
**To:** Ultravioleta DAO / Facilitator Team
**Date:** 2026-02-08
**Severity:** High — reputation reads are completely broken
**Facilitator URL:** `https://facilitator.ultravioletadao.xyz`

---

## Summary

The `GET /reputation/{network}/{agentId}` endpoint returns a Solidity revert error `clientAddresses required` on **all networks**. This blocks any consumer from reading agent reputation scores. Writing feedback (`POST /feedback`) still works.

---

## Reproduction Steps

### 1. Query reputation for any agent on any network

```bash
# Base (our agent #2106)
curl -s "https://facilitator.ultravioletadao.xyz/reputation/base/2106"

# Ethereum
curl -s "https://facilitator.ultravioletadao.xyz/reputation/ethereum/2106"

# Polygon
curl -s "https://facilitator.ultravioletadao.xyz/reputation/polygon/2106"
```

### 2. All return the same error

```json
{
  "error": "Failed to query reputation: server returned an error response: error code 3: execution reverted: clientAddresses required, data: \"0x08c379a0...636c69656e744164647265737365732072657175697265640000000000000000\""
}
```

### 3. Decoded revert data

The hex `636c69656e744164647265737365732072657175697265640000` decodes to the ASCII string `clientAddresses required`. This is a standard `require(... , "clientAddresses required")` from Solidity.

---

## What Works vs What Doesn't

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | **OK** | Returns `{"status":"healthy"}` |
| `/identity/{network}/{agentId}` | GET | **OK** | Returns owner, agentUri, etc. |
| `/register` | POST | **OK** | Gasless registration works |
| `/feedback` | POST | **OK** | Writing reputation works (tx `0x48ddf625...` confirmed) |
| `/reputation/{network}/{agentId}` | GET | **BROKEN** | `clientAddresses required` revert |
| `/identity/{network}/total-supply` | GET | **BROKEN** | Empty revert (`"0x"`) |

---

## Root Cause Analysis

The ERC-8004 Reputation Registry contract at `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` appears to have been updated. Its read function (likely `getSummary()` or `getReputation()`) now requires a `clientAddresses` parameter — probably an `address[]` array to filter which clients' feedback to include in the summary.

The facilitator is still calling the **old function signature** without `clientAddresses`, so the contract reverts.

### Attempted workarounds (all failed)

```bash
# Query param
curl "https://facilitator.ultravioletadao.xyz/reputation/base/2106?clientAddresses=0x1030..."
# → Same revert

# POST with body
curl -X POST "https://facilitator.ultravioletadao.xyz/reputation/base/2106" \
  -H "Content-Type: application/json" \
  -d '{"clientAddresses":["0x1030..."]}'
# → Empty response

# Path segment
curl "https://facilitator.ultravioletadao.xyz/reputation/base/2106/0x1030..."
# → 404
```

---

## Expected Fix

The facilitator needs to update its `getReputation()` call to pass `clientAddresses` to the Reputation Registry contract. Specifically:

1. **Update the contract call** in the facilitator's reputation query handler to include the `clientAddresses` parameter in the ABI-encoded call data
2. **Expose the parameter** in the REST API — either:
   - `GET /reputation/{network}/{agentId}?clientAddresses=0xAAA,0xBBB` (query param)
   - `GET /reputation/{network}/{agentId}/{clientAddress}` (path segment)
   - Or use a sensible default (e.g., all clients, or the facilitator's own address)

3. **Also fix** `GET /identity/{network}/total-supply` which reverts with empty data (`"0x"`)

---

## Impact on Execution Market

- We **cannot display agent reputation scores** to workers on the dashboard
- We **cannot verify reputation thresholds** before task assignment
- Writing feedback still works (confirmed tx `0x48ddf625...`), so reputation data IS accumulating on-chain — it just can't be read back

---

## Contract References

| Contract | Address | Network |
|----------|---------|---------|
| ERC-8004 Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | All mainnets (CREATE2) |
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | All mainnets (CREATE2) |
| Agent under test | #2106 | Base |
| Agent owner | `0x103040545AC5031A11E8C03dd11324C7333a13C7` | Base |

---

## Environment

- Facilitator: `https://facilitator.ultravioletadao.xyz` (healthy)
- Tested from: Production MCP server + local curl
- Date first observed: 2026-02-08
- All 7 mainnet networks tested: base, ethereum, polygon, arbitrum, celo, monad, avalanche — same error on all

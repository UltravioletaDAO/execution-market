# SDK Bug Report — uvd-x402-sdk v0.13.0

> From: Execution Market (Ultravioleta DAO)
> To: x402r / BackTrackCo team
> Date: 2026-02-12
> Contact: @UltravioletaDAO (Telegram/GitHub)

---

## Context

We are the largest production integration of x402r escrow contracts. During
our E2E testing on Base mainnet (2026-02-12), we identified critical bugs in
`uvd-x402-sdk v0.13.0` that break escrow operations when used with
`eth_account >= 0.10.0` and `web3.py >= 6.x`.

These bugs prevent `AdvancedEscrowClient.authorize()` from working at all
without manual patches. We have workarounds, but the SDK itself should be fixed.

**Our stack:**
- Python 3.11
- `uvd-x402-sdk==0.13.0`
- `eth_account==0.10.0`
- `eth_abi==5.2.0`
- `web3==6.x` (with HexBytes)

---

## Bug 1: Double `0x` prefix in `_compute_nonce()` (CRITICAL)

### Location

`uvd_x402_sdk/advanced_escrow.py`, line ~546

### Current code

```python
def _compute_nonce(self, payment_info: PaymentInfo) -> str:
    # ... encode and hash ...
    return "0x" + Web3.keccak(final_encoded).hex()
```

### Problem

`Web3.keccak()` returns a `HexBytes` object. In `web3 >= 6.x` / `hexbytes >= 1.x`,
`HexBytes.hex()` returns a string **already prefixed with `0x`**:

```python
>>> Web3.keccak(b"test").hex()
'0x9c22ff5f21f0b81b113e63f7db6da94fedef11b2119b4088b89664fb9a3cb658'
```

So `"0x" + "0xabc..."` produces `"0x0xabc..."` — a **double prefix** that is
invalid everywhere: signing, payload construction, facilitator API.

### Fix

```python
def _compute_nonce(self, payment_info: PaymentInfo) -> str:
    # ... encode and hash ...
    h = Web3.keccak(final_encoded).hex()
    # HexBytes.hex() already includes 0x in web3 >= 6.x
    return h if h.startswith("0x") else "0x" + h
```

Or more defensively:

```python
raw = Web3.keccak(final_encoded)
return "0x" + raw.hex().removeprefix("0x")
```

### Impact

Without this fix, **all escrow operations fail** because:
1. The nonce in the ERC-3009 message is corrupt → wrong signature
2. The nonce in the facilitator payload is corrupt → API rejects it

---

## Bug 2: `bytes32` encoding fails in `_sign_erc3009()` (CRITICAL)

### Location

`uvd_x402_sdk/advanced_escrow.py`, line ~572

### Current code

```python
def _sign_erc3009(self, auth: dict) -> str:
    # ...
    message = {
        # ...
        "nonce": auth["nonce"],  # This is a hex string like "0xabc..."
    }
    signable = encode_typed_data(domain_data=domain, message_types=types, message_data=message)
```

### Problem

`encode_typed_data()` in `eth_account >= 0.10.0` expects `bytes` for the
`bytes32` nonce field, not a hex string. When it receives a hex string like
`"0xabc..."`, the encoder treats it as ASCII bytes: `b'0xabc...'` which is
66+ bytes — too large for `bytes32` (32 bytes max).

Error:
```
eth_abi.exceptions.ValueOutOfBounds: Value `b'0x0xabc...'` of type <class 'bytes'>
cannot be encoded by BytesEncoder: exceeds total byte size for bytes32 encoding
```

### Fix

```python
def _sign_erc3009(self, auth: dict) -> str:
    # ...
    nonce = auth["nonce"]
    if isinstance(nonce, str):
        nonce = nonce.removeprefix("0x")
        nonce = bytes.fromhex(nonce)

    message = {
        # ...
        "nonce": nonce,  # Now bytes, correct for bytes32
    }
```

### Impact

Without this fix, `authorize()` crashes with `ValueOutOfBounds` before
even reaching the facilitator.

---

## Bug 3: Potential double `0x` in signature (MINOR)

### Location

`uvd_x402_sdk/advanced_escrow.py`, line ~576

### Current code

```python
signed = self.account.sign_message(signable)
return "0x" + signed.signature.hex()
```

### Problem

If `signed.signature` is a `HexBytes` (not plain `bytes`), then `.hex()` may
already include the `0x` prefix, producing `"0x0xabc..."`.

### Fix

```python
sig_hex = signed.signature.hex()
return sig_hex if sig_hex.startswith("0x") else "0x" + sig_hex
```

---

## Facilitator Feedback: Nonce Management Under Rapid TXs

### Issue

When sending multiple escrow operations in rapid succession (< 5 seconds apart),
the facilitator returns nonce errors:

```
ErrorResp(ErrorPayload { code: -32000, message: "nonce too low: next nonce 4571, tx nonce 4569" })
```

And timeout errors:

```
ContractCall("TxWatcher(Timeout)")
```

### Workaround

We currently insert a 15-second delay between escrow operations. This is
too long for production use (task creation should complete in < 5s).

### Suggested Fix

The facilitator's nonce manager should:
1. Wait for TX confirmation before reusing the nonce slot
2. Implement a nonce queue for concurrent operations
3. Consider a configurable `nonce_wait_ms` parameter

> **Note**: We had a similar issue with the V1 refund flow (via `settle`
> with extension args). That was fixed by adding a delay in the facilitator's
> nonce manager. The V2 escrow scheme (`authorize`/`release`/`refund`) likely
> needs the same treatment.

---

## Our Workaround (Monkey-Patch)

Until these are fixed upstream, we use this patch in our test scripts:

```python
from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient
from web3 import Web3
from eth_account.messages import encode_typed_data

_orig_compute = AdvancedEscrowClient._compute_nonce

def _fix_hex(v):
    """Remove double 0x prefix."""
    while isinstance(v, str) and v.startswith("0x0x"):
        v = "0x" + v[4:]
    return v

def _patched_compute_nonce(self, pi):
    return _fix_hex(_orig_compute(self, pi))

def _patched_sign_erc3009(self, auth):
    nonce = _fix_hex(auth.get("nonce", ""))
    if isinstance(nonce, str) and nonce.startswith("0x"):
        nonce = bytes.fromhex(nonce[2:])

    domain = {
        "name": "USD Coin", "version": "2",
        "chainId": self.chain_id,
        "verifyingContract": Web3.to_checksum_address(self.contracts["usdc"]),
    }
    types = {
        "ReceiveWithAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"},
        ],
    }
    message = {
        "from": Web3.to_checksum_address(auth["from"]),
        "to": Web3.to_checksum_address(auth["to"]),
        "value": int(auth["value"]),
        "validAfter": int(auth["validAfter"]),
        "validBefore": int(auth["validBefore"]),
        "nonce": nonce,
    }
    signable = encode_typed_data(
        domain_data=domain, message_types=types, message_data=message
    )
    signed = self.account.sign_message(signable)
    sig = signed.signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig
    return _fix_hex(sig)

AdvancedEscrowClient._compute_nonce = _patched_compute_nonce
AdvancedEscrowClient._sign_erc3009 = _patched_sign_erc3009
```

---

## Evidence

All bugs were discovered during our E2E test run on Base mainnet. Full
transaction evidence (7 successful TXs) is in our
[E2E Full Flow Report](./E2E_FULL_FLOW_REPORT.md).

**PaymentOperator contract page on BaseScan:**
https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723

Shows 20+ transactions through our operator, all labeled as "x402 Transaction"
by BaseScan.

---

## Environment to Reproduce

```bash
pip install uvd-x402-sdk==0.13.0 eth-account==0.10.0 web3>=6.0
python -c "
from uvd_x402_sdk.advanced_escrow import AdvancedEscrowClient, TaskTier
import os

client = AdvancedEscrowClient(
    private_key='0x' + 'a' * 64,  # dummy key
    facilitator_url='https://facilitator.ultravioletadao.xyz',
    rpc_url='https://mainnet.base.org',
    chain_id=8453,
    operator_address='0xb9635f544665758019159c04c08a3d583dadd723',
)
pi = client.build_payment_info(
    receiver='0x0000000000000000000000000000000000000001',
    amount=50_000,
    tier=TaskTier.MICRO,
)
nonce = client._compute_nonce(pi)
print(f'Nonce: {repr(nonce)}')  # Will show '0x0x...' (double prefix)
# client.authorize(pi)  # Will crash with ValueOutOfBounds
"
```

---

## Summary

| # | Bug | File | Line | Severity | Status |
|---|-----|------|------|----------|--------|
| 1 | Double `0x` in `_compute_nonce` | `advanced_escrow.py` | ~546 | Critical | Workaround applied |
| 2 | `bytes32` encoding in `_sign_erc3009` | `advanced_escrow.py` | ~572 | Critical | Workaround applied |
| 3 | Double `0x` in signature return | `advanced_escrow.py` | ~576 | Minor | Workaround applied |
| 4 | Facilitator nonce management | Facilitator (Rust) | N/A | Medium | Using 15s delay |

We're happy to submit a PR to fix bugs 1-3 in the SDK if you'd prefer that
over fixing them yourselves. Just point us to the right repo/branch.

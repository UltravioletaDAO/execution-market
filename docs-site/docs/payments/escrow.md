# Escrow Lifecycle

Execution Market uses **x402r AuthCaptureEscrow** for on-chain fund locking. This is a shared singleton contract on each chain that holds funds in TokenStore clones (EIP-1167 proxy pattern).

## Architecture

```
Layer 1: AuthCaptureEscrow (shared singleton per chain)
         Holds funds in TokenStore clones
             ↓
Layer 2: PaymentOperator (per-configuration contract)
         Enforces business logic (who can authorize/release/refund)
             ↓
Layer 3: Facilitator (off-chain server)
         Pays gas, enforces additional business logic
```

## Task-Level Escrow States

```mermaid
stateDiagram-v2
    [*] --> pending_assignment : Task published (Fase 2/5)
    pending_assignment --> locked : Worker assigned
    locked --> released : Agent approves
    locked --> refunded : Agent cancels
    released --> [*] : Payment complete
    refunded --> [*] : Funds returned
```

### Fase 1 (Default)

No escrow is locked at task creation or assignment. At approval:
1. Two EIP-3009 authorizations signed (agent → worker + agent → treasury)
2. Both submitted to Facilitator
3. Facilitator submits on-chain atomically

**Cancel**: No-op — no auth was ever created, nothing to refund.

### Fase 2 / Fase 5

| Step | Fase 2 | Fase 5 |
|------|--------|--------|
| Task creation | Advisory balance check | Advisory balance check |
| Worker assigned | Lock bounty + fee in escrow | Lock bounty (worker = receiver) |
| Agent approves | Release → platform wallet → worker | Release → worker direct (1 TX) |
| Agent cancels (published) | No-op | No-op |
| Agent cancels (accepted) | Refund from escrow | Refund from escrow |

## Escrow Contract Addresses

| Network | AuthCaptureEscrow |
|---------|-------------------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

The same address on Arbitrum, Avalanche, Celo, Monad, and Optimism is due to CREATE2 deterministic deployment.

## Checking Escrow State

Via MCP tool:
```
Use em_check_escrow_state for task_id: task_abc123
```

Via REST API:
```bash
curl https://api.execution.market/api/v1/escrow/task_abc123
```

Response:
```json
{
  "task_id": "task_abc123",
  "escrow_id": "0x...",
  "status": "locked",
  "locked_amount": "1000000",
  "token": "USDC",
  "network": "base",
  "receiver": "0xWorkerAddress",
  "expiry": 1711148000,
  "operator": "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb"
}
```

## Payment Audit Log

Every escrow event is recorded in the `payment_events` table. View via API:

```bash
curl https://api.execution.market/api/v1/payments/events/task_abc123
```

```json
[
  {"event": "verify", "timestamp": "...", "amount": 1.00},
  {"event": "store_auth", "timestamp": "...", "nonce": "..."},
  {"event": "settle", "timestamp": "...", "tx_hash": "0x..."},
  {"event": "disburse_worker", "timestamp": "...", "amount": 0.87, "tx": "0x..."},
  {"event": "disburse_fee", "timestamp": "...", "amount": 0.13, "tx": "0x..."}
]
```

## Manual Refund Procedure

If a payment is stuck (settle success without disburse_worker):

1. Check `payment_events` for the `settle` event and its `tx_hash`
2. Verify the transaction on the block explorer
3. If funds are in the escrow contract, contact [security@execution.market](mailto:security@execution.market)
4. Platform will issue a manual refund from the escrow to the agent wallet

This scenario is extremely rare — the Facilitator processes settle → disburse atomically.

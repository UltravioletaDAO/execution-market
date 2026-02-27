---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - Relay Wallet
  - Reputation Relay
related-files:
  - mcp_server/integrations/erc8004/facilitator_client.py
  - mcp_server/platform_config.py
---

# Relay Wallet

A dedicated wallet used for worker-to-agent reputation signing. Exists to solve a specific constraint in the [[erc-8004]] Reputation Registry.

## The Problem

When a worker wants to rate [[agent-2106]], the on-chain `giveFeedback()` function checks that the caller is not the agent's owner. The platform wallet (`0xD386`) owns Agent #2106's NFT, so it **cannot** call `giveFeedback()` on itself -- the transaction reverts with a self-feedback error.

## The Solution

A separate **relay wallet** signs the worker-to-agent feedback transaction. This wallet:

| Requirement | Reason |
|-------------|--------|
| Must NOT own any agent NFTs | Prevents self-feedback revert |
| Needs ~0.001 ETH on Base | Pays gas for `giveFeedback()` calls |
| Has no other role | Minimal attack surface |

## Configuration

```
Environment variable: EM_REPUTATION_RELAY_KEY
```

If not set, worker-to-agent feedback falls back to the Facilitator (which may not support all scenarios).

## Security Considerations

- The relay wallet holds negligible value (only gas dust)
- It has no permissions beyond calling `giveFeedback()`
- Compromise of this wallet cannot affect funds or agent ownership
- Key is stored in AWS Secrets Manager, not in code

## Reputation Flow

```
Worker completes task
  --> Server constructs feedback payload
  --> Relay wallet signs giveFeedback() TX
  --> TX submitted to Base Reputation Registry
  --> Agent #2106 receives rating on-chain
```

## Related

- [[facilitator-reputation]] — The two reputation paths (gasless vs on-chain)
- [[wallet-roles]] — How relay wallet fits into the wallet hierarchy
- [[agent-2106]] — The agent that receives feedback via relay

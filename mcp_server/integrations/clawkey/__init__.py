"""ClawKey KYA (Know Your Agent) integration for Execution Market.

Public-read REST against api.clawkey.ai/v1. Used as an additive trust signal
on agent profiles — *never* blocks task creation or application. Mirrors the
architectural intent of ERC-8004 reputation: signal, not gate.

Two lookup paths:
  - by Ed25519 public key (base58)
  - by device id

Both return `{registered, verified, humanId, registeredAt}`. No API key needed.
"""

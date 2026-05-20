"""Solana-specific integrations for Execution Market.

Owns:
  - `balance`: read-only SPL token balance probe over JSON-RPC (Phase 4.7
    balance-gating for the MoonPay on-ramp)
  - `pay_shell_client`: thin control-plane HTTP client for pay.sh (Phase 2.2)

NOTE: the data-plane / payment processing for direct Solana SPL transfers
lives in `integrations.x402.solana_handler` for historical reasons (Fase 1
predates the MPP integration). When we add MPP session-aware routes the
dispatcher reaches into `pay_shell_client` from here.
"""

# Changelog — `execution-market-cli`

All notable changes to the `em` CLI are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-05-28

### Breaking
- **Removed API-key authentication.** The backend disabled API-key auth
  (`EM_API_KEYS_ENABLED=false`) with skill v10.0.0, so v0.x clients
  returned HTTP 403 on every request. All requests now sign with the
  user's EVM wallet via the Open Wallet Standard (ERC-8128, RFC 9421
  HTTP Message Signatures).
- **`em login` no longer accepts `--api-key`.** Use
  `em login [--wallet-name N] [--wallet-address 0x...] [--chain-id 8453]`.
  Without flags, the command auto-detects wallets via `ows wallet list`
  and prompts for selection.
- **`Profile.api_key` removed from `~/.execution-market/config.json`.**
  Legacy configs load fine (the field is silently dropped); users re-run
  `em login` to bind a wallet.
- **`EM_API_KEY` / `EM_API_KEY_{PROFILE}` env vars removed.** Use
  `EM_WALLET_NAME` + `EM_WALLET_ADDRESS` (+ optional `EM_CHAIN_ID`).

### Added
- `em register` semantics now flow through `EMAPIClient.register_identity()`
  for gasless ERC-8004 identity registration via the Facilitator.
- Deterministic idempotency: `em tasks create` sends
  `X-Idempotency-Key = task_fingerprint(body)` so a retry after a timeout
  returns the original task instead of duplicating.
- Auto-detection of OWS wallets at login time (no manual address paste
  when only one wallet exists).
- Dependency on `execution-market>=1.0.0` for the canonical signer.

### Internal
- `EMAPIClient` now owns an `OwsEM8128Client` (composition) and bridges
  async↔sync with `asyncio.run` per request. The CLI remains synchronous
  for `click`'s sake.
- `commands/auth.py` (`em auth login`) and `em.py` (`em login`) both updated
  to the new flow; they produce identical profiles.

### Migration
See [`docs/MIGRATION_v1.md`](../docs/MIGRATION_v1.md) for before/after
examples.

## [0.1.0]
- Initial release (never functioned in production after the backend
  disabled API-key auth).

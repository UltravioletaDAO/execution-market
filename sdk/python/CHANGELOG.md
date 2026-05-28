# Changelog — `execution-market` Python SDK

All notable changes to the `execution-market` package are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-05-28

### Breaking
- **Removed API-key authentication.** All requests now sign with the
  user's EVM wallet via the Open Wallet Standard (ERC-8128). The backend
  disabled API-key auth (`EM_API_KEYS_ENABLED=false`) with skill v10.0.0,
  so v0.x clients returned HTTP 403 in production.
- **`ExecutionMarketClient.__init__` signature changed:** takes
  `wallet_name` + `wallet_address` (+ optional `chain_id`, `base_url`,
  `timeout`) instead of `api_key`. Passing `api_key=` now raises `TypeError`.
- **`EM_API_KEY` env var removed.** Use `EM_WALLET_NAME` +
  `EM_WALLET_ADDRESS` if you need env-driven config.

### Added
- **`OwsEM8128Client` (in `execution_market._signer`, re-exported from
  the top level).** The canonical Python signer: shells out to `ows sign
  message` via `subprocess` so the private key never enters the Python
  process. Implements RFC 9421 HTTP Message Signatures with the wire
  format documented in `dashboard/public/skill.md` STEP 1c Option A.
- **`task_fingerprint(body)` helper.** Deterministic SHA-256 of identity-
  defining fields for use as `X-Idempotency-Key`. `create_task()` now
  uses this — a retry after a timeout returns the original task, not a
  duplicate. (v0.x used `uuid4()`, which defeated server-side dedupe.)
- **`with_backoff(fn, ...)` helper.** Exponential backoff + jitter for
  429 / transient 5xx. `wait_for_completion()` now wraps polling in this.
- **`OwsSignError` exception** for failures in the OWS subprocess (CLI
  not installed, vault locked, returned wrong signature length).
- **18 unit tests for the signer** + **8 unit tests for the client**
  (mocked subprocess / httpx — no network or `ows` calls). `pytest`
  green.

### Changed
- `AuthenticationError`'s message now references "wallet signing"
  instead of "API key" (class name unchanged for `except` compatibility).
- `Development Status` classifier moved to `5 - Production/Stable`.

### Migration
See [`docs/MIGRATION_v1.md`](../../docs/MIGRATION_v1.md) for before/after
examples and gotchas.

## [0.1.0]
- Initial release (never functioned in production after the backend
  disabled API-key auth).

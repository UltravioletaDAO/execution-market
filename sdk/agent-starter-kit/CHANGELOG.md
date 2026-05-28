# Changelog — `execution-market-agent-starter-kit`

All notable changes to the agent starter kit are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-05-28

### Breaking
- **Removed API-key authentication.** Now uses the canonical
  `OwsEM8128Client` from the `execution-market` package (ERC-8128 wallet
  signing via OWS).
- **All public methods on `ExecutionMarketClient` are now `async`.** The
  kit composes the async signer directly and doesn't add a sync bridge —
  callers should `await` or wrap with `asyncio.run(...)`. Use the
  `execution-market` Python SDK if you need a sync surface.
- **Constructor signature:** `ExecutionMarketClient(wallet_name,
  wallet_address, chain_id=8453, api_url=...)` instead of `api_key=...`.
- **`EM_API_KEY` env var removed.**

### Fixed
- **API paths now include `/api/v1/`** prefix. The previous kit hit
  `/tasks`, `/submissions/{id}/approve`, etc., which 404'd against the
  current backend even before the auth change.

### Added
- Deterministic `X-Idempotency-Key` on `create_task()` via
  `task_fingerprint()`.
- `with_backoff()` jitter retry around every signed call (not just
  `wait_for_completion`).
- `pyproject.toml` (the kit was previously not packaged); depends on
  `execution-market>=1.0.0` for the signer.

### Migration
See [`docs/MIGRATION_v1.md`](../../docs/MIGRATION_v1.md).

## [0.x] — pre-1.0.0
- Illustrative kit with API-key auth. Never functioned in production
  after the backend disabled API-key auth.

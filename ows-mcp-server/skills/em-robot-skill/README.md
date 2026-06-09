---
date: 2026-05-19
tags:
  - type/guide
  - domain/agents
  - chain/solana
  - status/active
aliases:
  - em-robot-skill
  - robot-skill-readme
related-files:
  - ows-mcp-server/skills/em-robot-skill/skill.md
  - ows-mcp-server/src/skills/em-robot-skill/index.ts
  - scripts/demo/robot-sim.ts
status: active
---

# em-robot-skill — v0.1.0

> Universal worker skill for Execution Market on Solana. Five MCP tools that
> take an OWS Solana wallet from "task assigned" to "settlement complete" via
> the **pay.sh MPP proxy**, with the robot wallet keeping 0 SOL throughout
> (server-side fee sponsorship per `[[SOLANA_MPP_specs_pr201]]` §3.2).

**Phase 3 deliverable** of `[[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]]`. See the
companion manifest in [skill.md](skill.md) for the canonical metadata that
`ows skill validate` reads.

## Status

| Field | Value |
|-------|-------|
| version | `0.1.0` |
| stability | `alpha` |
| chain | `solana` |
| payment scheme | `x402-mpp` |
| MCP server host | `ows-mcp-server` (this repo) |
| Bundled simulator | `scripts/demo/robot-sim.ts` |
| Tracked by | Phase 3 of `MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO.md` |

## What this skill is for

Any worker that needs to accept an EM task, do real work paid by an MPP
payment channel, and have the channel settled atomically (87 % worker /
13 % treasury) at the end. Concretely, the demo flow is:

1. An external agent publishes a Solana-paid task on `execution.market`.
2. The robot (running this skill via any MCP client) applies via
   `robot_accept_task`.
3. The publisher assigns the robot. EM mints an `MPPChannelBinding` row
   linking the task to the upcoming pay.sh session.
4. The robot opens the channel (`robot_open_payshell_session`) — pay.sh
   responds with a 402 challenge, the robot signs `OpenChannelAuth`
   with its Ed25519 OWS key, pay.sh opens the PDA escrow paying the
   SOL gas itself.
5. The robot does the work (mock barcode scan in this skill — replace with
   real onboard CV later) and emits a voucher every second
   (`robot_sign_voucher_tick`). Each voucher carries the new cumulative
   spent so far.
6. Work finished. The robot calls `robot_close_payshell_session`, pay.sh
   runs `settleAndFinalize + distribute` atomically and refunds the
   unused cap to the original payer.

Everything else (task completion event on EM, reputation updates, dashboard
SSE taxímetro stop) is handled by the EM backend listening on
`MPPChannelBinding` updates (Phase 2.5.1).

## Tools (5)

| Tool | Phase | Purpose |
|------|-------|---------|
| `robot_accept_task` | 3.2 | Apply to a published task via ERC-8128 wallet-signed POST |
| `robot_scan_barcode` | 3.3 | Submit a decoded barcode/QR payload as evidence (caller pre-decodes) |
| `robot_open_payshell_session` | 3.4 | x402 challenge dance against pay.sh, get `channelId` back |
| `robot_sign_voucher_tick` | 3.5 | Sign one 48-byte Borsh voucher and POST `/_sessions/{id}/voucher` |
| `robot_close_payshell_session` | 3.6 | Close the channel, receive settlement tx hash |

The voucher tool is **single-tick** by design — the caller drives cadence.
A server-side loop would hold an MCP request open for the entire work
duration, which the protocol does not support cleanly. The bundled
`scripts/demo/robot-sim.ts` shows the canonical caller-side loop.

## Installation

The skill is built into the `@execution-market/ows-mcp-server` package; if you
already have that server installed there is nothing extra to install. The
five tools register themselves automatically alongside the 10 core
`ows_*` tools.

```bash
git clone https://github.com/Felipe-Tabares/execution-market.git
cd execution-market/ows-mcp-server
npm install         # installs bs58 + @solana/web3.js needed by the skill
npm start           # boots stdio MCP transport — 15 tools available
```

Verify the skill registered:

```bash
node --input-type=module -e \
  "import('@modelcontextprotocol/sdk/client/index.js').then(m=>console.log(Object.keys(m)))"
# (or any MCP client) — call tools/list, expect the 5 robot_* tools.
```

For the standalone simulator (no MCP transport — handy for CI / dry-runs):

```bash
cd ../scripts
npm install
npm run demo:robot -- --task-id <uuid> --wallet em-robot --duration 30
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EM_PAYSHELL_URL` | **yes** | – | pay.sh proxy base URL. Local dev: `http://127.0.0.1:7081`. Prod: `https://api.execution.market`. |
| `EM_API_BASE` | yes (for REST routes) | falls back to `EM_PAYSHELL_URL` | EM REST API base. In prod this is the same host as pay.sh. |
| `EM_ROBOT_WALLET_NAME` | yes | – | OWS wallet name created via `ows_create_wallet`. Must have a `solana:` account. |
| `EM_ROBOT_WALLET_PASSPHRASE` | no | – | Vault passphrase if the wallet was created with one. |
| `EM_ROBOT_SKILL_ALLOW_SOL` | no | unset | Set to `1` to bypass the strict 0-SOL cinematic assertion. Use only for non-cinematic dev flows. |
| `EM_ROBOT_SKILL_DEBUG` | no | unset | Set to `1` for verbose JSON traces on stderr. Never leak this in production — it logs request bodies. |
| `SOLANA_RPC_URL` | no | `https://api.mainnet-beta.solana.com` | RPC used for the 0-SOL balance precheck only. Use a private QuikNode URL for staging. |

Wallet keys never appear in env. The OWS vault lives at `~/.ows/wallets/`
encrypted with AES-256-GCM. The skill calls `ows.signMessage(...)` which
decrypts in-memory, signs, and wipes — same pattern as the core
`ows_sign_*` tools.

## Examples

### 1. End-to-end via the standalone simulator

The fastest way to validate everything works. Drives the same wire shapes
as the MCP tools but bypasses the MCP transport so it runs from any CLI.

```bash
export EM_PAYSHELL_URL=http://127.0.0.1:7081
export EM_API_BASE=http://127.0.0.1:8080

cd scripts
npm run demo:robot -- \
  --task-id 8b1d9e1d-9b5b-4c5b-8a1a-4f4d6c8e7a2b \
  --wallet em-robot \
  --duration 30 \
  --vouchers-per-sec 1 \
  --rate-uusdc-per-sec 1000
```

Successful output ends with a JSON summary on stdout — pipe to `jq` if you
want to extract just the settlement tx:

```bash
npm run demo:robot -- ... | jq -r .settlement.tx_hash
```

### 2. Via an MCP client (Claude Code, Cursor, etc.)

After `npm start` in `ows-mcp-server/`, point your MCP client at the
server's stdio transport. The five robot tools appear in `tools/list`.
Typical invocation order from a host agent:

```javascript
// (1) Apply
await client.callTool("robot_accept_task", {
  wallet: "em-robot",
  task_id: "8b1d9e1d-…",
});

// (2) Evidence (optional in this demo)
await client.callTool("robot_scan_barcode", {
  wallet: "em-robot",
  task_id: "8b1d9e1d-…",
  payload: "PRODUCT-SKU-12345",
});

// (3) Open MPP session
const open = await client.callTool("robot_open_payshell_session", {
  wallet: "em-robot",
  task_id: "8b1d9e1d-…",
});
const channelId = JSON.parse(open.content[0].text).channel_id;

// (4) Voucher loop — host owns cadence
let cumulative = 0n;
for (let i = 0; i < 30; i++) {
  cumulative += 1000n;
  await client.callTool("robot_sign_voucher_tick", {
    wallet: "em-robot",
    channel_id: channelId,
    cumulative_micro_usdc: cumulative.toString(),
  });
  await new Promise((r) => setTimeout(r, 1000));
}

// (5) Close
await client.callTool("robot_close_payshell_session", {
  wallet: "em-robot",
  channel_id: channelId,
});
```

### 3. Operator inspection

If a session misbehaves in production, the simulator is the fastest way to
isolate which hop is wrong. Run it with `--debug` against staging:

```bash
EM_ROBOT_SKILL_DEBUG=1 npm run demo:robot -- \
  --task-id <uuid> \
  --wallet em-robot \
  --proxy https://api.execution.market \
  --api   https://api.execution.market \
  --duration 5 \
  --debug
```

That writes per-hop request/response JSON to stderr while the final JSON
summary still goes to stdout — pipe stderr to a file and inspect the
exact request that was rejected. See [[payshell-ops]] for the
escalation path beyond client-side inspection.

## Differences vs the original Phase 3 plan (pre-D-15)

The plan as originally written had a **TypeScript sidecar** that this skill
would talk to directly. After **D-15** (Solana Foundation `pay.sh` adoption
on 2026-05-12), the sidecar was retired. What that means for you if you
arrived from the pre-D-15 docs:

| Old design | Current design |
|------------|----------------|
| Robot → custom TS sidecar → on-chain | Robot → pay.sh proxy → on-chain |
| Custom voucher envelope | Canonical 48-byte Borsh voucher per spec §4 |
| EM-managed fee-payer keypair | pay.sh embedded facilitator handles fee sponsorship |
| Separate `sidecar/` directory in this repo | No sidecar directory; everything goes through `EM_PAYSHELL_URL` |
| Per-tool retry/backoff baked in | Caller-owned cadence — the skill is a single tick |

The `skill.md` manifest already documents this in the "Differences vs the
original Phase 3 plan" section; this README mirrors it so a quick `cat
README.md` is enough to orient a new contributor without opening the
master plan.

## Idempotency & retry policy

Each tool's idempotency contract is documented in [skill.md](skill.md) but
to summarise:

- `robot_accept_task` — re-applying with the same wallet returns the
  existing application row (no 409).
- `robot_open_payshell_session` — pay.sh returns the existing `channelId`
  if a session for `(task, payer, payee)` is already open. The skill
  treats this as success and surfaces `already_open: true`.
- `robot_sign_voucher_tick` — pay.sh dedupes by `(channelId, cumulative)`.
  Sending the same cumulative twice is a no-op. A **regression** (lower
  cumulative than already accepted) is a 409 and the skill surfaces it
  so the caller can fix its counter.
- `robot_close_payshell_session` — calling twice yields the same tx hash.
  The skill flips `isError` to `false` on 409 so a host agent's retry
  loop can finish cleanly.

## Validation matrix (Phase 3 exit criteria)

| Check | How |
|-------|-----|
| Manifest parses | `ows skill validate em-robot-skill` |
| All 5 tools registered | MCP `tools/list` returns names beginning with `robot_*` |
| 30-second voucher loop | `npm run demo:robot -- ... --duration 30` exits 0 |
| Robot wallet stays 0 SOL | `assertCinematicBalance()` runs at start; final `final_robot_lamports` in JSON is `0` |
| Settlement tx visible on Surfpool / Solscan | Use the `settlement.tx_hash` from the JSON summary |

## See also

- [[surfpool-payshell-dev-env]] — local dev setup for pay.sh + Surfpool
- [[payshell-ops]] — production operations runbook
- [[mpp-scenarios-runbook]] — A/B/C/D worker scenarios this skill plugs into
- [[task-channel-binding]] — how EM mirrors pay.sh settle events into task state
- [[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]] — full master plan that produced this skill

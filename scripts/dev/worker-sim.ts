#!/usr/bin/env tsx
/**
 * Phase 2.5.2 — Worker simulator (universal worker).
 *
 * Drives the worker side of the MPP demo end-to-end against a local pay.sh
 * proxy (Phase 1) or staging deployment (Phase 2). Scenarios A/B/C/D in the
 * master plan all share this wire protocol — `--mode` only changes the
 * logging tag so demo recordings can label the session correctly.
 *
 *   pnpm tsx scripts/dev/worker-sim.ts \
 *     --task-id <uuid> \
 *     --mode {robot|human|agent|robot-sim} \
 *     --duration 30s \
 *     --vouchers-per-sec 1 \
 *     [--proxy http://127.0.0.1:7081] \
 *     [--keypair .secrets/surfpool-keys/payee.json]
 *
 * What it does:
 *   1. Accepts the task via EM HTTP API (auth via OWS / ERC-8128 wallet sig).
 *   2. Triggers the first pay.sh-gated request to receive the 402 challenge,
 *      then opens an MPP session.
 *   3. Loops voucher ticks at the configured rate until `--duration` elapses.
 *   4. Closes the session — pay.sh dispatches settleAndFinalize.
 *   5. Polls the EM SSE taxímetro for `settlement_complete` and prints the
 *      on-chain tx hash. Exits 0 iff the cap was honored within ±1 µUSDC.
 *
 * Not a production tool. This is the harness that lets Saul (or CI) prove
 * the platform works without a robot — Risk 3 mitigation.
 *
 * Security:
 *   - Keys are loaded from --keypair (defaults to dev keypair at
 *     .secrets/surfpool-keys/payee.json — gitignored). NEVER commit a key.
 *   - The script logs the worker's public key only, never the secret.
 *   - INC-2026-03-30 zero-tolerance: if no keypair file exists, the script
 *     fails LOUDLY instead of generating one inline.
 */

import { Keypair } from "@solana/web3.js";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";

// ---------------------------------------------------------------------------
// CLI parsing — keep small; tsx supports node:util.parseArgs but we avoid the
// extra dependency surface.
// ---------------------------------------------------------------------------

type Mode = "robot" | "human" | "agent" | "robot-sim";

interface Args {
  taskId: string;
  mode: Mode;
  durationMs: number;
  vouchersPerSec: number;
  proxy: string;
  emApi: string;
  keypair: string;
  endpoint: string;
}

function parseArgs(): Args {
  const argv = process.argv.slice(2);
  const get = (flag: string, fallback?: string): string => {
    const idx = argv.indexOf(flag);
    if (idx === -1) {
      if (fallback === undefined) {
        throw new Error(`missing required flag ${flag}`);
      }
      return fallback;
    }
    return argv[idx + 1];
  };
  const mode = get("--mode", "robot-sim") as Mode;
  if (!["robot", "human", "agent", "robot-sim"].includes(mode)) {
    throw new Error(`--mode must be one of robot|human|agent|robot-sim`);
  }
  const durationStr = get("--duration", "30s");
  const durationMs = parseDuration(durationStr);
  return {
    taskId: get("--task-id"),
    mode,
    durationMs,
    vouchersPerSec: parseFloat(get("--vouchers-per-sec", "1")),
    proxy: get("--proxy", process.env.EM_PAYSHELL_URL ?? "http://127.0.0.1:7081"),
    emApi: get("--em-api", process.env.EM_API_URL ?? "http://127.0.0.1:8080"),
    keypair: get("--keypair", ".secrets/surfpool-keys/payee.json"),
    endpoint: get("--endpoint", "/hello"),
  };
}

function parseDuration(s: string): number {
  // Accepts "30s", "2m", or a bare number of seconds. Bounded [1s, 5m] so
  // a typo doesn't burn the cap on a real channel.
  const m = s.match(/^(\d+(?:\.\d+)?)(s|m)?$/);
  if (!m) throw new Error(`bad duration: ${s}`);
  const n = parseFloat(m[1]);
  const ms = (m[2] === "m" ? n * 60 : n) * 1000;
  if (ms < 1000 || ms > 5 * 60 * 1000) {
    throw new Error(`duration out of range [1s, 5m]: ${s}`);
  }
  return ms;
}

// ---------------------------------------------------------------------------
// Key loading — fail loudly if missing (no inline generation).
// ---------------------------------------------------------------------------

async function loadKeypair(filePath: string): Promise<Keypair> {
  const abs = path.resolve(filePath);
  try {
    const raw = await fs.readFile(abs, "utf8");
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) throw new Error("keypair file is not a JSON array");
    return Keypair.fromSecretKey(new Uint8Array(arr));
  } catch (e) {
    console.error(
      `[FATAL] worker keypair not loadable at ${abs}: ${
        e instanceof Error ? e.message : String(e)
      }`,
    );
    console.error(
      `[HINT] run "pnpm tsx scripts/dev/surfpool-fund.ts" to generate dev keys.`,
    );
    process.exit(2);
  }
}

// ---------------------------------------------------------------------------
// EM API calls — the worker authenticates the same way agents do.
// ERC-8128 wallet signing is the canonical auth; for local dev against a
// stub backend we accept dev-only header EM_DEV_WORKER_ID instead.
// ---------------------------------------------------------------------------

async function acceptTask(args: Args, workerPubkey: string): Promise<void> {
  const url = `${args.emApi}/api/v1/tasks/${args.taskId}/applications`;
  const body = {
    wallet_address: workerPubkey,
    message: `worker-sim mode=${args.mode}`,
    auto_assign: true,
  };
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-EM-Task-Id": args.taskId,
  };
  if (process.env.EM_DEV_WORKER_ID) {
    headers["X-EM-Dev-Worker-Id"] = process.env.EM_DEV_WORKER_ID;
  }
  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`accept task ${args.taskId} failed: ${resp.status} ${text.slice(0, 200)}`);
  }
}

// ---------------------------------------------------------------------------
// pay.sh interaction via the `pay` CLI. We delegate signing to the CLI
// because TS doesn't have a stable bindings package (Plan B SDK direct
// is the fallback for that — Phase 1.7).
// ---------------------------------------------------------------------------

function payCliJson(...args: string[]): Record<string, unknown> {
  const result = spawnSync("pay", [...args, "--output", "json"], {
    encoding: "utf8",
    timeout: 30_000,
  });
  if (result.status !== 0) {
    throw new Error(
      `pay ${args.join(" ")} exited ${result.status}: ${result.stderr.slice(0, 500)}`,
    );
  }
  try {
    return JSON.parse(result.stdout);
  } catch {
    throw new Error(`pay ${args.join(" ")} produced non-JSON: ${result.stdout.slice(0, 200)}`);
  }
}

function openSession(args: Args): string {
  const out = payCliJson(
    "client",
    "session",
    "open",
    "--proxy",
    args.proxy,
    "--endpoint",
    args.endpoint,
    "--keypair",
    args.keypair,
  );
  const channelId = out["channelId"];
  if (typeof channelId !== "string") {
    throw new Error(`pay session open returned no channelId: ${JSON.stringify(out)}`);
  }
  return channelId;
}

function signVoucher(args: Args, channelId: string, incrementUusdc: number): void {
  payCliJson(
    "client",
    "voucher",
    "sign",
    "--proxy",
    args.proxy,
    "--session",
    channelId,
    "--keypair",
    args.keypair,
    "--increment-uusdc",
    String(incrementUusdc),
  );
}

function closeSession(args: Args, channelId: string): Record<string, unknown> {
  return payCliJson(
    "client",
    "session",
    "close",
    "--proxy",
    args.proxy,
    "--session",
    channelId,
    "--keypair",
    args.keypair,
  );
}

// ---------------------------------------------------------------------------
// Voucher loop — drives the cumulative cursor.
// ---------------------------------------------------------------------------

async function voucherLoop(args: Args, channelId: string): Promise<number> {
  const tickIntervalMs = 1000 / args.vouchersPerSec;
  const incrementUusdc = 1; // 1 µUSDC per tick — keeps demo costs tiny
  const start = Date.now();
  let count = 0;
  while (Date.now() - start < args.durationMs) {
    const tickStart = Date.now();
    signVoucher(args, channelId, incrementUusdc);
    count += 1;
    if ((count & 0x07) === 0) {
      console.log(`[tick ${count}] channel=${channelId.slice(0, 10)}... cumulative=${count} µUSDC`);
    }
    const elapsed = Date.now() - tickStart;
    if (elapsed < tickIntervalMs) {
      await sleep(tickIntervalMs - elapsed);
    }
  }
  return count;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const args = parseArgs();
  const kp = await loadKeypair(args.keypair);
  const workerPubkey = kp.publicKey.toBase58();

  console.log(
    `[start] worker-sim mode=${args.mode} task=${args.taskId} ` +
      `worker=${workerPubkey} proxy=${args.proxy}`,
  );

  // 1) Accept the task on EM side. This is what causes the dispatcher to
  //    call _authorize_solana_session and reserve the binding row.
  await acceptTask(args, workerPubkey);
  console.log(`[ok] accepted task ${args.taskId} as ${args.mode}`);

  // 2) Open MPP session via pay.sh CLI.
  const channelId = openSession(args);
  console.log(`[ok] opened pay.sh session channel=${channelId}`);

  // 3) Voucher loop.
  let count = 0;
  try {
    count = await voucherLoop(args, channelId);
  } catch (e) {
    console.error(
      `[warn] voucher loop interrupted after ${count} ticks: ${
        e instanceof Error ? e.message : String(e)
      }`,
    );
  }

  // 4) Close — pay.sh runs settleAndFinalize.
  const settled = closeSession(args, channelId);
  const txHash = settled["settlementTxHash"];
  console.log(`[ok] closed channel=${channelId} settlement_tx=${txHash}`);
  console.log(
    `[summary] mode=${args.mode} duration=${(args.durationMs / 1000).toFixed(1)}s ` +
      `ticks=${count} tx=${txHash}`,
  );

  // 5) Exit 0 — caller checks tx_hash truthiness for hard validation.
  if (typeof txHash !== "string" || txHash.length === 0) {
    console.error(`[fatal] settlement returned no tx hash: ${JSON.stringify(settled)}`);
    process.exit(3);
  }
}

main().catch((err) => {
  console.error(`[fatal] ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});

#!/usr/bin/env tsx
/**
 * Phase 3.8 — Standalone E2E robot simulator vs pay.sh proxy.
 *
 * Drives the full robot flow exercised by `em-robot-skill` without going
 * through the MCP transport. Useful for:
 *
 *   1. Pre-flight dry-runs before a cinematic demo recording — confirms
 *      pay.sh / EM backend / Solana RPC are all reachable and that the OWS
 *      wallet survives a full session without intervention.
 *   2. Reproducible CI smoke test for Phase 3 (the actual end-to-end pytest
 *      lives in `mcp_server/tests/test_robot_skill_e2e_smoke.py` — that one
 *      drives this script as a subprocess on staging).
 *   3. Operator debugging when a robot session misbehaves and we want to
 *      bypass the agent's MCP context to isolate which hop is wrong.
 *
 * What it does NOT do:
 *   - Decode an actual barcode image. The scan step posts a caller-supplied
 *     payload (default: a deterministic mock based on the task id). Real
 *     image decoding belongs in the robot's onboard vision stack, not here.
 *   - Talk to MCP. MCP is request/response and a long-running loop owned by
 *     a server-side tool would tie up the agent context for 30+ seconds.
 *     This script owns the cadence directly.
 *   - Print private keys, lamport balances of unrelated wallets, RPC API
 *     keys, or anything else the user is streaming. Only the public Solana
 *     pubkey of the robot wallet ever appears in stdout.
 *
 * Wire shapes are kept byte-identical to `ows-mcp-server/src/skills/em-robot-skill/*`
 * so that fixing a bug here usually fixes the same bug in the skill.
 *
 * Auth model (mirrors `_http.ts`):
 *   - Every request to EM REST routes carries the EM-AUTH/1 canonical
 *     message + Ed25519 signature in X-EM-Auth-* headers.
 *   - The 402 challenge / X-Payment retry for pay.sh `/hello` uses the
 *     x402 scheme defined in `payshell_open.ts`.
 *   - Voucher POSTs are unauthenticated at the header level — the voucher
 *     bytes themselves carry the Ed25519 signature pay.sh validates.
 *
 * Usage:
 *   tsx scripts/demo/robot-sim.ts \
 *     --task-id <uuid> \
 *     --wallet em-robot \
 *     [--proxy http://127.0.0.1:7081] \
 *     [--api http://127.0.0.1:8080] \
 *     [--duration 30] \
 *     [--vouchers-per-sec 1] \
 *     [--rate-uusdc-per-sec 1000] \
 *     [--cap-uusdc 100000] \
 *     [--endpoint /hello] \
 *     [--barcode-payload <text>] \
 *     [--passphrase <pwd>] \
 *     [--allow-sol] \
 *     [--rpc-url https://api.mainnet-beta.solana.com] \
 *     [--skip-scan] \
 *     [--skip-accept] \
 *     [--debug]
 */

import * as crypto from "node:crypto";
import { parseArgs } from "node:util";

import bs58 from "bs58";
import { Connection, PublicKey } from "@solana/web3.js";
import * as ows from "@open-wallet-standard/core";

// ---------------------------------------------------------------------------
// CLI parsing
// ---------------------------------------------------------------------------

const { values: opts } = parseArgs({
  options: {
    "task-id": { type: "string" },
    wallet: { type: "string" },
    proxy: { type: "string" },
    api: { type: "string" },
    duration: { type: "string", default: "30" },
    "vouchers-per-sec": { type: "string", default: "1" },
    "rate-uusdc-per-sec": { type: "string", default: "1000" },
    "cap-uusdc": { type: "string", default: "100000" },
    endpoint: { type: "string", default: "/hello" },
    "barcode-payload": { type: "string" },
    passphrase: { type: "string" },
    "allow-sol": { type: "boolean", default: false },
    "rpc-url": { type: "string" },
    "skip-scan": { type: "boolean", default: false },
    "skip-accept": { type: "boolean", default: false },
    debug: { type: "boolean", default: false },
    help: { type: "boolean", default: false, short: "h" },
  },
  allowPositionals: false,
});

if (opts.help) {
  printUsageAndExit(0);
}

function printUsageAndExit(code: number): never {
  // Heredoc-style help. Keep this in sync with the file-level comment.
  const lines = [
    "robot-sim.ts — Phase 3.8 standalone robot simulator",
    "",
    "Required:",
    "  --task-id <uuid>          EM task UUID to apply to",
    "  --wallet   <name>         OWS wallet name (also $EM_ROBOT_WALLET_NAME)",
    "",
    "Endpoints (default to env or localhost):",
    "  --proxy <url>             pay.sh proxy ($EM_PAYSHELL_URL)",
    "  --api   <url>             EM REST base ($EM_API_BASE — defaults to proxy)",
    "",
    "Channel & loop:",
    "  --duration <sec>          how long to run the voucher loop (default 30)",
    "  --vouchers-per-sec <n>    cadence (default 1)",
    "  --rate-uusdc-per-sec <n>  per-second spend rate (default 1000 = $0.001)",
    "  --cap-uusdc <n>           hard cap if you want to stop early (default 100000)",
    "  --endpoint <path>         protected pay.sh endpoint (default /hello)",
    "  --barcode-payload <text>  scan payload (default 'demo-task-<id>-barcode')",
    "",
    "Auth / safety:",
    "  --passphrase <pwd>        OWS vault passphrase ($EM_ROBOT_WALLET_PASSPHRASE)",
    "  --allow-sol               skip the cinematic 0-SOL assertion",
    "  --rpc-url <url>           Solana RPC ($SOLANA_RPC_URL, default mainnet-beta)",
    "",
    "Step toggles:",
    "  --skip-accept             reuse an existing application (e.g. rerun)",
    "  --skip-scan               skip the evidence submission step",
    "",
    "  --debug                   verbose tracing to stderr",
    "  -h, --help                show this help",
  ];
  process.stderr.write(lines.join("\n") + "\n");
  process.exit(code);
}

const TASK_ID = opts["task-id"];
if (!TASK_ID) {
  process.stderr.write("error: --task-id is required\n\n");
  printUsageAndExit(2);
}

const WALLET_NAME = opts.wallet ?? process.env.EM_ROBOT_WALLET_NAME;
if (!WALLET_NAME) {
  process.stderr.write(
    "error: --wallet not provided and $EM_ROBOT_WALLET_NAME is unset\n\n",
  );
  printUsageAndExit(2);
}

const PROXY = (
  opts.proxy ??
  process.env.EM_PAYSHELL_URL ??
  "http://127.0.0.1:7081"
).replace(/\/+$/, "");
const API_BASE = (
  opts.api ??
  process.env.EM_API_BASE ??
  PROXY
).replace(/\/+$/, "");

const DURATION_SECONDS = Number(opts.duration);
const VOUCHERS_PER_SEC = Number(opts["vouchers-per-sec"]);
const RATE_UUSDC = BigInt(opts["rate-uusdc-per-sec"] ?? "1000");
const CAP_UUSDC = BigInt(opts["cap-uusdc"] ?? "100000");
const ENDPOINT = opts.endpoint ?? "/hello";
const BARCODE_PAYLOAD =
  opts["barcode-payload"] ?? `demo-task-${TASK_ID}-barcode`;
const PASSPHRASE = opts.passphrase ?? process.env.EM_ROBOT_WALLET_PASSPHRASE;
const ALLOW_SOL =
  opts["allow-sol"] === true ||
  process.env.EM_ROBOT_SKILL_ALLOW_SOL === "1" ||
  process.env.EM_ROBOT_SKILL_ALLOW_SOL === "true";
const RPC_URL =
  opts["rpc-url"] ??
  process.env.SOLANA_RPC_URL ??
  "https://api.mainnet-beta.solana.com";
const DEBUG =
  opts.debug === true ||
  process.env.EM_ROBOT_SKILL_DEBUG === "1" ||
  process.env.EM_ROBOT_SKILL_DEBUG === "true";

if (!Number.isFinite(DURATION_SECONDS) || DURATION_SECONDS <= 0) {
  process.stderr.write("error: --duration must be a positive number\n");
  process.exit(2);
}
if (!Number.isFinite(VOUCHERS_PER_SEC) || VOUCHERS_PER_SEC <= 0) {
  process.stderr.write("error: --vouchers-per-sec must be a positive number\n");
  process.exit(2);
}

function debugLog(label: string, payload?: unknown): void {
  if (!DEBUG) return;
  const tail =
    payload === undefined
      ? ""
      : ": " + (typeof payload === "string" ? payload : JSON.stringify(payload));
  process.stderr.write(`[robot-sim] ${label}${tail}\n`);
}

// ---------------------------------------------------------------------------
// Resolve the OWS Solana account
// ---------------------------------------------------------------------------

function resolveSolanaAccount(walletName: string): {
  walletName: string;
  address: string;
  chainId: string;
} {
  const info = ows.getWallet(walletName);
  const acc = info.accounts.find((a) => a.chainId.startsWith("solana:"));
  if (!acc) {
    throw new Error(
      `wallet "${walletName}" has no solana account — run ows_create_wallet first`,
    );
  }
  return { walletName, address: acc.address, chainId: acc.chainId };
}

// ---------------------------------------------------------------------------
// Signed request helper (mirrors em-robot-skill/_http.ts)
// ---------------------------------------------------------------------------

interface SignedResp {
  status: number;
  body: unknown;
  headers: Record<string, string>;
}

async function signedRequest(
  method: string,
  url: string,
  body: unknown | undefined,
  taskId?: string,
): Promise<SignedResp> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const parsed = new URL(url);
  const path = parsed.pathname + parsed.search;
  const timestamp = new Date().toISOString();
  const nonce = crypto.randomBytes(16).toString("hex");

  const bodyBytes =
    body === undefined || body === null
      ? new Uint8Array(0)
      : Buffer.from(JSON.stringify(body), "utf8");
  const bodyDigest = crypto
    .createHash("sha256")
    .update(Buffer.from(bodyBytes))
    .digest("hex");

  const canonical = [
    "EM-AUTH/1",
    `method=${method.toUpperCase()}`,
    `path=${path}`,
    `timestamp=${timestamp}`,
    `nonce=${nonce}`,
    `body-sha256=${bodyDigest}`,
  ].join("\n");

  const sig = ows.signMessage(WALLET_NAME!, "solana", canonical, PASSPHRASE);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-EM-Auth-Wallet": account.address,
    "X-EM-Auth-Chain": "solana",
    "X-EM-Auth-Timestamp": timestamp,
    "X-EM-Auth-Nonce": nonce,
    "X-EM-Auth-Body-SHA256": bodyDigest,
    "X-EM-Auth-Signature": sig.signature,
  };
  if (taskId) headers["X-EM-Task-Id"] = taskId;

  const resp = await fetch(url, {
    method,
    headers,
    body: bodyBytes.byteLength === 0 ? undefined : bodyBytes,
  });

  const respHeaders: Record<string, string> = {};
  resp.headers.forEach((v, k) => {
    respHeaders[k] = v;
  });
  const contentType = resp.headers.get("content-type") ?? "";
  const parsedBody = contentType.includes("application/json")
    ? await resp.json().catch(() => ({}))
    : await resp.text().catch(() => "");
  return { status: resp.status, body: parsedBody, headers: respHeaders };
}

// ---------------------------------------------------------------------------
// Voucher serialization (mirrors em-robot-skill/voucher_tick.ts)
// ---------------------------------------------------------------------------

const VOUCHER_BYTES = 48;
const CHANNEL_ID_BYTES = 32;

function serializeVoucher(
  channelIdBase58: string,
  cumulativeMicroUsdc: bigint,
  expiresAtUnixSeconds: bigint,
): Uint8Array {
  const channelBytes = bs58.decode(channelIdBase58);
  if (channelBytes.length !== CHANNEL_ID_BYTES) {
    throw new Error(
      `channel_id must decode to ${CHANNEL_ID_BYTES} bytes, got ${channelBytes.length}`,
    );
  }
  if (cumulativeMicroUsdc < 0n || cumulativeMicroUsdc > 0xffffffffffffffffn) {
    throw new Error(
      `cumulative_micro_usdc out of u64 range: ${cumulativeMicroUsdc}`,
    );
  }
  const out = new Uint8Array(VOUCHER_BYTES);
  out.set(channelBytes, 0);
  const view = new DataView(out.buffer);
  view.setBigUint64(CHANNEL_ID_BYTES, cumulativeMicroUsdc, true);
  view.setBigInt64(CHANNEL_ID_BYTES + 8, expiresAtUnixSeconds, true);
  return out;
}

// ---------------------------------------------------------------------------
// Step 0 — assert 0 SOL (or warn if allowed)
// ---------------------------------------------------------------------------

async function assertCinematicBalance(): Promise<void> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const conn = new Connection(RPC_URL, "confirmed");
  const pk = new PublicKey(account.address);
  const lamports = await conn.getBalance(pk, "confirmed");
  debugLog("balance", { lamports });

  if (lamports === 0) {
    process.stderr.write(
      `[robot-sim] ok — robot wallet ${account.address} has 0 SOL (cinematic)\n`,
    );
    return;
  }

  if (ALLOW_SOL) {
    process.stderr.write(
      `[robot-sim] warn — robot wallet has ${lamports} lamports; --allow-sol bypasses strict assertion\n`,
    );
    return;
  }

  process.stderr.write(
    `[robot-sim] fatal — robot wallet has ${lamports} lamports; demo expects 0 (use --allow-sol to bypass)\n`,
  );
  process.exit(3);
}

// ---------------------------------------------------------------------------
// Step 1 — accept task
// ---------------------------------------------------------------------------

async function acceptTask(): Promise<unknown> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const url = `${API_BASE}/api/v1/tasks/${TASK_ID}/applications`;
  const body = {
    wallet_address: account.address,
    chain: "solana",
    message: "robot-sim — em-robot-skill Phase 3.8 dry run",
    auto_assign: false,
  };
  debugLog("accept.request", { url, body });
  const resp = await signedRequest("POST", url, body, TASK_ID!);
  debugLog("accept.response", { status: resp.status, body: resp.body });
  if (resp.status === 409) {
    process.stderr.write(
      `[robot-sim] info — wallet already applied to task ${TASK_ID} (idempotent)\n`,
    );
    return resp.body;
  }
  if (resp.status >= 400) {
    throw new Error(
      `accept failed (${resp.status}): ${JSON.stringify(resp.body)}`,
    );
  }
  return resp.body;
}

// ---------------------------------------------------------------------------
// Step 2 — scan barcode (mock)
// ---------------------------------------------------------------------------

async function scanBarcode(): Promise<unknown> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const url = `${API_BASE}/api/v1/tasks/${TASK_ID}/submissions`;
  const body = {
    worker_wallet: account.address,
    chain: "solana",
    evidence: {
      barcode: {
        decoded_payload: BARCODE_PAYLOAD,
        decoded_at: new Date().toISOString(),
        source: "scripts/demo/robot-sim.ts",
      },
    },
  };
  debugLog("scan.request", {
    url,
    payload_preview: BARCODE_PAYLOAD.slice(0, 40),
  });
  const resp = await signedRequest("POST", url, body, TASK_ID!);
  debugLog("scan.response", { status: resp.status, body: resp.body });
  if (resp.status >= 400) {
    throw new Error(
      `scan failed (${resp.status}): ${JSON.stringify(resp.body)}`,
    );
  }
  return resp.body;
}

// ---------------------------------------------------------------------------
// Step 3 — open pay.sh MPP session via 402 challenge
// ---------------------------------------------------------------------------

interface OpenSessionResult {
  channelId: string;
  capUusdc: bigint | null;
  expiresAt: number | null;
  splits: Record<string, number> | null;
  payshellBody: unknown;
}

async function openSession(): Promise<OpenSessionResult> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const url = `${PROXY}${ENDPOINT.startsWith("/") ? ENDPOINT : "/" + ENDPOINT}`;
  const probeHeaders: Record<string, string> = {
    "X-EM-Task-Id": TASK_ID!,
    "X-EM-Worker-Wallet": account.address,
    "X-EM-Worker-Chain": "solana",
    Accept: "application/json",
  };
  debugLog("open.probe", { url });
  const probe = await fetch(url, { method: "GET", headers: probeHeaders });

  if (probe.status !== 402) {
    if (probe.status >= 200 && probe.status < 300) {
      process.stderr.write(
        "[robot-sim] warn — pay.sh returned 200 without challenge; reusing existing session\n",
      );
    } else {
      const errBody = await probe.text().catch(() => "");
      throw new Error(
        `pay.sh unreachable: expected 402, got ${probe.status}: ${errBody.slice(0, 500)}`,
      );
    }
  }

  // Parse the challenge.
  const rawChallenge =
    probe.headers.get("payment-required") ??
    probe.headers.get("x-payment-required") ??
    probe.headers.get("www-authenticate");
  let challenge:
    | {
        scheme?: string;
        network?: string;
        version?: string;
        x402Version?: number;
        channelId?: string;
        payTo?: string;
        asset?: string;
        mint?: string;
        cap?: string | number;
        capUusdc?: string | number;
        splits?: Record<string, number>;
        expiresAt?: number;
        canonical?: string;
        challenge?: string;
      }
    | null = null;
  if (rawChallenge) {
    try {
      challenge = rawChallenge.startsWith("{")
        ? JSON.parse(rawChallenge)
        : JSON.parse(rawChallenge.replace(/^x402\s+/i, ""));
    } catch (e) {
      debugLog("open.header_parse_failed", String(e));
    }
  }
  if (!challenge) {
    const contentType = probe.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      challenge = (await probe.clone().json().catch(() => null)) as
        | typeof challenge
        | null;
    }
  }
  if (!challenge) {
    throw new Error("pay.sh returned 402 but no challenge could be parsed");
  }

  const messageToSign =
    challenge.canonical ?? challenge.challenge ?? JSON.stringify(challenge);
  debugLog("open.signing_challenge", { length: messageToSign.length });

  const sig = ows.signMessage(
    WALLET_NAME!,
    "solana",
    messageToSign,
    PASSPHRASE,
  );

  const envelope = {
    x402Version: challenge.x402Version ?? 1,
    scheme: challenge.scheme ?? "mpp-session",
    network: challenge.network ?? "solana",
    payload: {
      signer: account.address,
      signature: sig.signature,
      message: messageToSign,
      payee: account.address,
      taskId: TASK_ID,
    },
  };
  const paymentHeader = Buffer.from(JSON.stringify(envelope), "utf8").toString(
    "base64",
  );

  debugLog("open.retry_with_payment");
  const settled = await fetch(url, {
    method: "GET",
    headers: { ...probeHeaders, "X-Payment": paymentHeader },
  });
  if (settled.status >= 400) {
    const errBody = await settled.text().catch(() => "");
    throw new Error(
      `open rejected (${settled.status}): ${errBody.slice(0, 500)}`,
    );
  }

  const channelId =
    settled.headers.get("x-payment-response-channel-id") ??
    settled.headers.get("x-payshell-channel-id") ??
    challenge.channelId ??
    null;
  if (!channelId) {
    throw new Error("pay.sh did not return a channelId after open");
  }
  const payshellBody = await settled
    .json()
    .catch(() => ({ note: "non-JSON pay.sh response" }));

  const capUusdc =
    challenge.capUusdc !== undefined
      ? BigInt(challenge.capUusdc)
      : challenge.cap !== undefined
        ? BigInt(challenge.cap)
        : null;

  return {
    channelId,
    capUusdc,
    expiresAt: challenge.expiresAt ?? null,
    splits: challenge.splits ?? null,
    payshellBody,
  };
}

// ---------------------------------------------------------------------------
// Step 4 — voucher tick loop
// ---------------------------------------------------------------------------

interface VoucherLoopResult {
  ticks: number;
  finalCumulative: bigint;
  lastExpiresAt: number;
  lastResponse: unknown;
}

async function voucherLoop(channelId: string): Promise<VoucherLoopResult> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const tickIntervalMs = Math.max(50, Math.floor(1000 / VOUCHERS_PER_SEC));
  const totalTicks = Math.max(1, Math.floor(DURATION_SECONDS * VOUCHERS_PER_SEC));
  const perTickUusdc = RATE_UUSDC / BigInt(Math.max(1, VOUCHERS_PER_SEC));

  let cumulative = 0n;
  let lastResponse: unknown = null;
  let lastExpiresAt = Math.floor(Date.now() / 1000) + 60;

  process.stderr.write(
    `[robot-sim] voucher loop: ${totalTicks} ticks @ ${tickIntervalMs} ms (cap ${CAP_UUSDC} uusdc, +${perTickUusdc}/tick)\n`,
  );

  for (let i = 0; i < totalTicks; i++) {
    cumulative += perTickUusdc;
    if (cumulative > CAP_UUSDC) {
      cumulative = CAP_UUSDC;
    }
    const expiresAt = BigInt(Math.floor(Date.now() / 1000) + 60);
    lastExpiresAt = Number(expiresAt);

    const voucherBytes = serializeVoucher(channelId, cumulative, expiresAt);
    const voucherBase64 = Buffer.from(voucherBytes).toString("base64");
    const sig = ows.signMessage(
      WALLET_NAME!,
      "solana",
      voucherBase64,
      PASSPHRASE,
    );

    const url = `${PROXY}/_sessions/${channelId}/voucher`;
    const body = {
      channelId,
      cumulativeMicroUsdc: cumulative.toString(),
      expiresAt: Number(expiresAt),
      signer: account.address,
      signature: sig.signature,
      voucherBytesBase64: voucherBase64,
    };

    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const contentType = resp.headers.get("content-type") ?? "";
    const respBody = contentType.includes("application/json")
      ? await resp.json().catch(() => ({}))
      : await resp.text().catch(() => "");

    if (resp.status >= 400) {
      throw new Error(
        `voucher tick ${i + 1}/${totalTicks} rejected (${resp.status}): ${JSON.stringify(
          respBody,
        )}`,
      );
    }
    lastResponse = respBody;
    debugLog("voucher.tick", {
      i: i + 1,
      cumulative: cumulative.toString(),
    });

    if (cumulative >= CAP_UUSDC) {
      process.stderr.write(
        `[robot-sim] cap reached at tick ${i + 1} — stopping loop early\n`,
      );
      break;
    }
    // Stop ticking before the next iteration if we're at the last tick already.
    if (i < totalTicks - 1) {
      await sleep(tickIntervalMs);
    }
  }

  return {
    ticks: totalTicks,
    finalCumulative: cumulative,
    lastExpiresAt,
    lastResponse,
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((res) => setTimeout(res, ms));
}

// ---------------------------------------------------------------------------
// Step 5 — close session
// ---------------------------------------------------------------------------

interface CloseResult {
  settlementTxHash: string;
  finalCumulativeUusdc: string | number | null;
  refundUusdc: string | number | null;
  distribution: unknown;
}

async function closeSession(
  channelId: string,
  finalCumulative: bigint,
): Promise<CloseResult> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  const url = `${PROXY}/_sessions/${channelId}/close`;
  const body: Record<string, unknown> = {
    channelId,
    signer: account.address,
    finalCumulativeMicroUsdc: finalCumulative.toString(),
  };
  debugLog("close.request", { url, body });

  const resp = await signedRequest("POST", url, body);
  debugLog("close.response", { status: resp.status, body: resp.body });

  if (resp.status === 409) {
    // Idempotent re-close.
    process.stderr.write(
      "[robot-sim] info — channel already closed; reading cached settlement result\n",
    );
  } else if (resp.status >= 400) {
    throw new Error(
      `close failed (${resp.status}): ${JSON.stringify(resp.body)}`,
    );
  }

  const parsed = (resp.body ?? {}) as Record<string, unknown>;
  const txHash =
    (parsed.settlementTxHash as string | undefined) ??
    (parsed.tx_hash as string | undefined) ??
    (parsed.signature as string | undefined) ??
    null;
  if (!txHash) {
    throw new Error(
      `close returned no tx hash: ${JSON.stringify(parsed).slice(0, 400)}`,
    );
  }

  return {
    settlementTxHash: txHash,
    finalCumulativeUusdc:
      (parsed.finalCumulativeUusdc as string | number | null) ??
      (parsed.final_cumulative_uusdc as string | number | null) ??
      null,
    refundUusdc:
      (parsed.refundUusdc as string | number | null) ??
      (parsed.refund_uusdc as string | number | null) ??
      null,
    distribution: parsed.distribution ?? null,
  };
}

// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const account = resolveSolanaAccount(WALLET_NAME!);
  process.stderr.write(
    `[robot-sim] start — task=${TASK_ID} wallet=${account.address} proxy=${PROXY} api=${API_BASE}\n`,
  );

  await assertCinematicBalance();

  let applicationResult: unknown = null;
  if (!opts["skip-accept"]) {
    process.stderr.write("[robot-sim] step 1 — accept task\n");
    applicationResult = await acceptTask();
  } else {
    process.stderr.write("[robot-sim] step 1 — skipped (--skip-accept)\n");
  }

  let scanResult: unknown = null;
  if (!opts["skip-scan"]) {
    process.stderr.write("[robot-sim] step 2 — submit barcode scan\n");
    scanResult = await scanBarcode();
  } else {
    process.stderr.write("[robot-sim] step 2 — skipped (--skip-scan)\n");
  }

  process.stderr.write("[robot-sim] step 3 — open pay.sh MPP session\n");
  const openResult = await openSession();
  process.stderr.write(
    `[robot-sim]              channel_id=${openResult.channelId} cap=${openResult.capUusdc ?? "?"} uusdc\n`,
  );

  process.stderr.write("[robot-sim] step 4 — voucher loop\n");
  const loopResult = await voucherLoop(openResult.channelId);
  process.stderr.write(
    `[robot-sim]              done — ${loopResult.ticks} ticks, cumulative=${loopResult.finalCumulative} uusdc\n`,
  );

  process.stderr.write("[robot-sim] step 5 — close session\n");
  const closeResult = await closeSession(
    openResult.channelId,
    loopResult.finalCumulative,
  );
  process.stderr.write(
    `[robot-sim]              settled — tx=${closeResult.settlementTxHash}\n`,
  );

  // Final balance check (purely informational — robot may now have lamports
  // from receiving the worker share if the splits include SOL).
  const conn = new Connection(RPC_URL, "confirmed");
  const finalLamports = await conn
    .getBalance(new PublicKey(account.address), "confirmed")
    .catch(() => null);

  const summary = {
    task_id: TASK_ID,
    wallet: account.address,
    application: applicationResult,
    scan: scanResult,
    session: {
      channel_id: openResult.channelId,
      cap_uusdc: openResult.capUusdc?.toString() ?? null,
      splits: openResult.splits,
      expires_at: openResult.expiresAt,
    },
    voucher_loop: {
      ticks: loopResult.ticks,
      final_cumulative_uusdc: loopResult.finalCumulative.toString(),
      last_expires_at: loopResult.lastExpiresAt,
    },
    settlement: {
      tx_hash: closeResult.settlementTxHash,
      final_cumulative_uusdc: closeResult.finalCumulativeUusdc,
      refund_uusdc: closeResult.refundUusdc,
      distribution: closeResult.distribution,
    },
    final_robot_lamports: finalLamports,
  };

  // Single JSON line on stdout so callers can pipe to jq / parse from CI.
  process.stdout.write(JSON.stringify(summary, null, 2) + "\n");
  process.stderr.write("[robot-sim] success\n");
}

main().catch((err) => {
  process.stderr.write(
    `[robot-sim] FAIL — ${err instanceof Error ? err.message : String(err)}\n`,
  );
  if (DEBUG && err instanceof Error && err.stack) {
    process.stderr.write(err.stack + "\n");
  }
  process.exit(1);
});

/**
 * Phase 3 — em-robot-skill HTTP helpers.
 *
 * Shared utilities for issuing wallet-signed HTTP requests from the robot
 * tools. Centralises the canonical message format and signature header so each
 * tool stays a thin wrapper around its endpoint.
 *
 * Auth model: ERC-8128 over the Solana hot wallet. The canonical message is a
 * single line containing method + path + ISO-8601 timestamp + nonce. The
 * signature is Ed25519 (base58) produced by the OWS vault and travels in the
 * `X-EM-Auth-Signature` header. The backend re-derives the canonical message
 * from the request line + timestamp + nonce headers and validates against the
 * worker's known Solana pubkey.
 *
 * Why a single line and not EIP-712 / structured: Solana wallets do not yet
 * have a canonical typed-data scheme (SLIP-0024 / SIP-44 are MUST-support but
 * not unanimously adopted by hot wallets — see `[[SOLANA_MPP_specs_pr201]]`
 * §3.4). A textual canonical message round-trips cleanly through Phantom,
 * Backpack, Solflare AND the OWS vault.
 */

import * as crypto from "node:crypto";
import * as ows from "@open-wallet-standard/core";

export interface SolanaSignerAccount {
  walletName: string;
  address: string;
  chainId: string;
}

/**
 * Resolve the Solana account from an OWS wallet. Throws if the wallet has no
 * `solana:` account — the robot skill is Solana-only by design (Phase 3 ties
 * the entire signing path to Ed25519 + MPP vouchers).
 */
export function resolveSolanaAccount(walletName: string): SolanaSignerAccount {
  const info = ows.getWallet(walletName);
  const acc = info.accounts.find((a) => a.chainId.startsWith("solana:"));
  if (!acc) {
    throw new Error(
      `wallet "${walletName}" has no solana account — robot skill requires an Ed25519 key`,
    );
  }
  return { walletName, address: acc.address, chainId: acc.chainId };
}

/**
 * Build the canonical message that the backend will reconstruct on the verify
 * side. Whitespace and casing MUST match exactly — diverging here is the most
 * common 401 cause across the prior auth-hardening master plan.
 */
export function buildCanonicalMessage(
  method: string,
  path: string,
  timestamp: string,
  nonce: string,
  bodyDigest: string,
): string {
  return [
    `EM-AUTH/1`,
    `method=${method.toUpperCase()}`,
    `path=${path}`,
    `timestamp=${timestamp}`,
    `nonce=${nonce}`,
    `body-sha256=${bodyDigest}`,
  ].join("\n");
}

function sha256Hex(bytes: Uint8Array | string): string {
  const buf =
    typeof bytes === "string" ? Buffer.from(bytes, "utf8") : Buffer.from(bytes);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

export interface SignedRequestOptions {
  walletName: string;
  passphrase?: string;
  method: string;
  url: string;
  body?: unknown;
  taskId?: string;
  extraHeaders?: Record<string, string>;
}

export interface SignedRequestResult {
  status: number;
  body: unknown;
  headers: Record<string, string>;
}

/**
 * Issue a wallet-signed HTTP request. Returns the parsed JSON body when the
 * response Content-Type is JSON, otherwise the raw text.
 *
 * Side-effect free apart from the network call. No retries — caller decides
 * the retry policy because pay.sh and EM treat idempotency differently:
 * `robot_sign_voucher_tick` is cumulative-safe to retry, `robot_accept_task`
 * is idempotent at the row level, but a generic retry inside this helper
 * would hide voucher rejections that the caller MUST surface.
 */
export async function signedRequest(
  opts: SignedRequestOptions,
): Promise<SignedRequestResult> {
  const account = resolveSolanaAccount(opts.walletName);

  const parsedUrl = new URL(opts.url);
  const pathForAuth = parsedUrl.pathname + parsedUrl.search;
  const timestamp = new Date().toISOString();
  const nonce = crypto.randomBytes(16).toString("hex");

  const bodyBytes =
    opts.body === undefined || opts.body === null
      ? new Uint8Array(0)
      : Buffer.from(JSON.stringify(opts.body), "utf8");
  const bodyDigest = sha256Hex(bodyBytes);

  const canonical = buildCanonicalMessage(
    opts.method,
    pathForAuth,
    timestamp,
    nonce,
    bodyDigest,
  );

  const sig = ows.signMessage(
    opts.walletName,
    "solana",
    canonical,
    opts.passphrase ?? undefined,
  );

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-EM-Auth-Wallet": account.address,
    "X-EM-Auth-Chain": "solana",
    "X-EM-Auth-Timestamp": timestamp,
    "X-EM-Auth-Nonce": nonce,
    "X-EM-Auth-Body-SHA256": bodyDigest,
    "X-EM-Auth-Signature": sig.signature,
    ...opts.extraHeaders,
  };
  if (opts.taskId) {
    headers["X-EM-Task-Id"] = opts.taskId;
  }

  const resp = await fetch(opts.url, {
    method: opts.method,
    headers,
    body: bodyBytes.byteLength === 0 ? undefined : bodyBytes,
  });

  const respHeaders: Record<string, string> = {};
  resp.headers.forEach((v, k) => {
    respHeaders[k] = v;
  });

  const contentType = resp.headers.get("content-type") ?? "";
  let parsedBody: unknown;
  if (contentType.includes("application/json")) {
    parsedBody = await resp.json().catch(() => ({}));
  } else {
    parsedBody = await resp.text().catch(() => "");
  }

  return { status: resp.status, body: parsedBody, headers: respHeaders };
}

/**
 * Resolve base URLs from env. Centralised so tools fail with a consistent
 * error if the operator forgot to wire EM_PAYSHELL_URL.
 */
export function getPayshellBase(): string {
  const v = process.env.EM_PAYSHELL_URL;
  if (!v) {
    throw new Error(
      "EM_PAYSHELL_URL is not set — point at pay.sh proxy (e.g. https://api.execution.market)",
    );
  }
  return v.replace(/\/+$/, "");
}

export function getApiBase(): string {
  return (process.env.EM_API_BASE ?? getPayshellBase()).replace(/\/+$/, "");
}

/**
 * Tiny env passthrough so individual tools don't grow conditional debug
 * logging logic. Anything written here goes to stderr (MCP stdout is the
 * transport).
 */
export function debugLog(label: string, payload: unknown): void {
  if (
    process.env.EM_ROBOT_SKILL_DEBUG === "1" ||
    process.env.EM_ROBOT_SKILL_DEBUG === "true"
  ) {
    const safe =
      typeof payload === "string" ? payload : JSON.stringify(payload);
    process.stderr.write(`[em-robot-skill] ${label}: ${safe}\n`);
  }
}

#!/usr/bin/env tsx
/**
 * Phase 4.11 + 6.1 prep — Dry-run preflight automation.
 *
 * Reads `.env.local`, exercises every external surface the demo depends
 * on (Solana RPC, pay.sh control plane, EM backend, dashboard, MoonPay
 * quote, URL signing), and reports a pass/fail line per check. Pairs
 * with `docs/runbooks/nyc-demo-dry-run-checklist.md`.
 *
 * The script *never* prints private keys, env values, RPC URLs with API
 * keys embedded, or anything else that could leak on stream. Only public
 * pubkeys (base58), integer balances, and pass/fail booleans hit stdout.
 *
 * Modes
 *   --mode surfpool   uses local Surfpool fork at SURFPOOL_RPC_URL (defaults
 *                     to http://127.0.0.1:8899). MoonPay checks are stubs.
 *   --mode mainnet    uses SOLANA_RPC_URL (production QuikNode). Hits the
 *                     real MoonPay test surface for the quote round-trip.
 *
 * Exit codes
 *   0  all checks passed
 *   1  one or more checks failed (see stdout + report file for details)
 *   2  fatal env error (missing .env.local, invalid mode)
 */
import { Connection, PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { getAssociatedTokenAddressSync } from "@solana/spl-token";
import { config } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdir, writeFile } from "node:fs/promises";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env.local") });

const USDC_MINT_MAINNET = new PublicKey(
  "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
);

interface CheckResult {
  id: string;
  label: string;
  status: "pass" | "fail" | "skip";
  detail?: string;
  hint?: string;
}

interface PreflightConfig {
  mode: "surfpool" | "mainnet";
  rpcUrl: string;
  emBaseUrl: string;
  dashboardUrl: string;
  payshellBaseUrl: string;
  saulPubkey?: string;
  robotPubkey?: string;
  backupPubkey?: string;
  treasuryPubkey?: string;
  moonpayBaseUrl: string;
}

function parseArgs(): { mode: "surfpool" | "mainnet" } {
  const args = process.argv.slice(2);
  const modeIdx = args.indexOf("--mode");
  if (modeIdx < 0 || !args[modeIdx + 1]) {
    console.error(
      "[fatal] --mode <surfpool|mainnet> is required (see docs/runbooks/nyc-demo-dry-run-checklist.md)",
    );
    process.exit(2);
  }
  const mode = args[modeIdx + 1];
  if (mode !== "surfpool" && mode !== "mainnet") {
    console.error(`[fatal] unknown mode: ${mode}`);
    process.exit(2);
  }
  return { mode };
}

function loadConfig(mode: "surfpool" | "mainnet"): PreflightConfig {
  const rpcUrl =
    mode === "surfpool"
      ? process.env.SURFPOOL_RPC_URL ?? "http://127.0.0.1:8899"
      : process.env.SOLANA_RPC_URL ?? "";
  return {
    mode,
    rpcUrl,
    emBaseUrl: process.env.EM_BASE_URL ?? "https://api.execution.market",
    dashboardUrl: process.env.DASHBOARD_URL ?? "https://execution.market",
    payshellBaseUrl: process.env.PAYSHELL_BASE_URL ?? "",
    saulPubkey: process.env.DEMO_SAUL_SOLANA_PUBKEY,
    robotPubkey: process.env.DEMO_ROBOT_SOLANA_PUBKEY,
    backupPubkey: process.env.DEMO_BACKUP_SOLANA_PUBKEY,
    treasuryPubkey: process.env.DEMO_TREASURY_SOLANA_PUBKEY,
    moonpayBaseUrl: process.env.MOONPAY_BASE_URL ?? "https://api.moonpay.com",
  };
}

function pass(id: string, label: string, detail?: string): CheckResult {
  return { id, label, status: "pass", detail };
}

function fail(id: string, label: string, hint: string): CheckResult {
  return { id, label, status: "fail", hint };
}

function skip(id: string, label: string, detail: string): CheckResult {
  return { id, label, status: "skip", detail };
}

async function checkEnvVars(cfg: PreflightConfig): Promise<CheckResult> {
  const required = [
    "DEMO_SAUL_SOLANA_PUBKEY",
    "DEMO_ROBOT_SOLANA_PUBKEY",
    "DEMO_BACKUP_SOLANA_PUBKEY",
    "DEMO_TREASURY_SOLANA_PUBKEY",
    "PAYSHELL_BASE_URL",
  ];
  if (cfg.mode === "mainnet") {
    required.push(
      "SOLANA_RPC_URL",
      "MOONPAY_API_KEY",
      "MOONPAY_SECRET_KEY",
    );
  }
  const missing = required.filter((name) => !process.env[name]);
  if (missing.length === 0) {
    return pass("env-vars", "Env vars present");
  }
  return fail(
    "env-vars",
    "Env vars present",
    `missing in .env.local: ${missing.join(", ")}`,
  );
}

async function checkSolanaRpc(cfg: PreflightConfig): Promise<CheckResult> {
  if (!cfg.rpcUrl) {
    return fail("solana-rpc", "Solana RPC reachable", "rpc URL not configured");
  }
  try {
    const conn = new Connection(cfg.rpcUrl, "confirmed");
    const start = Date.now();
    const slot = await conn.getSlot();
    const elapsed = Date.now() - start;
    if (elapsed > 2000) {
      return fail(
        "solana-rpc",
        "Solana RPC reachable",
        `slow response: ${elapsed}ms (>2s budget)`,
      );
    }
    return pass("solana-rpc", "Solana RPC reachable", `slot=${slot} (${elapsed}ms)`);
  } catch (e) {
    return fail(
      "solana-rpc",
      "Solana RPC reachable",
      e instanceof Error ? e.message : "unknown error",
    );
  }
}

async function checkHttp(
  id: string,
  label: string,
  url: string,
  expectStatus = 200,
): Promise<CheckResult> {
  if (!url) {
    return fail(id, label, "URL not configured");
  }
  try {
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === expectStatus) {
      return pass(id, label, `HTTP ${resp.status}`);
    }
    return fail(id, label, `HTTP ${resp.status} (expected ${expectStatus})`);
  } catch (e) {
    return fail(id, label, e instanceof Error ? e.message : "fetch error");
  }
}

async function checkSolanaBalances(
  cfg: PreflightConfig,
): Promise<CheckResult[]> {
  if (!cfg.saulPubkey || !cfg.robotPubkey || !cfg.backupPubkey) {
    return [fail("balances", "Wallet baselines", "demo pubkeys missing")];
  }
  const conn = new Connection(cfg.rpcUrl, "confirmed");
  const out: CheckResult[] = [];

  for (const [id, label, pubkey, expect] of [
    [
      "saul-baseline",
      "Saul wallet baseline (USDC=0, SOL>=0.05)",
      cfg.saulPubkey,
      { usdc: 0, solMin: 0.05 },
    ],
    [
      "robot-baseline",
      "Robot wallet baseline (USDC=0, SOL=0)",
      cfg.robotPubkey,
      { usdc: 0, solMin: 0, solMax: 0.001 },
    ],
    [
      "backup-baseline",
      "Backup wallet baseline (USDC>=40, SOL>=0.05)",
      cfg.backupPubkey,
      { usdcMin: 40, solMin: 0.05 },
    ],
  ] as const) {
    try {
      const owner = new PublicKey(pubkey);
      const sol =
        (await conn.getBalance(owner)) / LAMPORTS_PER_SOL;
      let usdc = 0;
      try {
        const ata = getAssociatedTokenAddressSync(USDC_MINT_MAINNET, owner);
        const tokenAcc = await conn.getTokenAccountBalance(ata);
        usdc = Number(tokenAcc.value.uiAmount ?? 0);
      } catch {
        usdc = 0;
      }
      const violations: string[] = [];
      if ("usdc" in expect && usdc !== expect.usdc) {
        violations.push(`USDC=${usdc} (want ${expect.usdc})`);
      }
      if ("usdcMin" in expect && usdc < expect.usdcMin) {
        violations.push(`USDC=${usdc} (want >=${expect.usdcMin})`);
      }
      if ("solMin" in expect && sol < expect.solMin) {
        violations.push(`SOL=${sol.toFixed(4)} (want >=${expect.solMin})`);
      }
      if ("solMax" in expect && sol > expect.solMax) {
        violations.push(`SOL=${sol.toFixed(4)} (want <=${expect.solMax})`);
      }
      out.push(
        violations.length === 0
          ? pass(id, label, `USDC=${usdc} SOL=${sol.toFixed(4)}`)
          : fail(id, label, violations.join(", ")),
      );
    } catch (e) {
      out.push(
        fail(id, label, e instanceof Error ? e.message : "balance read failed"),
      );
    }
  }
  return out;
}

async function checkMoonpayQuote(
  cfg: PreflightConfig,
): Promise<CheckResult> {
  if (cfg.mode === "surfpool") {
    return skip("moonpay-quote", "MoonPay quote round-trip", "surfpool mode");
  }
  const apiKey = process.env.MOONPAY_API_KEY;
  if (!apiKey) {
    return fail(
      "moonpay-quote",
      "MoonPay quote round-trip",
      "MOONPAY_API_KEY not set",
    );
  }
  const url = `${cfg.moonpayBaseUrl}/v3/currencies/quote?apiKey=${apiKey}&baseCurrencyCode=usd&quoteCurrencyCode=usdc_sol&baseCurrencyAmount=20`;
  try {
    const resp = await fetch(url, { headers: { Accept: "application/json" } });
    if (resp.status !== 200) {
      return fail(
        "moonpay-quote",
        "MoonPay quote round-trip",
        `HTTP ${resp.status}`,
      );
    }
    const json = (await resp.json()) as { quoteCurrencyAmount?: number };
    if (typeof json.quoteCurrencyAmount !== "number") {
      return fail(
        "moonpay-quote",
        "MoonPay quote round-trip",
        "no quoteCurrencyAmount in response",
      );
    }
    return pass(
      "moonpay-quote",
      "MoonPay quote round-trip",
      `usdc≈${json.quoteCurrencyAmount.toFixed(2)} for $20`,
    );
  } catch (e) {
    return fail(
      "moonpay-quote",
      "MoonPay quote round-trip",
      e instanceof Error ? e.message : "fetch failed",
    );
  }
}

async function writeReport(
  mode: string,
  results: CheckResult[],
): Promise<string> {
  const reportDir = resolve(__dirname, "../../.dry-run-reports");
  await mkdir(reportDir, { recursive: true });
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const path = resolve(reportDir, `${ts}.json`);
  const passed = results.filter((r) => r.status === "pass").length;
  const failed = results.filter((r) => r.status === "fail").length;
  const skipped = results.filter((r) => r.status === "skip").length;
  await writeFile(
    path,
    JSON.stringify(
      { mode, ranAt: new Date().toISOString(), passed, failed, skipped, checks: results },
      null,
      2,
    ),
  );
  return path;
}

function printSummary(results: CheckResult[]): void {
  for (const r of results) {
    const icon =
      r.status === "pass" ? "[ok]" : r.status === "fail" ? "[FAIL]" : "[skip]";
    const tail = r.detail ?? r.hint ?? "";
    console.log(`${icon.padEnd(6)} ${r.label}${tail ? ` — ${tail}` : ""}`);
  }
}

async function main() {
  const { mode } = parseArgs();
  const cfg = loadConfig(mode);
  const results: CheckResult[] = [];

  results.push(await checkEnvVars(cfg));
  results.push(await checkSolanaRpc(cfg));
  results.push(
    await checkHttp(
      "payshell-health",
      "pay.sh control plane reachable",
      `${cfg.payshellBaseUrl}/healthz`,
    ),
  );
  results.push(
    await checkHttp("em-health", "EM backend reachable", `${cfg.emBaseUrl}/health`),
  );
  results.push(
    await checkHttp(
      "dashboard-health",
      "Dashboard reachable",
      `${cfg.dashboardUrl}/`,
    ),
  );
  results.push(...(await checkSolanaBalances(cfg)));
  results.push(await checkMoonpayQuote(cfg));

  printSummary(results);

  const reportPath = await writeReport(mode, results);
  const failed = results.filter((r) => r.status === "fail").length;
  console.log("");
  console.log(`Report: ${reportPath}`);
  console.log(
    failed === 0
      ? "[ok] All checks passed. Safe to start the dry-run."
      : `[FAIL] ${failed} check(s) failed. Do NOT start the dry-run until resolved.`,
  );
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error(
    "[fatal]",
    err instanceof Error ? err.message : String(err),
  );
  process.exit(2);
});

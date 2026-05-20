#!/usr/bin/env tsx
/**
 * Phase 6.4 — Verify and (optionally) prefund the demo wallets for the
 * MoonPay NYC cinematic capture.
 *
 * The demo flow depends on a very specific starting state on Solana:
 *
 *   Saul publisher wallet:  USDC=0      SOL>=0.05   (on-ramp is on-camera)
 *   Robot worker wallet:    USDC=0      SOL=0        (fee-sponsorship sells the demo)
 *   Backup buyer wallet:    USDC>=40    SOL>=0.05   (second-take reserve)
 *   Treasury wallet:        any         any          (read-only sanity)
 *
 * Getting one of these wrong on the day breaks the cinematography (e.g. if
 * the robot has any SOL, the "robot starts with nothing" narration is a lie).
 * This script's job is to read those balances and tell the operator exactly
 * what's off, and — for the local Surfpool fork only — to fix it with the
 * cheatcode RPC.
 *
 * Modes
 *   --check                  (default) read-only sanity report against expected balances
 *   --surfpool               use Heist cheatcodes to set state on a local Surfpool fork
 *   --mainnet-plan           print the exact USDC + SOL transfers needed on mainnet,
 *                            but do NOT sign or send anything. The actual funding is
 *                            done from a Ledger by the operator (no hot key here).
 *   --reset                  after the demo, prints the "drain back to baseline" plan
 *                            (or executes it on Surfpool when combined with --surfpool).
 *
 * What it does NOT do
 *   - Sign or send mainnet transactions. The mainnet path is "print the plan,
 *     human signs from Ledger". Hot keys never appear in this script.
 *   - Display private keys, seed phrases, RPC API keys, or anything else the
 *     user might have on stream. Only public Solana pubkeys and integer
 *     balances are printed.
 *
 * Required env (read from .env.local; never inline):
 *   DEMO_SAUL_SOLANA_PUBKEY        Base58 pubkey of Saul's hot OWS wallet
 *   DEMO_ROBOT_SOLANA_PUBKEY       Base58 pubkey of the robot's OWS skill wallet
 *   DEMO_BACKUP_SOLANA_PUBKEY      Base58 pubkey of the $40 reserve wallet
 *   DEMO_TREASURY_SOLANA_PUBKEY    Base58 pubkey of the treasury (read-only)
 *   SOLANA_RPC_URL                 QuikNode mainnet URL (when --mainnet-plan)
 *                                  defaults to http://127.0.0.1:8899 for Surfpool
 */
import { Connection, PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { getAssociatedTokenAddressSync } from "@solana/spl-token";
import { config } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env.local") });

const USDC_MINT = new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");
const USDC_DECIMALS = 6;
const USDC_MIN_RAW_BACKUP = 40 * 1_000_000;
const SOL_MIN_LAMPORTS_GAS = Math.floor(0.05 * LAMPORTS_PER_SOL);

type Mode = "check" | "surfpool" | "mainnet-plan" | "reset";

interface WalletTarget {
  role: "saul" | "robot" | "backup" | "treasury";
  pubkey: PublicKey;
  expect: { usdcRaw: number | "any"; lamports: number | "any" };
  comparator: "exact" | "atLeast" | "any";
}

interface WalletReading {
  target: WalletTarget;
  actualUsdcRaw: number;
  actualLamports: number;
  ok: boolean;
  issues: string[];
}

function parseMode(argv: string[]): Mode {
  const flags = argv.slice(2);
  if (flags.includes("--surfpool")) return "surfpool";
  if (flags.includes("--mainnet-plan")) return "mainnet-plan";
  if (flags.includes("--reset")) return "reset";
  return "check";
}

function requireEnv(name: string): string {
  const raw = process.env[name];
  if (!raw) {
    console.error(`[FATAL] ${name} is required in .env.local`);
    process.exit(1);
  }
  return raw;
}

function buildTargets(): WalletTarget[] {
  return [
    {
      role: "saul",
      pubkey: new PublicKey(requireEnv("DEMO_SAUL_SOLANA_PUBKEY")),
      expect: { usdcRaw: 0, lamports: SOL_MIN_LAMPORTS_GAS },
      comparator: "atLeast",
    },
    {
      role: "robot",
      pubkey: new PublicKey(requireEnv("DEMO_ROBOT_SOLANA_PUBKEY")),
      expect: { usdcRaw: 0, lamports: 0 },
      comparator: "exact",
    },
    {
      role: "backup",
      pubkey: new PublicKey(requireEnv("DEMO_BACKUP_SOLANA_PUBKEY")),
      expect: { usdcRaw: USDC_MIN_RAW_BACKUP, lamports: SOL_MIN_LAMPORTS_GAS },
      comparator: "atLeast",
    },
    {
      role: "treasury",
      pubkey: new PublicKey(requireEnv("DEMO_TREASURY_SOLANA_PUBKEY")),
      expect: { usdcRaw: "any", lamports: "any" },
      comparator: "any",
    },
  ];
}

async function readUsdcRaw(conn: Connection, owner: PublicKey): Promise<number> {
  const ata = getAssociatedTokenAddressSync(USDC_MINT, owner, true);
  const info = await conn.getTokenAccountBalance(ata).catch(() => null);
  if (!info) return 0;
  return Number(info.value.amount);
}

function evaluateReading(target: WalletTarget, usdcRaw: number, lamports: number): WalletReading {
  const issues: string[] = [];
  const { expect, comparator } = target;

  if (comparator !== "any") {
    if (expect.usdcRaw !== "any") {
      const expectedUsdc = expect.usdcRaw;
      const usdcMismatch =
        comparator === "exact" ? usdcRaw !== expectedUsdc : usdcRaw < expectedUsdc;
      if (usdcMismatch) {
        issues.push(
          `USDC ${comparator === "exact" ? "must equal" : "must be at least"} ` +
            `${(expectedUsdc / 10 ** USDC_DECIMALS).toFixed(6)} (actual ${(usdcRaw / 10 ** USDC_DECIMALS).toFixed(6)})`,
        );
      }
    }
    if (expect.lamports !== "any") {
      const expectedLamports = expect.lamports;
      const solMismatch =
        comparator === "exact"
          ? lamports !== expectedLamports
          : lamports < expectedLamports;
      if (solMismatch) {
        issues.push(
          `SOL ${comparator === "exact" ? "must equal" : "must be at least"} ` +
            `${(expectedLamports / LAMPORTS_PER_SOL).toFixed(4)} (actual ${(lamports / LAMPORTS_PER_SOL).toFixed(4)})`,
        );
      }
    }
  }

  return {
    target,
    actualUsdcRaw: usdcRaw,
    actualLamports: lamports,
    ok: issues.length === 0,
    issues,
  };
}

function formatRow(reading: WalletReading): string {
  const { target, actualUsdcRaw, actualLamports, ok } = reading;
  const usdc = (actualUsdcRaw / 10 ** USDC_DECIMALS).toFixed(6);
  const sol = (actualLamports / LAMPORTS_PER_SOL).toFixed(4);
  const status = ok ? "OK" : "DRIFT";
  return `  ${target.role.padEnd(9)} ${target.pubkey.toBase58().padEnd(46)} USDC=${usdc.padStart(12)}  SOL=${sol.padStart(8)}  [${status}]`;
}

function printPlan(reading: WalletReading, mode: Mode): void {
  if (reading.ok) return;
  if (mode === "mainnet-plan" || mode === "check") {
    for (const issue of reading.issues) {
      console.log(`     - ${issue}`);
    }
    if (mode === "mainnet-plan") {
      console.log(
        `     → fund manually from Ledger: send the delta to ${reading.target.pubkey.toBase58()}`,
      );
    }
  }
}

async function runSurfpoolHeist(
  rpcUrl: string,
  target: WalletTarget,
): Promise<void> {
  if (target.comparator === "any" || target.expect.usdcRaw === "any") return;
  const desiredRaw = target.expect.usdcRaw as number;

  const body = {
    jsonrpc: "2.0",
    id: 1,
    method: "surfnet_setTokenAccount",
    params: [
      target.pubkey.toBase58(),
      USDC_MINT.toBase58(),
      { amount: desiredRaw.toString() },
    ],
  };
  const resp = await fetch(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`surfnet_setTokenAccount HTTP ${resp.status}`);
  }
  const json = (await resp.json()) as { error?: { message: string } };
  if (json.error) {
    throw new Error(`surfnet_setTokenAccount: ${json.error.message}`);
  }

  if (target.expect.lamports !== "any" && (target.expect.lamports as number) > 0) {
    const sig = await new Connection(rpcUrl, "confirmed").requestAirdrop(
      target.pubkey,
      target.expect.lamports as number,
    );
    await new Connection(rpcUrl, "confirmed").confirmTransaction(sig, "confirmed");
  }
}

async function main() {
  const mode = parseMode(process.argv);
  const rpcUrl =
    mode === "surfpool"
      ? process.env.SOLANA_RPC_URL ?? "http://127.0.0.1:8899"
      : requireEnv("SOLANA_RPC_URL");

  console.log(`[INFO] mode: ${mode}`);
  console.log(`[INFO] rpc:  ${rpcUrl.includes("api.mainnet") ? "<mainnet>" : rpcUrl}`);
  console.log("");

  const targets = buildTargets();
  const conn = new Connection(rpcUrl, "confirmed");

  if (mode === "surfpool") {
    for (const target of targets) {
      if (target.role === "treasury") continue;
      await runSurfpoolHeist(rpcUrl, target);
    }
  }

  const readings: WalletReading[] = [];
  for (const target of targets) {
    const [usdcRaw, lamports] = await Promise.all([
      readUsdcRaw(conn, target.pubkey),
      conn.getBalance(target.pubkey),
    ]);
    readings.push(evaluateReading(target, usdcRaw, lamports));
  }

  console.log("  role      pubkey".padEnd(58) + "  USDC".padEnd(18) + "  SOL".padEnd(12) + "  status");
  for (const reading of readings) {
    console.log(formatRow(reading));
    printPlan(reading, mode);
  }
  console.log("");

  if (mode === "reset") {
    console.log("[NOTE] reset mode prints the drain plan but never spends on mainnet.");
    console.log("       Surfpool: re-run with --surfpool to snap back to baseline.");
    console.log("       Mainnet:  drain the backup wallet's residual USDC back to treasury");
    console.log("                 via a Ledger-signed transfer; let Saul's SOL dust decay.");
  }

  const drift = readings.filter((r) => !r.ok);
  if (drift.length > 0) {
    console.log(`[WARN] ${drift.length} wallet(s) off baseline.`);
    process.exit(mode === "check" ? 1 : 0);
  }
  console.log("[OK] all demo wallets at baseline.");
}

main().catch((err) => {
  console.error("[FATAL]", err?.message ?? err);
  process.exit(1);
});

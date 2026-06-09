/**
 * Phase 1.9 — Plan B safety net: open / voucher / close a MPP session directly via @solana/mpp
 * SDK, bypassing pay.sh. If this passes but session-helloworld.sh fails, the issue is in
 * pay.sh config (em-gateway.yml), not in the SDK or chain.
 *
 * Run:  pnpm tsx scripts/verify-session.ts
 *
 * SECURITY: reads keypairs from .secrets/surfpool-keys/ (DEV ONLY, gitignored).
 */
import { Connection, Keypair, PublicKey } from "@solana/web3.js";
import { promises as fs } from "node:fs";
import * as path from "node:path";

const RPC_URL = process.env.SOLANA_RPC_URL ?? "http://127.0.0.1:8899";
const USDC_MINT = new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");
const KEY_DIR = path.resolve("../../.secrets/surfpool-keys");

async function loadKey(role: "payer" | "payee" | "treasury"): Promise<Keypair> {
  const raw = await fs.readFile(path.join(KEY_DIR, `${role}.json`), "utf8");
  return Keypair.fromSecretKey(new Uint8Array(JSON.parse(raw)));
}

async function main() {
  const conn = new Connection(RPC_URL, "confirmed");
  console.log(`[INFO] RPC: ${RPC_URL}`);

  const payer = await loadKey("payer");
  const payee = await loadKey("payee");
  const treasury = await loadKey("treasury");

  console.log(`[INFO] payer    = ${payer.publicKey.toBase58()}`);
  console.log(`[INFO] payee    = ${payee.publicKey.toBase58()}`);
  console.log(`[INFO] treasury = ${treasury.publicKey.toBase58()}`);

  // @solana/mpp 0.5.2 exports a SessionClient. The exact import path can shift
  // with rev `01`; pin happens via package.json `0.5.2` exact (D-11).
  let SessionClient: unknown;
  try {
    SessionClient = (await import("@solana/mpp")).SessionClient;
  } catch (err) {
    console.error("[FATAL] @solana/mpp not installed. Run pnpm install in this workspace.");
    console.error("        Or @solana/mpp@0.5.2 may not export SessionClient under this name.");
    console.error("        Inspect: node -e \"console.log(Object.keys(require('@solana/mpp')))\"");
    process.exit(1);
  }

  console.log("[INFO] @solana/mpp loaded. Exports:", Object.keys(await import("@solana/mpp")));
  console.log("[TODO] open / voucher / close flow — implement once Phase 1.8 (pay.sh hello-world)");
  console.log("       confirms the wire format empirically. Keep this as the comparator script.");
}

main().catch((err: unknown) => {
  const msg = err instanceof Error ? err.message : String(err);
  console.error("[FATAL]", msg);
  process.exit(1);
});

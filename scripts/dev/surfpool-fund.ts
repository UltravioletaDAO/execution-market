#!/usr/bin/env tsx
/**
 * Phase 1.2 — Fund test wallets on local Surfpool via "Heist" cheatcode RPC methods.
 *
 * Generates 3 keypairs (payer/payee/treasury), persists them to .secrets/surfpool-keys/
 * (gitignored), and airdrops SOL + mints USDC into their associated token accounts.
 *
 * Run:   pnpm tsx scripts/dev/surfpool-fund.ts
 * Reset: rm -rf .secrets/surfpool-keys && pnpm tsx scripts/dev/surfpool-fund.ts
 *
 * SECURITY: keys produced here are DEV-ONLY for a local fork. Never reuse on mainnet.
 *           Files written to .secrets/ which is gitignored. INC-2026-03-30 zero-tolerance.
 */
import { Keypair, Connection, PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { promises as fs } from "node:fs";
import * as path from "node:path";

const RPC_URL = process.env.SOLANA_RPC_URL ?? "http://127.0.0.1:8899";
const USDC_MINT = new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");
const SOL_AIRDROP = 5 * LAMPORTS_PER_SOL;
const USDC_AMOUNT_RAW = 100 * 1_000_000; // 100 USDC (6 decimals)
const KEY_DIR = path.resolve(".secrets/surfpool-keys");

type Role = "payer" | "payee" | "treasury";
const ROLES: Role[] = ["payer", "payee", "treasury"];

async function loadOrCreateKey(role: Role): Promise<Keypair> {
  const file = path.join(KEY_DIR, `${role}.json`);
  try {
    const raw = await fs.readFile(file, "utf8");
    return Keypair.fromSecretKey(new Uint8Array(JSON.parse(raw)));
  } catch {
    const kp = Keypair.generate();
    await fs.mkdir(KEY_DIR, { recursive: true });
    await fs.writeFile(file, JSON.stringify(Array.from(kp.secretKey)), { mode: 0o600 });
    return kp;
  }
}

async function airdropSol(conn: Connection, pubkey: PublicKey, lamports: number) {
  const sig = await conn.requestAirdrop(pubkey, lamports);
  await conn.confirmTransaction(sig, "confirmed");
}

async function setTokenAccount(conn: Connection, owner: PublicKey, mint: PublicKey, amountRaw: number) {
  // Surfpool "Heist" cheatcode — set an SPL token account balance without a real transfer.
  const body = {
    jsonrpc: "2.0",
    id: 1,
    method: "surfnet_setTokenAccount",
    params: [
      owner.toBase58(),
      mint.toBase58(),
      { amount: amountRaw.toString() },
    ],
  };
  const resp = await fetch(RPC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`surfnet_setTokenAccount HTTP ${resp.status}`);
  const json = await resp.json() as { error?: { message: string } };
  if (json.error) throw new Error(`surfnet_setTokenAccount: ${json.error.message}`);
}

async function main() {
  const conn = new Connection(RPC_URL, "confirmed");
  console.log(`[INFO] connecting to surfpool: ${RPC_URL}`);

  for (const role of ROLES) {
    const kp = await loadOrCreateKey(role);
    console.log(`[INFO] ${role.padEnd(8)} = ${kp.publicKey.toBase58()}`);

    await airdropSol(conn, kp.publicKey, SOL_AIRDROP);
    await setTokenAccount(conn, kp.publicKey, USDC_MINT, USDC_AMOUNT_RAW);

    const bal = await conn.getBalance(kp.publicKey);
    console.log(`         SOL=${(bal / LAMPORTS_PER_SOL).toFixed(2)}  USDC=${USDC_AMOUNT_RAW / 1_000_000}`);
  }

  console.log(`\n[OK] funded ${ROLES.length} wallets. Keys in ${KEY_DIR} (gitignored).`);
}

main().catch((err) => {
  console.error("[FATAL]", err.message);
  process.exit(1);
});

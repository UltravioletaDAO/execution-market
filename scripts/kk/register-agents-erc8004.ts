/**
 * Karma Kadabra V2 — Task 3.6: ERC-8004 Agent Registration
 *
 * Registers all swarm agents on ERC-8004 Identity Registry (Base mainnet)
 * via the Ultravioleta Facilitator (gasless registration).
 *
 * Usage:
 *   npx tsx register-agents-erc8004.ts --wallets config/wallets.json --dry-run
 *   npx tsx register-agents-erc8004.ts --wallets config/wallets.json
 *   npx tsx register-agents-erc8004.ts --wallets config/wallets.json --network polygon
 */

import { readFileSync, writeFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { config } from "dotenv";
import type { Address } from "viem";
import type { WalletManifest } from "./generate-wallets.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env.local") });

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz";
const DELAY_MS = 2000; // 2s between registrations to avoid rate limiting

interface RegistrationResult {
  name: string;
  address: string;
  agentId: number | null;
  network: string;
  txHash: string | null;
  status: "success" | "already_registered" | "failed";
  error?: string;
}

// ---------------------------------------------------------------------------
// Facilitator API
// ---------------------------------------------------------------------------

async function registerAgent(
  address: string,
  agentName: string,
  network: string,
): Promise<{ agentId: number; txHash: string }> {
  const domain = `${agentName}.kk.ultravioletadao.xyz`;

  const response = await fetch(`${FACILITATOR_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      address,
      domain,
      network,
      metadata: {
        name: `KK Agent: ${agentName}`,
        description: `Karma Kadabra swarm agent representing ${agentName} from Ultravioleta DAO community`,
        swarm: "karma-kadabra-v2",
        version: "1.0",
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  const data = await response.json();
  return {
    agentId: data.agent_id || data.agentId || data.tokenId,
    txHash: data.tx_hash || data.txHash || data.transaction_hash || "unknown",
  };
}

async function checkIdentity(
  address: string,
  network: string,
): Promise<{ registered: boolean; agentId?: number }> {
  try {
    const response = await fetch(
      `${FACILITATOR_URL}/identity?address=${address}&network=${network}`,
    );
    if (response.ok) {
      const data = await response.json();
      if (data.agent_id || data.agentId) {
        return { registered: true, agentId: data.agent_id || data.agentId };
      }
    }
    return { registered: false };
  } catch {
    return { registered: false };
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);

  const walletsFile = args.includes("--wallets")
    ? args[args.indexOf("--wallets") + 1]
    : resolve(__dirname, "config", "wallets.json");

  const network = args.includes("--network")
    ? args[args.indexOf("--network") + 1]
    : "base";

  const dryRun = args.includes("--dry-run");
  const skipExisting = !args.includes("--force");

  // Load wallets
  let manifest: WalletManifest;
  try {
    manifest = JSON.parse(readFileSync(walletsFile, "utf-8"));
  } catch {
    console.error(`ERROR: Cannot read ${walletsFile}. Run generate-wallets.ts first.`);
    process.exit(1);
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log(`  Karma Kadabra V2 — ERC-8004 Registration`);
  console.log(`  Network: ${network}`);
  console.log(`  Agents:  ${manifest.count}`);
  console.log(`  Facilitator: ${FACILITATOR_URL}`);
  if (dryRun) console.log(`  ** DRY RUN — no registrations **`);
  console.log(`${"=".repeat(60)}\n`);

  const results: RegistrationResult[] = [];
  let registered = 0;
  let skipped = 0;
  let failed = 0;

  for (const wallet of manifest.wallets) {
    const { name, address, index } = wallet;

    // Check if already registered
    if (skipExisting) {
      const identity = await checkIdentity(address, network);
      if (identity.registered) {
        console.log(`  [${index}] ${name}: already registered (Agent #${identity.agentId})`);
        results.push({
          name,
          address,
          agentId: identity.agentId || null,
          network,
          txHash: null,
          status: "already_registered",
        });
        skipped++;
        continue;
      }
    }

    if (dryRun) {
      console.log(`  [${index}] ${name}: would register ${address} on ${network}`);
      results.push({
        name,
        address,
        agentId: null,
        network,
        txHash: null,
        status: "success",
      });
      registered++;
      continue;
    }

    // Register
    try {
      console.log(`  [${index}] ${name}: registering ${address} on ${network}...`);
      const result = await registerAgent(address, name, network);
      console.log(`         Agent #${result.agentId} — TX: ${result.txHash}`);
      results.push({
        name,
        address,
        agentId: result.agentId,
        network,
        txHash: result.txHash,
        status: "success",
      });
      registered++;
    } catch (err: any) {
      console.error(`         FAILED: ${err.message}`);
      results.push({
        name,
        address,
        agentId: null,
        network,
        txHash: null,
        status: "failed",
        error: err.message,
      });
      failed++;
    }

    // Rate limit delay
    await new Promise((r) => setTimeout(r, DELAY_MS));
  }

  // Save report
  const report = {
    timestamp: new Date().toISOString(),
    network,
    dryRun,
    summary: {
      total: manifest.count,
      registered,
      skipped,
      failed,
    },
    results,
  };

  const reportFile = resolve(
    __dirname,
    `report-erc8004-registration-${network}-${Date.now()}.json`,
  );
  writeFileSync(reportFile, JSON.stringify(report, null, 2));

  console.log(`\n${"=".repeat(60)}`);
  console.log(`  Registration complete on ${network}`);
  console.log(`    Registered: ${registered}`);
  console.log(`    Skipped:    ${skipped} (already registered)`);
  console.log(`    Failed:     ${failed}`);
  console.log(`  Report: ${reportFile}`);
  console.log(`${"=".repeat(60)}\n`);
}

main().catch(console.error);

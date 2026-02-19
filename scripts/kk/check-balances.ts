/**
 * Karma Kadabra V2 — Task 1.7: Balance Checker
 *
 * Shows a matrix of all agent wallets across all chains.
 * Uses multicall for efficient batch reads (1 RPC call per chain).
 *
 * Usage:
 *   npx tsx check-balances.ts --config config/wallets.json
 *   npx tsx check-balances.ts --config config/wallets.json --chain base
 *   npx tsx check-balances.ts --config config/wallets.json --json
 */

import {
  createPublicClient,
  http,
  formatUnits,
  formatEther,
  getAddress,
  type Address,
} from "viem";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { config } from "dotenv";
import { CHAINS, ERC20_ABI, getChainNames } from "./lib/chains.js";
import type { WalletManifest } from "./generate-wallets.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env.local") });

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BalanceRow {
  name: string;
  address: string;
  chain: string;
  usdc: string;
  native: string;
  funded: boolean;
}

// ---------------------------------------------------------------------------
// Balance Check
// ---------------------------------------------------------------------------

async function checkChain(
  chainName: string,
  wallets: Array<{ name: string; address: Address }>,
): Promise<BalanceRow[]> {
  const chainInfo = CHAINS[chainName];
  if (!chainInfo) throw new Error(`Unknown chain: ${chainName}`);

  const client = createPublicClient({
    chain: chainInfo.chain,
    transport: http(chainInfo.rpcUrl),
    batch: { multicall: true },
  });

  // Batch read all balances via multicall
  const [usdcBalances, nativeBalances] = await Promise.all([
    Promise.all(
      wallets.map((w) =>
        client.readContract({
          address: chainInfo.usdc,
          abi: ERC20_ABI,
          functionName: "balanceOf",
          args: [w.address],
        }),
      ),
    ),
    Promise.all(
      wallets.map((w) => client.getBalance({ address: w.address })),
    ),
  ]);

  return wallets.map((w, i) => ({
    name: w.name,
    address: w.address,
    chain: chainName,
    usdc: formatUnits(usdcBalances[i], 6),
    native: formatEther(nativeBalances[i]),
    funded: usdcBalances[i] > 0n || nativeBalances[i] > 0n,
  }));
}

// ---------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------

function displayTable(rows: BalanceRow[], chainName: string): void {
  const chainInfo = CHAINS[chainName];
  console.log(`\n${"=".repeat(80)}`);
  console.log(`  ${chainInfo.name} (${chainInfo.chainId}) — ${chainInfo.nativeSymbol}`);
  console.log(`${"=".repeat(80)}`);

  const funded = rows.filter((r) => r.funded).length;
  const unfunded = rows.length - funded;

  console.log(
    `  ${"Name".padEnd(25)} ${"USDC".padStart(12)} ${"Native".padStart(15)} Status`,
  );
  console.log(`  ${"─".repeat(70)}`);

  for (const r of rows) {
    const status = r.funded ? "[OK]" : "[--]";
    const nativeStr = `${r.native} ${chainInfo.nativeSymbol}`;
    console.log(
      `  ${r.name.padEnd(25)} ${r.usdc.padStart(12)} ${nativeStr.padStart(15)} ${status}`,
    );
  }

  console.log(`\n  Summary: ${funded} funded, ${unfunded} unfunded`);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);

  const configIdx = args.indexOf("--config");
  const configFile = configIdx >= 0
    ? args[configIdx + 1]
    : resolve(__dirname, "config", "wallets.json");

  const chainFilter = args.includes("--chain")
    ? args[args.indexOf("--chain") + 1]
    : null;

  const jsonOutput = args.includes("--json");

  // Load wallet manifest
  let manifest: WalletManifest;
  try {
    manifest = JSON.parse(readFileSync(configFile, "utf-8"));
  } catch {
    console.error(`ERROR: Cannot read wallet manifest at ${configFile}`);
    console.error("Run generate-wallets.ts first.");
    process.exit(1);
  }

  const wallets = manifest.wallets.map((w) => ({
    name: w.name,
    address: getAddress(w.address) as Address,
  }));

  console.log(`\nChecking ${wallets.length} wallets across ${chainFilter || "all"} chains...\n`);

  const chains = chainFilter ? [chainFilter] : getChainNames();
  const allRows: BalanceRow[] = [];

  for (const chainName of chains) {
    try {
      const rows = await checkChain(chainName, wallets);
      allRows.push(...rows);

      if (!jsonOutput) {
        displayTable(rows, chainName);
      }
    } catch (err: any) {
      console.error(`  ERROR on ${chainName}: ${err.message}`);
    }
  }

  if (jsonOutput) {
    console.log(JSON.stringify(allRows, null, 2));
  }

  // Summary
  if (!jsonOutput) {
    const totalFunded = allRows.filter((r) => r.funded).length;
    const totalSlots = allRows.length;
    console.log(`\n${"=".repeat(80)}`);
    console.log(`  TOTAL: ${totalFunded}/${totalSlots} wallet-chain slots funded`);
    console.log(`${"=".repeat(80)}\n`);
  }
}

main().catch(console.error);

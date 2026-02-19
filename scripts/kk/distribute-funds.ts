/**
 * Karma Kadabra V2 — Task 1.2 + 1.3: Same-Chain Batch Distribution
 *
 * Distributes USDC + native gas tokens to N wallets on a SINGLE chain.
 * Uses Disperse.app (1 TX for all recipients) where available,
 * falls back to sequential transfers where Disperse isn't deployed.
 *
 * Usage:
 *   npx tsx distribute-funds.ts --chain base --wallets config/wallets.json --usdc 3.00 --gas 0.0005
 *   npx tsx distribute-funds.ts --chain base --wallets config/wallets.json --dry-run
 */

import {
  createPublicClient,
  createWalletClient,
  http,
  parseUnits,
  parseEther,
  formatUnits,
  formatEther,
  getAddress,
  type Address,
  type Hex,
} from "viem";
import { privateKeyToAccount, nonceManager } from "viem/accounts";
import { readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { config } from "dotenv";
import {
  CHAINS,
  DISPERSE_ADDRESS,
  DISPERSE_ABI,
  ERC20_ABI,
  getChain,
} from "./lib/chains.js";
import type { WalletManifest } from "./generate-wallets.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env.local") });

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TxResult {
  type: "approve" | "usdc_batch" | "native_batch" | "usdc_single" | "native_single";
  txHash: string;
  recipients: number;
  amount: string;
  status: "confirmed" | "failed";
  error?: string;
}

// ---------------------------------------------------------------------------
// Distribution
// ---------------------------------------------------------------------------

async function distribute(
  chainName: string,
  wallets: Array<{ name: string; address: Address }>,
  usdcPerWallet: string,
  gasPerWallet: string,
  dryRun: boolean,
): Promise<TxResult[]> {
  const chainInfo = getChain(chainName);
  const results: TxResult[] = [];

  const privateKey = (process.env.WALLET_PRIVATE_KEY || process.env.PRIVATE_KEY) as Hex;
  if (!privateKey) {
    console.error("ERROR: WALLET_PRIVATE_KEY not set in .env.local");
    process.exit(1);
  }

  const account = privateKeyToAccount(privateKey, { nonceManager });

  const publicClient = createPublicClient({
    chain: chainInfo.chain,
    transport: http(chainInfo.rpcUrl),
    batch: { multicall: true },
  });

  const walletClient = createWalletClient({
    account,
    chain: chainInfo.chain,
    transport: http(chainInfo.rpcUrl),
  });

  // Calculate totals
  const usdcAmount = parseUnits(usdcPerWallet, 6);
  const gasAmount = parseEther(gasPerWallet);
  const totalUsdc = usdcAmount * BigInt(wallets.length);
  const totalGas = gasAmount * BigInt(wallets.length);
  const addresses = wallets.map((w) => w.address);
  const usdcAmounts = wallets.map(() => usdcAmount);
  const gasAmounts = wallets.map(() => gasAmount);

  // Check balances
  const [nativeBalance, usdcBalance] = await Promise.all([
    publicClient.getBalance({ address: account.address }),
    publicClient.readContract({
      address: chainInfo.usdc,
      abi: ERC20_ABI,
      functionName: "balanceOf",
      args: [account.address],
    }),
  ]);

  console.log(`\n--- ${chainInfo.name} (${wallets.length} wallets) ---`);
  console.log(`  Funder:     ${account.address}`);
  console.log(`  USDC bal:   ${formatUnits(usdcBalance, 6)}`);
  console.log(`  Native bal: ${formatEther(nativeBalance)} ${chainInfo.nativeSymbol}`);
  console.log(`  Need USDC:  ${formatUnits(totalUsdc, 6)}`);
  console.log(`  Need gas:   ${formatEther(totalGas)} ${chainInfo.nativeSymbol}`);

  if (usdcBalance < totalUsdc) {
    console.error(`  INSUFFICIENT USDC: need ${formatUnits(totalUsdc, 6)}, have ${formatUnits(usdcBalance, 6)}`);
    return results;
  }

  // Add gas buffer for the distribution TXs themselves
  const gasBuffer = parseEther("0.005");
  if (nativeBalance < totalGas + gasBuffer) {
    console.error(`  INSUFFICIENT NATIVE: need ${formatEther(totalGas + gasBuffer)}, have ${formatEther(nativeBalance)}`);
    return results;
  }

  if (dryRun) {
    console.log(`  [DRY RUN] Would distribute ${formatUnits(totalUsdc, 6)} USDC + ${formatEther(totalGas)} ${chainInfo.nativeSymbol}`);
    return results;
  }

  // --- Execute ---
  if (chainInfo.disperseAvailable) {
    // DISPERSE PATH — 3 TXs total
    console.log(`  Using Disperse.app (batch mode)...`);

    // 1. Approve USDC
    console.log(`  [1/3] Approving ${formatUnits(totalUsdc, 6)} USDC...`);
    try {
      const approveTx = await walletClient.writeContract({
        address: chainInfo.usdc,
        abi: ERC20_ABI,
        functionName: "approve",
        args: [DISPERSE_ADDRESS, totalUsdc],
      });
      await publicClient.waitForTransactionReceipt({ hash: approveTx });
      console.log(`        TX: ${approveTx}`);
      results.push({ type: "approve", txHash: approveTx, recipients: 1, amount: formatUnits(totalUsdc, 6), status: "confirmed" });
    } catch (err: any) {
      console.error(`  APPROVE FAILED: ${err.message}`);
      results.push({ type: "approve", txHash: "", recipients: 1, amount: "0", status: "failed", error: err.message });
      return results;
    }

    // 2. Disperse USDC
    console.log(`  [2/3] Dispersing USDC to ${addresses.length} wallets...`);
    try {
      const usdcTx = await walletClient.writeContract({
        address: DISPERSE_ADDRESS,
        abi: DISPERSE_ABI,
        functionName: "disperseToken",
        args: [chainInfo.usdc, addresses, usdcAmounts],
      });
      await publicClient.waitForTransactionReceipt({ hash: usdcTx });
      console.log(`        TX: ${usdcTx}`);
      results.push({ type: "usdc_batch", txHash: usdcTx, recipients: addresses.length, amount: formatUnits(totalUsdc, 6), status: "confirmed" });
    } catch (err: any) {
      console.error(`  USDC DISPERSE FAILED: ${err.message}`);
      results.push({ type: "usdc_batch", txHash: "", recipients: 0, amount: "0", status: "failed", error: err.message });
      return results;
    }

    // 3. Disperse native gas
    if (gasAmount > 0n) {
      console.log(`  [3/3] Dispersing ${chainInfo.nativeSymbol} to ${addresses.length} wallets...`);
      try {
        const nativeTx = await walletClient.writeContract({
          address: DISPERSE_ADDRESS,
          abi: DISPERSE_ABI,
          functionName: "disperseEther",
          args: [addresses, gasAmounts],
          value: totalGas,
        });
        await publicClient.waitForTransactionReceipt({ hash: nativeTx });
        console.log(`        TX: ${nativeTx}`);
        results.push({ type: "native_batch", txHash: nativeTx, recipients: addresses.length, amount: formatEther(totalGas), status: "confirmed" });
      } catch (err: any) {
        console.error(`  NATIVE DISPERSE FAILED: ${err.message}`);
        results.push({ type: "native_batch", txHash: "", recipients: 0, amount: "0", status: "failed", error: err.message });
      }
    }
  } else {
    // SEQUENTIAL FALLBACK — N+N TXs
    console.log(`  Using sequential transfers (Disperse not available on ${chainName})...`);

    // USDC transfers
    for (let i = 0; i < wallets.length; i++) {
      try {
        console.log(`  [USDC ${i + 1}/${wallets.length}] ${formatUnits(usdcAmount, 6)} -> ${wallets[i].name}`);
        const tx = await walletClient.writeContract({
          address: chainInfo.usdc,
          abi: ERC20_ABI,
          functionName: "transfer",
          args: [wallets[i].address, usdcAmount],
        });
        results.push({ type: "usdc_single", txHash: tx, recipients: 1, amount: formatUnits(usdcAmount, 6), status: "confirmed" });
      } catch (err: any) {
        console.error(`    FAILED: ${err.message}`);
        results.push({ type: "usdc_single", txHash: "", recipients: 1, amount: "0", status: "failed", error: err.message });
      }
    }

    // Native transfers
    if (gasAmount > 0n) {
      for (let i = 0; i < wallets.length; i++) {
        try {
          console.log(`  [GAS ${i + 1}/${wallets.length}] ${formatEther(gasAmount)} -> ${wallets[i].name}`);
          const tx = await walletClient.sendTransaction({
            to: wallets[i].address,
            value: gasAmount,
          });
          results.push({ type: "native_single", txHash: tx, recipients: 1, amount: formatEther(gasAmount), status: "confirmed" });
        } catch (err: any) {
          console.error(`    FAILED: ${err.message}`);
          results.push({ type: "native_single", txHash: "", recipients: 1, amount: "0", status: "failed", error: err.message });
        }
      }
    }
  }

  const success = results.filter((r) => r.status === "confirmed").length;
  console.log(`\n  Done: ${success}/${results.length} TXs confirmed on ${chainName}`);
  return results;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);

  const chainName = args.includes("--chain") ? args[args.indexOf("--chain") + 1] : "base";
  const walletsFile = args.includes("--wallets")
    ? args[args.indexOf("--wallets") + 1]
    : resolve(__dirname, "config", "wallets.json");
  const usdcPerWallet = args.includes("--usdc") ? args[args.indexOf("--usdc") + 1] : "3.00";
  const gasPerWallet = args.includes("--gas") ? args[args.indexOf("--gas") + 1] : "0.0005";
  const dryRun = args.includes("--dry-run");

  // Load wallets
  let manifest: WalletManifest;
  try {
    manifest = JSON.parse(readFileSync(walletsFile, "utf-8"));
  } catch {
    console.error(`ERROR: Cannot read ${walletsFile}. Run generate-wallets.ts first.`);
    process.exit(1);
  }

  const wallets = manifest.wallets.map((w) => ({
    name: w.name,
    address: getAddress(w.address) as Address,
  }));

  console.log(`\nDistributing to ${wallets.length} wallets on ${chainName}`);
  console.log(`  USDC/wallet: ${usdcPerWallet}`);
  console.log(`  Gas/wallet:  ${gasPerWallet}`);
  if (dryRun) console.log(`  ** DRY RUN **`);

  const results = await distribute(chainName, wallets, usdcPerWallet, gasPerWallet, dryRun);

  // Save report
  const report = {
    timestamp: new Date().toISOString(),
    chain: chainName,
    walletCount: wallets.length,
    usdcPerWallet,
    gasPerWallet,
    dryRun,
    results,
  };
  const reportFile = resolve(__dirname, `report-distribute-${chainName}-${Date.now()}.json`);
  writeFileSync(reportFile, JSON.stringify(report, null, 2));
  console.log(`\nReport: ${reportFile}`);
}

main().catch(console.error);

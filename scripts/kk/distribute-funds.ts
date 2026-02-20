/**
 * Karma Kadabra V2 — Multi-Token Batch Distribution
 *
 * Distributes multiple stablecoins + native gas tokens to N wallets on a SINGLE chain.
 * Uses Disperse.app (1 TX for all recipients) where available,
 * falls back to sequential transfers where Disperse isn't deployed.
 *
 * Usage:
 *   npx tsx distribute-funds.ts --chain base --wallets config/wallets.json --amount 3.00 --gas 0.0005
 *   npx tsx distribute-funds.ts --chain arbitrum --tokens USDC,AUSD --amount 1.00
 *   npx tsx distribute-funds.ts --chain base --wallets config/wallets.json --dry-run
 *   npx tsx distribute-funds.ts --chain polygon --tokens USDC --usdc 5.00  # --usdc is alias for --amount
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
  DISPERSE_ADDRESS,
  DISPERSE_ABI,
  ERC20_ABI,
  getChain,
  getTokens,
  getTokenSymbols,
  type TokenInfo,
} from "./lib/chains.js";
import type { WalletManifest } from "./generate-wallets.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env.local") });

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TxResult {
  type: "approve" | "token_batch" | "native_batch" | "token_single" | "native_single";
  txHash: string;
  recipients: number;
  amount: string;
  token?: string;
  status: "confirmed" | "failed";
  error?: string;
}

interface TokenDistResult {
  symbol: string;
  address: string;
  decimals: number;
  amountPerWallet: string;
  totalAmount: string;
  txs: TxResult[];
}

// ---------------------------------------------------------------------------
// Distribution (multi-token)
// ---------------------------------------------------------------------------

async function distribute(
  chainName: string,
  wallets: Array<{ name: string; address: Address }>,
  tokensToDistribute: TokenInfo[],
  amountPerWallet: string,
  gasPerWallet: string,
  dryRun: boolean,
): Promise<{ tokenResults: TokenDistResult[]; gasResults: TxResult[] }> {
  const chainInfo = getChain(chainName);
  const tokenResults: TokenDistResult[] = [];
  const gasResults: TxResult[] = [];

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

  const addresses = wallets.map((w) => w.address);
  const gasAmount = parseEther(gasPerWallet);
  const totalGas = gasAmount * BigInt(wallets.length);

  // Check native balance upfront
  const nativeBalance = await publicClient.getBalance({ address: account.address });

  console.log(`\n=== ${chainInfo.name} (${wallets.length} wallets, ${tokensToDistribute.length} token(s)) ===`);
  console.log(`  Funder:     ${account.address}`);
  console.log(`  Native bal: ${formatEther(nativeBalance)} ${chainInfo.nativeSymbol}`);
  console.log(`  Need gas:   ${formatEther(totalGas)} ${chainInfo.nativeSymbol}`);
  console.log(`  Tokens:     ${tokensToDistribute.map((t) => t.symbol).join(", ")}`);

  // ---- Distribute each token ----
  for (const token of tokensToDistribute) {
    console.log(`\n--- ${token.symbol} (${token.name}) ---`);

    const tokenAmount = parseUnits(amountPerWallet, token.decimals);
    const totalToken = tokenAmount * BigInt(wallets.length);
    const tokenAmounts = wallets.map(() => tokenAmount);

    const tokenBalance = (await publicClient.readContract({
      address: token.address,
      abi: ERC20_ABI,
      functionName: "balanceOf",
      args: [account.address],
    })) as bigint;

    console.log(`  ${token.symbol} bal:  ${formatUnits(tokenBalance, token.decimals)}`);
    console.log(`  Need:       ${formatUnits(totalToken, token.decimals)}`);

    const result: TokenDistResult = {
      symbol: token.symbol,
      address: token.address,
      decimals: token.decimals,
      amountPerWallet,
      totalAmount: formatUnits(totalToken, token.decimals),
      txs: [],
    };

    if (tokenBalance < totalToken) {
      console.error(`  INSUFFICIENT ${token.symbol}: need ${formatUnits(totalToken, token.decimals)}, have ${formatUnits(tokenBalance, token.decimals)}`);
      tokenResults.push(result);
      continue;
    }

    if (dryRun) {
      console.log(`  [DRY RUN] Would distribute ${formatUnits(totalToken, token.decimals)} ${token.symbol}`);
      tokenResults.push(result);
      continue;
    }

    // --- Execute token distribution ---
    if (chainInfo.disperseAvailable) {
      console.log(`  Using Disperse.app (batch mode)...`);

      // 1. Approve
      console.log(`  [1/2] Approving ${formatUnits(totalToken, token.decimals)} ${token.symbol}...`);
      try {
        const approveTx = await walletClient.writeContract({
          address: token.address,
          abi: ERC20_ABI,
          functionName: "approve",
          args: [DISPERSE_ADDRESS, totalToken],
        });
        await publicClient.waitForTransactionReceipt({ hash: approveTx });
        console.log(`        TX: ${approveTx}`);
        result.txs.push({ type: "approve", txHash: approveTx, recipients: 1, amount: formatUnits(totalToken, token.decimals), token: token.symbol, status: "confirmed" });
      } catch (err: any) {
        console.error(`  APPROVE FAILED: ${err.message}`);
        result.txs.push({ type: "approve", txHash: "", recipients: 1, amount: "0", token: token.symbol, status: "failed", error: err.message });
        tokenResults.push(result);
        continue;
      }

      // 2. Disperse token
      console.log(`  [2/2] Dispersing ${token.symbol} to ${addresses.length} wallets...`);
      try {
        const tokenTx = await walletClient.writeContract({
          address: DISPERSE_ADDRESS,
          abi: DISPERSE_ABI,
          functionName: "disperseToken",
          args: [token.address, addresses, tokenAmounts],
        });
        await publicClient.waitForTransactionReceipt({ hash: tokenTx });
        console.log(`        TX: ${tokenTx}`);
        result.txs.push({ type: "token_batch", txHash: tokenTx, recipients: addresses.length, amount: formatUnits(totalToken, token.decimals), token: token.symbol, status: "confirmed" });
      } catch (err: any) {
        console.error(`  ${token.symbol} DISPERSE FAILED: ${err.message}`);
        result.txs.push({ type: "token_batch", txHash: "", recipients: 0, amount: "0", token: token.symbol, status: "failed", error: err.message });
      }
    } else {
      // SEQUENTIAL FALLBACK
      console.log(`  Using sequential transfers (Disperse not available on ${chainName})...`);

      for (let i = 0; i < wallets.length; i++) {
        try {
          console.log(`  [${token.symbol} ${i + 1}/${wallets.length}] ${formatUnits(tokenAmount, token.decimals)} -> ${wallets[i].name}`);
          const tx = await walletClient.writeContract({
            address: token.address,
            abi: ERC20_ABI,
            functionName: "transfer",
            args: [wallets[i].address, tokenAmount],
          });
          await publicClient.waitForTransactionReceipt({ hash: tx });
          result.txs.push({ type: "token_single", txHash: tx, recipients: 1, amount: formatUnits(tokenAmount, token.decimals), token: token.symbol, status: "confirmed" });
        } catch (err: any) {
          console.error(`    FAILED: ${err.message}`);
          result.txs.push({ type: "token_single", txHash: "", recipients: 1, amount: "0", token: token.symbol, status: "failed", error: err.message });
        }
      }
    }

    tokenResults.push(result);
  }

  // ---- Distribute native gas (once, after all tokens) ----
  if (gasAmount > 0n) {
    const gasBuffer = parseEther("0.005");
    if (nativeBalance < totalGas + gasBuffer) {
      console.error(`\n  INSUFFICIENT NATIVE: need ${formatEther(totalGas + gasBuffer)}, have ${formatEther(nativeBalance)}`);
    } else if (dryRun) {
      console.log(`\n  [DRY RUN] Would distribute ${formatEther(totalGas)} ${chainInfo.nativeSymbol}`);
    } else {
      console.log(`\n--- ${chainInfo.nativeSymbol} (gas) ---`);

      if (chainInfo.disperseAvailable) {
        console.log(`  Dispersing ${chainInfo.nativeSymbol} to ${addresses.length} wallets...`);
        const gasAmounts = wallets.map(() => gasAmount);
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
          gasResults.push({ type: "native_batch", txHash: nativeTx, recipients: addresses.length, amount: formatEther(totalGas), status: "confirmed" });
        } catch (err: any) {
          console.error(`  NATIVE DISPERSE FAILED: ${err.message}`);
          gasResults.push({ type: "native_batch", txHash: "", recipients: 0, amount: "0", status: "failed", error: err.message });
        }
      } else {
        for (let i = 0; i < wallets.length; i++) {
          try {
            console.log(`  [GAS ${i + 1}/${wallets.length}] ${formatEther(gasAmount)} -> ${wallets[i].name}`);
            const tx = await walletClient.sendTransaction({
              to: wallets[i].address,
              value: gasAmount,
            });
            await publicClient.waitForTransactionReceipt({ hash: tx });
            gasResults.push({ type: "native_single", txHash: tx, recipients: 1, amount: formatEther(gasAmount), status: "confirmed" });
          } catch (err: any) {
            console.error(`    FAILED: ${err.message}`);
            gasResults.push({ type: "native_single", txHash: "", recipients: 1, amount: "0", status: "failed", error: err.message });
          }
        }
      }
    }
  }

  // Summary
  const allTxs = [...tokenResults.flatMap((t) => t.txs), ...gasResults];
  const success = allTxs.filter((r) => r.status === "confirmed").length;
  console.log(`\n  Done: ${success}/${allTxs.length} TXs confirmed on ${chainName}`);

  return { tokenResults, gasResults };
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

  // --amount is the primary flag, --usdc is a backward-compat alias
  const amountPerWallet = args.includes("--amount")
    ? args[args.indexOf("--amount") + 1]
    : args.includes("--usdc")
      ? args[args.indexOf("--usdc") + 1]
      : "1.00";

  const gasPerWallet = args.includes("--gas") ? args[args.indexOf("--gas") + 1] : "0.0005";
  const dryRun = args.includes("--dry-run");

  // --tokens flag: comma-separated list, or default to ALL tokens on chain
  const availableSymbols = getTokenSymbols(chainName);
  let selectedSymbols: string[];

  if (args.includes("--tokens")) {
    const raw = args[args.indexOf("--tokens") + 1];
    selectedSymbols = raw.split(",").map((s) => s.trim().toUpperCase());
    // Validate
    for (const sym of selectedSymbols) {
      if (!availableSymbols.includes(sym)) {
        console.error(`ERROR: Token ${sym} not available on ${chainName}. Available: ${availableSymbols.join(", ")}`);
        process.exit(1);
      }
    }
  } else {
    selectedSymbols = availableSymbols;
  }

  const tokensToDistribute = getTokens(chainName).filter((t) => selectedSymbols.includes(t.symbol));

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
  console.log(`  Tokens:       ${tokensToDistribute.map((t) => t.symbol).join(", ")}`);
  console.log(`  Amount/token: ${amountPerWallet}`);
  console.log(`  Gas/wallet:   ${gasPerWallet}`);
  if (dryRun) console.log(`  ** DRY RUN **`);

  const { tokenResults, gasResults } = await distribute(
    chainName,
    wallets,
    tokensToDistribute,
    amountPerWallet,
    gasPerWallet,
    dryRun,
  );

  // Save report
  const report = {
    timestamp: new Date().toISOString(),
    chain: chainName,
    walletCount: wallets.length,
    amountPerWallet,
    gasPerWallet,
    dryRun,
    tokens: tokenResults,
    gas: gasResults,
  };
  const reportFile = resolve(__dirname, `report-distribute-${chainName}-${Date.now()}.json`);
  writeFileSync(reportFile, JSON.stringify(report, null, 2));
  console.log(`\nReport: ${reportFile}`);
}

main().catch(console.error);

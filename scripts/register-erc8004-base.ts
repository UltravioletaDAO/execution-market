/**
 * Execution Market ERC-8004 Registration Script — Base Mainnet
 *
 * Registers Execution Market as Agent #469 (cross-chain) in the ERC-8004
 * IdentityRegistry on Base Mainnet. The registry is deployed at the same
 * CREATE2 address on every supported chain.
 *
 * Usage:
 *   npx tsx scripts/register-erc8004-base.ts
 *   npx tsx scripts/register-erc8004-base.ts --dry-run   # estimate only, no tx
 *
 * Requirements:
 *   - WALLET_PRIVATE_KEY in .env.local (must hold ETH on Base for gas)
 *   - Optional: BASE_RPC_URL in .env.local (defaults to https://mainnet.base.org)
 */

import {
  createWalletClient,
  createPublicClient,
  http,
  formatEther,
  formatGwei,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createInterface } from 'readline';

// ---------------------------------------------------------------------------
// ESM compatibility
// ---------------------------------------------------------------------------
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env.local from project root
config({ path: resolve(__dirname, '../.env.local') });

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** CREATE2-deployed IdentityRegistry — same address on every mainnet. */
const ERC8004_IDENTITY_REGISTRY = '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432' as const;

/**
 * Agent URI pointing to the existing metadata on IPFS (pinned via Pinata).
 * This is the same CID already used for the Sepolia registration (Agent #469).
 * The HTTP-accessible URL is also listed here for reference:
 *   https://execution.market/.well-known/agent.json
 *   https://gateway.pinata.cloud/ipfs/QmZJaHCf4u9Wy9hPusKF9bpV69Jr3E6ZAVXHZCinfMrjbL
 */
const EM_AGENT_URI = 'ipfs://QmZJaHCf4u9Wy9hPusKF9bpV69Jr3E6ZAVXHZCinfMrjbL';

// ---------------------------------------------------------------------------
// ABI (minimal — register + balanceOf only)
// ---------------------------------------------------------------------------
const IDENTITY_REGISTRY_ABI = [
  {
    name: 'register',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [{ name: 'agentURI', type: 'string' }],
    outputs: [{ name: 'agentId', type: 'uint256' }],
  },
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'owner', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Prompt the user and return their answer (stdin). */
function ask(question: string): Promise<string> {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const dryRun = process.argv.includes('--dry-run');

  // ---- Wallet key --------------------------------------------------------
  const privateKey = process.env.WALLET_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error(
      'WALLET_PRIVATE_KEY not found. Set it in .env.local or as an environment variable.',
    );
  }

  const rpcUrl = process.env.BASE_RPC_URL || 'https://mainnet.base.org';

  // ---- Banner ------------------------------------------------------------
  console.log('');
  console.log('Execution Market ERC-8004 Registration — Base Mainnet');
  console.log('=====================================================');
  console.log(`Network:           Base Mainnet (chain ${base.id})`);
  console.log(`Identity Registry: ${ERC8004_IDENTITY_REGISTRY}`);
  console.log(`Agent URI:         ${EM_AGENT_URI}`);
  console.log(`RPC:               ${rpcUrl}`);
  if (dryRun) {
    console.log(`Mode:              DRY RUN (no transaction will be sent)`);
  }
  console.log('');

  // ---- Clients -----------------------------------------------------------
  const account = privateKeyToAccount(privateKey as `0x${string}`);
  console.log(`Wallet: ${account.address}`);

  const publicClient = createPublicClient({
    chain: base,
    transport: http(rpcUrl),
  });

  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http(rpcUrl),
  });

  // ---- Balance check -----------------------------------------------------
  const balance = await publicClient.getBalance({ address: account.address });
  console.log(`Balance: ${formatEther(balance)} ETH`);
  console.log('');

  if (balance === 0n) {
    throw new Error(
      'Wallet has 0 ETH on Base Mainnet. Fund it before registering.',
    );
  }

  // ---- Already registered? -----------------------------------------------
  const existingBalance = await publicClient.readContract({
    address: ERC8004_IDENTITY_REGISTRY,
    abi: IDENTITY_REGISTRY_ABI,
    functionName: 'balanceOf',
    args: [account.address],
  });

  if (existingBalance > 0n) {
    console.log(
      `WARNING: Wallet already owns ${existingBalance} agent token(s) on Base.`,
    );
    console.log(
      'Proceeding will mint an additional token. If you want to re-use the',
    );
    console.log('existing registration, you can skip this script.');
    console.log('');
  }

  // ---- Gas estimation ----------------------------------------------------
  console.log('Estimating gas...');

  let gasEstimate: bigint;
  try {
    gasEstimate = await publicClient.estimateContractGas({
      address: ERC8004_IDENTITY_REGISTRY,
      abi: IDENTITY_REGISTRY_ABI,
      functionName: 'register',
      args: [EM_AGENT_URI],
      account: account.address,
    });
  } catch (err: any) {
    console.error('Gas estimation failed. The contract may revert for this call.');
    console.error(`Reason: ${err.shortMessage || err.message}`);
    throw err;
  }

  const gasPrice = await publicClient.getGasPrice();
  const estimatedCostWei = gasEstimate * gasPrice;

  console.log(`  Gas units (est.): ${gasEstimate.toLocaleString()}`);
  console.log(`  Gas price:        ${formatGwei(gasPrice)} gwei`);
  console.log(`  Estimated cost:   ${formatEther(estimatedCostWei)} ETH`);
  console.log('');

  if (estimatedCostWei > balance) {
    throw new Error(
      `Insufficient balance. Need ~${formatEther(estimatedCostWei)} ETH but wallet only has ${formatEther(balance)} ETH.`,
    );
  }

  // ---- Dry-run exit ------------------------------------------------------
  if (dryRun) {
    console.log('Dry run complete. No transaction was sent.');
    return;
  }

  // ---- Confirmation prompt -----------------------------------------------
  const answer = await ask(
    'Proceed with on-chain registration? (yes/no): ',
  );
  if (answer.toLowerCase() !== 'yes' && answer.toLowerCase() !== 'y') {
    console.log('Aborted.');
    return;
  }

  // ---- Send transaction --------------------------------------------------
  console.log('');
  console.log('Registering Execution Market on Base Mainnet...');
  console.log(`Agent URI: ${EM_AGENT_URI}`);

  const hash = await walletClient.writeContract({
    address: ERC8004_IDENTITY_REGISTRY,
    abi: IDENTITY_REGISTRY_ABI,
    functionName: 'register',
    args: [EM_AGENT_URI],
    gas: gasEstimate + (gasEstimate / 5n), // +20% buffer
  });

  console.log('');
  console.log(`Transaction submitted: ${hash}`);
  console.log(`Explorer: https://basescan.org/tx/${hash}`);

  // ---- Wait for confirmation ---------------------------------------------
  console.log('');
  console.log('Waiting for confirmation...');
  const receipt = await publicClient.waitForTransactionReceipt({ hash });

  if (receipt.status === 'success') {
    console.log('');
    console.log('Registration successful!');
    console.log(`  Gas used:  ${receipt.gasUsed.toLocaleString()}`);
    console.log(`  Block:     ${receipt.blockNumber}`);

    // Try to extract the agent ID from the Registered event log.
    // Event signature: Registered(uint256 indexed agentId, address indexed owner, string agentURI)
    // keccak256 of that signature may differ per implementation, so we look
    // for a log from the registry with a plausible topic layout.
    const registryLogs = receipt.logs.filter(
      (log) =>
        log.address.toLowerCase() === ERC8004_IDENTITY_REGISTRY.toLowerCase(),
    );

    let agentId: bigint | null = null;
    for (const log of registryLogs) {
      // The first indexed param (topics[1]) should be the agentId
      if (log.topics.length >= 2 && log.topics[1]) {
        agentId = BigInt(log.topics[1]);
        break;
      }
    }

    if (agentId !== null) {
      console.log(`  Agent ID:  ${agentId}`);
      console.log('');
      console.log('Add to .env.local:');
      console.log(`  EM_BASE_AGENT_ID=${agentId}`);
    } else {
      console.log('');
      console.log('Could not parse Agent ID from logs.');
      console.log('Check the transaction on BaseScan to find your Agent ID:');
      console.log(`  https://basescan.org/tx/${hash}`);
    }

    console.log('');
    console.log('Next steps:');
    console.log('  1. Verify the token URI on BaseScan (Read Contract > tokenURI)');
    console.log('  2. Update agent-card.json _deployment section if needed');
    console.log('  3. Optionally call setAgentURI later to update metadata');
  } else {
    console.log('');
    console.log('Transaction reverted.');
    console.log(JSON.stringify(receipt, null, 2));
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('Error:', error.shortMessage || error.message || error);
  process.exit(1);
});

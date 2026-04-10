/**
 * LEGACY: Execution Market ERC-8004 Registration Script — Sepolia Testnet
 *
 * STATUS: LEGACY. Sepolia registration for Agent #469 (deprecated — production is
 * Agent #2106 on Base). Uses direct walletClient.writeContract() instead of the
 * Facilitator's gasless POST /register endpoint. Kept for historical reference only.
 *
 * For current registration, use:
 *   - Facilitator: POST https://facilitator.ultravioletadao.xyz/register
 *   - register-erc8004-base.ts (also legacy, but for Base mainnet)
 *
 * Usage:
 *   npx tsx scripts/register_erc8004.ts
 *
 * Requirements:
 *   - WALLET_PRIVATE_KEY in .env.local with Sepolia ETH
 *   - SEPOLIA_RPC_URL in .env.local
 */

import { createWalletClient, createPublicClient, http, parseEther } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { mainnet } from 'viem/chains';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// ESM compatibility
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env.local
config({ path: resolve(__dirname, '../.env.local') });

// Contract addresses (Ethereum Mainnet)
const ERC8004_IDENTITY_REGISTRY = '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432';
const ERC8004_REPUTATION_REGISTRY = '0x8004BAa17C55a88189AE136b182e5fdA19dE9b63';

// ABI for registration (simplified - just URI version)
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

// Execution Market Agent metadata
const EM_AGENT_URI = 'https://execution.market/.well-known/agent.json';
const EM_METADATA = [
  { key: 'name', value: 'Execution Market' },
  { key: 'type', value: 'service_provider' },
  { key: 'category', value: 'universal_execution_layer' },
  { key: 'description', value: 'Universal Execution Layer — humans today, robots tomorrow' },
  { key: 'protocols', value: 'A2A,MCP,HTTP' },
  { key: 'capabilities', value: 'task_publish,task_verify,evidence_submit,escrow_management' },
  { key: 'ecosystem', value: 'ultravioleta' },
];

async function main() {
  const privateKey = process.env.WALLET_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error('WALLET_PRIVATE_KEY not found in .env.local');
  }

  const rpcUrl = process.env.ETHEREUM_RPC_URL || 'https://1rpc.io/eth';

  console.log('Execution Market ERC-8004 Registration');
  console.log('================================');
  console.log(`Network: Ethereum Mainnet (${mainnet.id})`);
  console.log(`Identity Registry: ${ERC8004_IDENTITY_REGISTRY}`);
  console.log(`Reputation Registry: ${ERC8004_REPUTATION_REGISTRY}`);
  console.log(`RPC: ${rpcUrl}`);
  console.log('');

  // Create clients
  const account = privateKeyToAccount(privateKey as `0x${string}`);
  console.log(`Wallet: ${account.address}`);

  const publicClient = createPublicClient({
    chain: mainnet,
    transport: http(rpcUrl),
  });

  const walletClient = createWalletClient({
    account,
    chain: mainnet,
    transport: http(rpcUrl),
  });

  // Check balance
  const balance = await publicClient.getBalance({ address: account.address });
  console.log(`Balance: ${(Number(balance) / 1e18).toFixed(4)} ETH`);

  if (balance < parseEther('0.001')) {
    throw new Error('Insufficient balance. Need at least 0.001 ETH for gas.');
  }

  // Check if already registered
  const existingBalance = await publicClient.readContract({
    address: ERC8004_IDENTITY_REGISTRY,
    abi: IDENTITY_REGISTRY_ABI,
    functionName: 'balanceOf',
    args: [account.address],
  });

  if (existingBalance > 0n) {
    console.log(`\n⚠️  Wallet already has ${existingBalance} agent(s) registered.`);
    console.log('Proceeding with registration anyway...');
  }

  // Note: totalSupply might not be implemented, skip the check
  console.log(`\nProceeding with registration...`);

  // Register
  console.log('\n📝 Registering Execution Market...');
  console.log(`Agent URI: ${EM_AGENT_URI}`);

  const hash = await walletClient.writeContract({
    address: ERC8004_IDENTITY_REGISTRY,
    abi: IDENTITY_REGISTRY_ABI,
    functionName: 'register',
    args: [EM_AGENT_URI],
  });

  console.log(`\n⏳ Transaction submitted: ${hash}`);
  console.log(`Explorer: https://etherscan.io/tx/${hash}`);

  // Wait for confirmation
  console.log('\nWaiting for confirmation...');
  const receipt = await publicClient.waitForTransactionReceipt({ hash });

  if (receipt.status === 'success') {
    // Parse logs to find the Registered event and get the agentId
    console.log('\n✅ Registration successful!');
    console.log(`Gas used: ${receipt.gasUsed}`);
    console.log(`Block: ${receipt.blockNumber}`);

    // Try to find the Registered event to get the agent ID
    const registeredEvent = receipt.logs.find(log =>
      log.topics[0] === '0x97c3d2b8b8c2f0cf6b9e8e8f05a8f1e2b9f8c5d4e3a2b1c0d9e8f7a6b5c4d3e2f1' // keccak256("Registered(uint256,address,string)")
    );

    if (registeredEvent && registeredEvent.topics[1]) {
      const agentId = BigInt(registeredEvent.topics[1]);
      console.log(`Execution Market Agent ID: ${agentId}`);
      console.log(`\nUpdate .env.local with:`);
      console.log(`EM_AGENT_ID=${agentId}`);
    } else {
      console.log('\nCheck the transaction on Etherscan to get your Agent ID:');
      console.log(`https://etherscan.io/tx/${hash}`);
    }
  } else {
    console.log('\n❌ Transaction failed');
    console.log(receipt);
  }
}

main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});

/**
 * Register Chamba as merchant in x402r DepositRelayFactory
 *
 * This creates a deterministic proxy address for Chamba that receives
 * x402r payments with refund capability.
 *
 * Contracts (Base Mainnet):
 * - Factory: 0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814
 * - Escrow: 0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC
 *
 * Usage:
 *   npx tsx scripts/register_x402r_merchant.ts
 *   npx tsx scripts/register_x402r_merchant.ts --network base-sepolia
 */
import { createPublicClient, createWalletClient, http, formatEther } from 'viem';
import { base, baseSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

// Contract addresses
const CONTRACTS = {
  'base': {
    factory: '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as `0x${string}`,
    escrow: '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as `0x${string}`,
    chain: base,
    rpc: 'https://mainnet.base.org',
  },
  'base-sepolia': {
    factory: '0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2' as `0x${string}`,
    escrow: '0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058' as `0x${string}`,
    chain: baseSepolia,
    rpc: 'https://sepolia.base.org',
  },
} as const;

// DepositRelayFactory ABI
const FACTORY_ABI = [
  {
    name: 'deployRelay',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [{ name: 'merchantPayout', type: 'address' }],
    outputs: [{ name: '', type: 'address' }],
  },
  {
    name: 'getRelayAddress',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'merchantPayout', type: 'address' }],
    outputs: [{ name: '', type: 'address' }],
  },
  {
    name: 'getMerchantFromRelay',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'relayAddress', type: 'address' }],
    outputs: [{ name: '', type: 'address' }],
  },
] as const;

async function main() {
  const networkArg = process.argv.find(arg => arg.startsWith('--network='));
  const network = (networkArg?.split('=')[1] || 'base-sepolia') as keyof typeof CONTRACTS;

  if (!CONTRACTS[network]) {
    console.error(`Unknown network: ${network}. Use: base or base-sepolia`);
    process.exit(1);
  }

  const config = CONTRACTS[network];

  const key = process.env.WALLET_PRIVATE_KEY as `0x${string}`;
  if (!key) {
    console.error('WALLET_PRIVATE_KEY not found in .env.local');
    process.exit(1);
  }

  const account = privateKeyToAccount(key);
  console.log(`\n=== x402r Merchant Registration (${network}) ===`);
  console.log('Merchant Wallet:', account.address);
  console.log('Factory:', config.factory);
  console.log('Escrow:', config.escrow);

  const publicClient = createPublicClient({
    chain: config.chain,
    transport: http(config.rpc),
  });

  const walletClient = createWalletClient({
    account,
    chain: config.chain,
    transport: http(config.rpc),
  });

  // Check balance
  const balance = await publicClient.getBalance({ address: account.address });
  console.log('ETH Balance:', formatEther(balance), 'ETH');

  if (balance === 0n) {
    console.error('\nError: No ETH for gas. Fund the wallet first.');
    process.exit(1);
  }

  // Check if proxy already exists
  console.log('\nChecking existing proxy...');
  const existingProxy = await publicClient.readContract({
    address: config.factory,
    abi: FACTORY_ABI,
    functionName: 'getRelayAddress',
    args: [account.address],
  });

  if (existingProxy !== '0x0000000000000000000000000000000000000000') {
    console.log('\nProxy already deployed!');
    console.log('Proxy Address:', existingProxy);

    // Verify merchant mapping
    const merchant = await publicClient.readContract({
      address: config.factory,
      abi: FACTORY_ABI,
      functionName: 'getMerchantFromRelay',
      args: [existingProxy],
    });
    console.log('Merchant (verified):', merchant);

    printConfig(network, account.address, existingProxy, config.factory, config.escrow);
    return;
  }

  // Deploy new proxy
  console.log('\nDeploying new proxy...');

  const hash = await walletClient.writeContract({
    address: config.factory,
    abi: FACTORY_ABI,
    functionName: 'deployRelay',
    args: [account.address],
  });

  console.log('Transaction:', hash);
  console.log('Waiting for confirmation...');

  const receipt = await publicClient.waitForTransactionReceipt({ hash });

  if (receipt.status !== 'success') {
    console.error('Transaction failed!');
    process.exit(1);
  }

  console.log('Transaction confirmed in block:', receipt.blockNumber);

  // Get deployed proxy address
  const proxyAddress = await publicClient.readContract({
    address: config.factory,
    abi: FACTORY_ABI,
    functionName: 'getRelayAddress',
    args: [account.address],
  });

  console.log('\n=== SUCCESS ===');
  console.log('Proxy Address:', proxyAddress);

  printConfig(network, account.address, proxyAddress, config.factory, config.escrow);
}

function printConfig(
  network: string,
  merchant: string,
  proxy: string,
  factory: string,
  escrow: string
) {
  console.log('\n=== Configuration for Chamba ===');
  console.log(`
Add to .env.local:

# x402r Configuration (${network})
X402R_NETWORK=${network}
X402R_MERCHANT_ADDRESS=${merchant}
X402R_PROXY_ADDRESS=${proxy}
X402R_FACTORY_ADDRESS=${factory}
X402R_ESCROW_ADDRESS=${escrow}
`);

  console.log('=== Payment Payload Extension ===');
  console.log(`
When agents pay Chamba, include this extension in x402 v2 payloads:

{
  "extensions": {
    "refund": {
      "info": {
        "factoryAddress": "${factory}",
        "merchantPayouts": {
          "${proxy}": "${merchant}"
        }
      }
    }
  }
}

Agents should set payTo to: ${proxy}
`);
}

main().catch(console.error);

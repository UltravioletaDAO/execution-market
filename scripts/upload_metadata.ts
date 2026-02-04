/**
 * Execution Market Agent Metadata Upload Script
 *
 * Uploads agent metadata to IPFS via Pinata and updates the ERC-8004 agent URI.
 *
 * Usage:
 *   npx tsx scripts/upload_metadata.ts
 *
 * Requirements:
 *   - WALLET_PRIVATE_KEY in .env.local
 *   - PINATA_API_KEY and PINATA_SECRET_KEY in .env.local
 *   - EM_AGENT_ID (or CHAMBA_AGENT_ID as fallback) in .env.local
 */

import { createWalletClient, createPublicClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { sepolia } from 'viem/chains';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { readFileSync } from 'fs';

// ESM compatibility
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env.local
config({ path: resolve(__dirname, '../.env.local') });

// Load agent card from file
const AGENT_CARD_PATH = resolve(__dirname, '../agent-card.json');

// Contract addresses
const ERC8004_IDENTITY_REGISTRY = '0x8004A818BFB912233c491871b3d84c89A494BD9e';

// ABI for setAgentURI
const IDENTITY_REGISTRY_ABI = [
  {
    name: 'setAgentURI',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'agentId', type: 'uint256' },
      { name: 'newURI', type: 'string' },
    ],
    outputs: [],
  },
  {
    name: 'tokenURI',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'tokenId', type: 'uint256' }],
    outputs: [{ name: '', type: 'string' }],
  },
] as const;

// Load metadata from agent-card.json (excluding _deployment field)
function loadAgentCard(): object {
  const raw = readFileSync(AGENT_CARD_PATH, 'utf-8');
  const card = JSON.parse(raw);

  // Remove _deployment field (internal tracking, not for IPFS)
  const { _deployment, ...metadata } = card;

  // Update timestamp
  metadata.updated_at = new Date().toISOString();

  return metadata;
}

async function uploadToPinata(metadata: object): Promise<string> {
  const pinataApiKey = process.env.PINATA_API_KEY;
  const pinataSecretKey = process.env.PINATA_SECRET_KEY;

  if (!pinataApiKey || !pinataSecretKey) {
    throw new Error('PINATA_API_KEY and PINATA_SECRET_KEY required in .env.local');
  }

  console.log('📤 Uploading metadata to Pinata...');

  const response = await fetch('https://api.pinata.cloud/pinning/pinJSONToIPFS', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      pinata_api_key: pinataApiKey,
      pinata_secret_api_key: pinataSecretKey,
    },
    body: JSON.stringify({
      pinataContent: metadata,
      pinataMetadata: {
        name: 'execution-market-agent-metadata.json',
      },
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Pinata upload failed: ${error}`);
  }

  const result = await response.json();
  const ipfsHash = result.IpfsHash;
  const ipfsUri = `ipfs://${ipfsHash}`;

  console.log(`✅ Uploaded to IPFS: ${ipfsUri}`);
  console.log(`   Gateway: https://gateway.pinata.cloud/ipfs/${ipfsHash}`);

  return ipfsUri;
}

async function updateAgentURI(agentId: bigint, newUri: string): Promise<string> {
  const privateKey = process.env.WALLET_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error('WALLET_PRIVATE_KEY not found in .env.local');
  }

  const rpcUrl = process.env.SEPOLIA_RPC_URL || 'https://sepolia.drpc.org';

  const account = privateKeyToAccount(privateKey as `0x${string}`);

  const publicClient = createPublicClient({
    chain: sepolia,
    transport: http(rpcUrl),
  });

  const walletClient = createWalletClient({
    account,
    chain: sepolia,
    transport: http(rpcUrl),
  });

  console.log(`\n🔗 Updating Agent URI on-chain...`);
  console.log(`   Agent ID: ${agentId}`);
  console.log(`   New URI: ${newUri}`);

  const hash = await walletClient.writeContract({
    address: ERC8004_IDENTITY_REGISTRY,
    abi: IDENTITY_REGISTRY_ABI,
    functionName: 'setAgentURI',
    args: [agentId, newUri],
  });

  console.log(`\n⏳ Transaction submitted: ${hash}`);
  console.log(`   Explorer: https://sepolia.etherscan.io/tx/${hash}`);

  // Wait for confirmation
  console.log('\nWaiting for confirmation...');
  const receipt = await publicClient.waitForTransactionReceipt({ hash });

  if (receipt.status === 'success') {
    console.log('\n✅ Agent URI updated successfully!');
    console.log(`   Gas used: ${receipt.gasUsed}`);

    // Verify the update
    const currentUri = await publicClient.readContract({
      address: ERC8004_IDENTITY_REGISTRY,
      abi: IDENTITY_REGISTRY_ABI,
      functionName: 'tokenURI',
      args: [agentId],
    });
    console.log(`   Verified URI: ${currentUri}`);

    return hash;
  } else {
    throw new Error('Transaction failed');
  }
}

async function main() {
  const agentId = process.env.EM_AGENT_ID || process.env.CHAMBA_AGENT_ID;
  if (!agentId) {
    throw new Error('EM_AGENT_ID not found in .env.local (CHAMBA_AGENT_ID also accepted as fallback)');
  }

  console.log('🚀 Execution Market Agent Metadata Upload');
  console.log('================================');
  console.log(`Agent ID: ${agentId}`);
  console.log(`Source: ${AGENT_CARD_PATH}`);
  console.log('');

  // Load metadata from file
  const metadata = loadAgentCard();

  // Show metadata
  console.log('📋 Metadata to upload:');
  console.log(JSON.stringify(metadata, null, 2));
  console.log('');

  // Upload to IPFS
  const ipfsUri = await uploadToPinata(metadata);

  // Update on-chain
  const txHash = await updateAgentURI(BigInt(agentId), ipfsUri);

  console.log('\n🎉 Done!');
  console.log(`   IPFS URI: ${ipfsUri}`);
  console.log(`   Transaction: ${txHash}`);
}

main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});

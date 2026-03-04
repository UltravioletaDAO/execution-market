/**
 * Check wallet balances across all supported chains (EVM + Solana)
 */
import { createPublicClient, http, formatEther, formatUnits } from 'viem';
import { base, arbitrum, polygon, avalanche, mainnet, celo } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { Connection, PublicKey, LAMPORTS_PER_SOL } from '@solana/web3.js';
import { getAssociatedTokenAddressSync } from '@solana/spl-token';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

const key = process.env.WALLET_PRIVATE_KEY as `0x${string}`;
if (!key) { console.error('WALLET_PRIVATE_KEY not set'); process.exit(1); }

const account = privateKeyToAccount(key);
console.log('Wallet:', account.address);
console.log('---');

const USDC_ABI = [{ name: 'balanceOf', type: 'function', stateMutability: 'view' as const, inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }] as const;

interface ChainConfig {
  name: string;
  chain: any;
  rpc: string;
  tokens: { name: string; address: string; decimals: number }[];
}

const CHAINS: ChainConfig[] = [
  { name: 'Base', chain: base, rpc: process.env.BASE_RPC_URL || 'https://mainnet.base.org', tokens: [
    { name: 'USDC', address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6 },
    { name: 'EURC', address: '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42', decimals: 6 },
  ]},
  { name: 'Arbitrum', chain: arbitrum, rpc: process.env.ARBITRUM_RPC_URL || 'https://arb1.arbitrum.io/rpc', tokens: [
    { name: 'USDC', address: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831', decimals: 6 },
    { name: 'USDT', address: '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', decimals: 6 },
  ]},
  { name: 'Polygon', chain: polygon, rpc: process.env.POLYGON_RPC_URL || 'https://polygon-rpc.com', tokens: [
    { name: 'USDC', address: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', decimals: 6 },
  ]},
  { name: 'Avalanche', chain: avalanche, rpc: process.env.AVALANCHE_RPC_URL || 'https://api.avax.network/ext/bc/C/rpc', tokens: [
    { name: 'USDC', address: '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E', decimals: 6 },
  ]},
  { name: 'Ethereum', chain: mainnet, rpc: process.env.ETHEREUM_RPC_URL || 'https://1rpc.io/eth', tokens: [
    { name: 'USDC', address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', decimals: 6 },
    { name: 'PYUSD', address: '0x6c3ea9036406852006290770BEdFcAbA0e23A0e8', decimals: 6 },
  ]},
  { name: 'Celo', chain: celo, rpc: process.env.CELO_RPC_URL || 'https://forno.celo.org', tokens: [
    { name: 'USDC', address: '0xcebA9300f2b948710d2653dD7B07f33A8B32118C', decimals: 6 },
  ]},
];

// Solana SPL token mints (from backend NETWORK_CONFIG)
interface SolanaTokenConfig {
  name: string;
  mint: string;
  decimals: number;
}

const SOLANA_TOKENS: SolanaTokenConfig[] = [
  { name: 'USDC', mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6 },
  { name: 'AUSD', mint: 'AUSD1jCcCyPLybk1YnvPWsHQSrZ46dxwoMniN4N2UEB9', decimals: 6 },
];

async function checkChain(c: ChainConfig) {
  const client = createPublicClient({ chain: c.chain, transport: http(c.rpc) });
  try {
    const eth = await client.getBalance({ address: account.address });
    let line = `${c.name}: ${formatEther(eth)} native`;

    for (const token of c.tokens) {
      try {
        const bal = await client.readContract({
          address: token.address as `0x${string}`,
          abi: USDC_ABI,
          functionName: 'balanceOf',
          args: [account.address],
        });
        line += `, ${formatUnits(bal, token.decimals)} ${token.name}`;
      } catch { line += `, ? ${token.name}`; }
    }
    console.log(line);
  } catch (e: any) {
    console.log(`${c.name}: ERROR - ${e.message?.slice(0, 80)}`);
  }
}

async function checkSolana() {
  const solanaWallet = process.env.SOLANA_WALLET_ADDRESS;
  if (!solanaWallet) {
    console.log('Solana: SKIPPED (SOLANA_WALLET_ADDRESS not set)');
    return;
  }

  const rpcUrl = process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';
  const connection = new Connection(rpcUrl, 'confirmed');

  try {
    const owner = new PublicKey(solanaWallet);
    const lamports = await connection.getBalance(owner);
    let line = `Solana: ${(lamports / LAMPORTS_PER_SOL).toFixed(9)} SOL`;

    for (const token of SOLANA_TOKENS) {
      try {
        const mint = new PublicKey(token.mint);
        const ata = getAssociatedTokenAddressSync(mint, owner);
        const accountInfo = await connection.getTokenAccountBalance(ata);
        line += `, ${accountInfo.value.uiAmountString} ${token.name}`;
      } catch {
        line += `, 0 ${token.name}`;
      }
    }
    console.log(line);
  } catch (e: any) {
    console.log(`Solana: ERROR - ${e.message?.slice(0, 80)}`);
  }
}

async function main() {
  // EVM chains
  for (const c of CHAINS) {
    await checkChain(c);
  }
  // Solana
  await checkSolana();
}

main().catch(console.error);

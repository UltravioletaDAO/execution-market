/**
 * Check wallet balances across all supported chains
 */
import { createPublicClient, http, formatEther, formatUnits } from 'viem';
import { base, arbitrum, polygon, avalanche, mainnet, celo } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
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
  { name: 'Base', chain: base, rpc: 'https://mainnet.base.org', tokens: [
    { name: 'USDC', address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6 },
    { name: 'EURC', address: '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42', decimals: 6 },
  ]},
  { name: 'Arbitrum', chain: arbitrum, rpc: 'https://arb1.arbitrum.io/rpc', tokens: [
    { name: 'USDC', address: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831', decimals: 6 },
    { name: 'USDT', address: '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', decimals: 6 },
  ]},
  { name: 'Polygon', chain: polygon, rpc: 'https://polygon-rpc.com', tokens: [
    { name: 'USDC', address: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', decimals: 6 },
  ]},
  { name: 'Avalanche', chain: avalanche, rpc: 'https://api.avax.network/ext/bc/C/rpc', tokens: [
    { name: 'USDC', address: '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E', decimals: 6 },
  ]},
  { name: 'Ethereum', chain: mainnet, rpc: 'https://1rpc.io/eth', tokens: [
    { name: 'USDC', address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', decimals: 6 },
    { name: 'PYUSD', address: '0x6c3ea9036406852006290770BEdFcAbA0e23A0e8', decimals: 6 },
  ]},
  { name: 'Celo', chain: celo, rpc: 'https://forno.celo.org', tokens: [
    { name: 'USDC', address: '0xcebA9300f2b948710d2653dD7B07f33A8B32118C', decimals: 6 },
  ]},
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

async function main() {
  for (const c of CHAINS) {
    await checkChain(c);
  }
}

main().catch(console.error);

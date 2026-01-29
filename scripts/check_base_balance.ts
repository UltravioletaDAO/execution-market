/**
 * Check wallet balance on Ethereum mainnet
 */
import { createPublicClient, http, formatEther, formatUnits } from 'viem';
import { mainnet } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

const USDC_ETH = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const USDC_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

async function main() {
  const key = process.env.WALLET_PRIVATE_KEY as `0x${string}`;
  if (!key) {
    console.error('WALLET_PRIVATE_KEY not found');
    process.exit(1);
  }

  const account = privateKeyToAccount(key);
  console.log('=== Ethereum Mainnet Wallet ===');
  console.log('Address:', account.address);

  const client = createPublicClient({
    chain: mainnet,
    transport: http('https://1rpc.io/eth'),
  });

  const ethBal = await client.getBalance({ address: account.address });
  console.log('ETH Balance:', formatEther(ethBal), 'ETH');

  try {
    const usdcBal = await client.readContract({
      address: USDC_ETH,
      abi: USDC_ABI,
      functionName: 'balanceOf',
      args: [account.address],
    });
    console.log('USDC Balance:', formatUnits(usdcBal, 6), 'USDC');
  } catch (e) {
    console.log('USDC Balance: Error reading', (e as Error).message);
  }
}

main().catch(console.error);

/**
 * Derive address from private key
 */
import { privateKeyToAccount } from 'viem/accounts';
import { createPublicClient, http, formatEther } from 'viem';
import { mainnet } from 'viem/chains';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.unused/erc8004-pk.txt') });

// Read the key value (it's stored as PRIVATE_KEY=0x...)
const keyLine = 'PRIVATE_KEY_REMOVED';

const account = privateKeyToAccount(keyLine);
console.log('='.repeat(50));
console.log('Wallet Information');
console.log('='.repeat(50));
console.log('Address:', account.address);

const client = createPublicClient({
  chain: mainnet,
  transport: http('https://ethereum.publicnode.com'),
});

const balance = await client.getBalance({ address: account.address });
console.log('ETH Balance:', formatEther(balance), 'ETH');
console.log('='.repeat(50));

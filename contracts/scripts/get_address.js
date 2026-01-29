/**
 * Get address from private key
 */
const { ethers } = require('ethers');

const PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || 'PRIVATE_KEY_REMOVED';

async function main() {
  const wallet = new ethers.Wallet(PRIVATE_KEY);
  console.log('='.repeat(50));
  console.log('Wallet Address:', wallet.address);

  // Check balance on Ethereum mainnet
  const provider = new ethers.JsonRpcProvider('https://ethereum.publicnode.com');
  const balance = await provider.getBalance(wallet.address);
  console.log('ETH Balance:', ethers.formatEther(balance), 'ETH');
  console.log('='.repeat(50));
}

main().catch(console.error);

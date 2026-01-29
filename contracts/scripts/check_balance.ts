/**
 * Check deployer wallet balance on Ethereum mainnet
 */
import { ethers, network } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  const chainId = Number((await ethers.provider.getNetwork()).chainId);
  const balance = await ethers.provider.getBalance(deployer.address);

  console.log("=".repeat(50));
  console.log("Wallet Balance Check");
  console.log("=".repeat(50));
  console.log(`Network: ${network.name} (chainId: ${chainId})`);
  console.log(`Address: ${deployer.address}`);
  console.log(`Balance: ${ethers.formatEther(balance)} ETH`);
  console.log("=".repeat(50));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

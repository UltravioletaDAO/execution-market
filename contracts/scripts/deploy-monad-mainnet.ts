/**
 * Deploy ChambaEscrow + MockUSDC to Monad Mainnet
 * 
 * Prerequisites:
 *   1. MON tokens in wallet (bridge from ETH via gas.zip or bungee.exchange)
 *   2. PRIVATE_KEY env var set
 * 
 * Usage:
 *   cd ~/clawd/projects/execution-market/contracts
 *   PRIVATE_KEY=<key> npx hardhat run scripts/deploy-monad-mainnet.ts --network monad_mainnet
 * 
 * Or use the wrapper: ~/clawd/hackathon/moltiverse-2026/deploy-monad.sh
 */

import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  const balance = await ethers.provider.getBalance(deployer.address);
  
  console.log("=== Monad Mainnet Deployment ===");
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Balance: ${ethers.formatEther(balance)} MON`);
  
  if (balance === 0n) {
    console.error("\n❌ ERROR: No MON balance! Bridge MON first:");
    console.error("   → https://www.gas.zip (easiest)");
    console.error("   → https://www.bungee.exchange");
    process.exit(1);
  }

  // 1. Deploy MockUSDC
  console.log("\n📦 Deploying MockUSDC...");
  const MockUSDC = await ethers.getContractFactory("MockERC20");
  const usdc = await MockUSDC.deploy("USD Coin", "USDC", 6);
  await usdc.waitForDeployment();
  const usdcAddr = await usdc.getAddress();
  console.log(`✅ MockUSDC deployed: ${usdcAddr}`);

  // 2. Deploy ChambaEscrow
  console.log("\n📦 Deploying ChambaEscrow...");
  const ChambaEscrow = await ethers.getContractFactory("ChambaEscrow");
  // Constructor: treasury address, fee basis points (800 = 8%)
  const escrow = await ChambaEscrow.deploy(deployer.address, 800);
  await escrow.waitForDeployment();
  const escrowAddr = await escrow.getAddress();
  console.log(`✅ ChambaEscrow deployed: ${escrowAddr}`);

  // 3. Summary
  console.log("\n=== Deployment Complete ===");
  console.log(`Network: Monad Mainnet (Chain ID: 143)`);
  console.log(`MockUSDC:     ${usdcAddr}`);
  console.log(`ChambaEscrow: ${escrowAddr}`);
  console.log(`Explorer: https://explorer.monad.xyz`);
  
  // Save deployment info
  const fs = require("fs");
  const deployInfo = {
    network: "monad-mainnet",
    chainId: 143,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      MockUSDC: usdcAddr,
      ChambaEscrow: escrowAddr,
    },
  };
  
  const outPath = "./deployments/monad-mainnet.json";
  fs.mkdirSync("./deployments", { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(deployInfo, null, 2));
  console.log(`\n📄 Deployment info saved to: ${outPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

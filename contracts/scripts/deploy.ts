import { ethers, network } from "hardhat";

// Known USDC addresses (aligned with x402 facilitator supported networks)
// Source: x402-rs/src/network.rs
const USDC_ADDRESSES: { [chainId: number]: string } = {
  // Ethereum
  1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", // Ethereum Mainnet
  11155111: "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238", // Ethereum Sepolia
  // Base
  8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", // Base Mainnet
  84532: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", // Base Sepolia
  // Avalanche
  43114: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", // Avalanche Mainnet (native USDC)
  43113: "0x5425890298aed601595a70AB815c96711a31Bc65", // Avalanche Fuji
  // Polygon
  137: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", // Polygon Mainnet (native USDC)
  80002: "0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582", // Polygon Amoy
  // Optimism
  10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", // Optimism Mainnet (native USDC)
  11155420: "0x5fd84259d66Cd46123540766Be93DFE6D43130D7", // Optimism Sepolia
  // Arbitrum
  42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", // Arbitrum One (native USDC)
  421614: "0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d", // Arbitrum Sepolia
  // Celo
  42220: "0xcebA9300f2b948710d2653dD7B07f33A8B32118C", // Celo Mainnet
  44787: "0x2F25deB3848C207fc8E0c34035B3Ba7fC157602B", // Celo Alfajores
  // BSC
  56: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", // BSC Mainnet (USDC.e)
  97: "0x64544969ed7EBf5f083679233325356EbE738930", // BSC Testnet
  // Scroll
  534352: "0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4", // Scroll Mainnet
  534351: "0x690000EF01deCE82d837B5fAa2719AE47b156697", // Scroll Sepolia
  // Local
  31337: "", // Will be deployed
};

async function main() {
  const [deployer] = await ethers.getSigners();
  const chainId = Number((await ethers.provider.getNetwork()).chainId);

  console.log("=".repeat(60));
  console.log("Chamba Escrow Deployment");
  console.log("=".repeat(60));
  console.log(`Network: ${network.name} (chainId: ${chainId})`);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Balance: ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} ETH`);
  console.log("=".repeat(60));

  // Deploy mock USDC if on localhost
  let usdcAddress = USDC_ADDRESSES[chainId];
  if (chainId === 31337) {
    console.log("\n[1/2] Deploying Mock USDC for testing...");
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    const mockUsdc = await MockERC20.deploy("USD Coin", "USDC", 6);
    await mockUsdc.waitForDeployment();
    usdcAddress = await mockUsdc.getAddress();
    console.log(`Mock USDC deployed at: ${usdcAddress}`);

    // Mint some tokens to deployer for testing
    const mintAmount = ethers.parseUnits("1000000", 6); // 1M USDC
    await mockUsdc.mint(deployer.address, mintAmount);
    console.log(`Minted ${ethers.formatUnits(mintAmount, 6)} USDC to deployer`);
  }

  // Deploy ChambaEscrow
  const step = chainId === 31337 ? "[2/2]" : "[1/1]";
  console.log(`\n${step} Deploying ChambaEscrow...`);

  const ChambaEscrow = await ethers.getContractFactory("ChambaEscrow");
  const escrow = await ChambaEscrow.deploy();
  await escrow.waitForDeployment();

  const escrowAddress = await escrow.getAddress();
  console.log(`ChambaEscrow deployed at: ${escrowAddress}`);

  // Verify deployment
  console.log("\n" + "=".repeat(60));
  console.log("Deployment Summary");
  console.log("=".repeat(60));
  console.log(`ChambaEscrow: ${escrowAddress}`);
  if (usdcAddress) {
    console.log(`USDC Address: ${usdcAddress}`);
  }
  console.log(`Owner: ${await escrow.owner()}`);
  console.log(`Next Escrow ID: ${await escrow.nextEscrowId()}`);
  console.log("=".repeat(60));

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    chainId,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: {
      ChambaEscrow: escrowAddress,
      USDC: usdcAddress,
    },
  };

  console.log("\nDeployment Info (save this):");
  console.log(JSON.stringify(deploymentInfo, null, 2));

  // Verification instructions for testnets/mainnet
  if (chainId !== 31337) {
    console.log("\n" + "=".repeat(60));
    console.log("Verification Command:");
    console.log("=".repeat(60));
    console.log(`npx hardhat verify --network ${network.name} ${escrowAddress}`);
  }

  return deploymentInfo;
}

main()
  .then((info) => {
    console.log("\nDeployment completed successfully!");
    process.exit(0);
  })
  .catch((error) => {
    console.error("\nDeployment failed:", error);
    process.exit(1);
  });

#!/usr/bin/env node
/**
 * KarmaCadabra Phase 0 Fund Distribution
 * 
 * Distributes USDC to first 5 agents for testing
 */

import { ethers } from 'ethers';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__dirname);

// Base network configuration
const BASE_CONFIG = {
    chainId: 8453,
    name: 'Base Mainnet',
    rpcUrl: 'https://mainnet.base.org',
    usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
};

// USDC ABI
const USDC_ABI = [
    "function transfer(address to, uint256 amount) returns (bool)",
    "function balanceOf(address account) view returns (uint256)",
    "function decimals() view returns (uint8)"
];

// Phase 0 agents (first 5)
const PHASE0_AGENTS = [
    { name: 'aurora', address: '0x2cF434B713047d713750484AC9196A3C2F4497e8', personality: 'builder' },
    { name: 'blaze', address: '0x6d02a44f6De6B86a7fd79d8368dA74e1c5f9c392', personality: 'explorer' },
    { name: 'cipher', address: '0xB3a4BDFfd91021c60cA219A52F6B974C67ea5aF0', personality: 'analyst' },
    { name: 'drift', address: '0xf3B4d01b7d3c0C1BAeAdc8de90aD94dE198FF2aC', personality: 'connector' },
    { name: 'echo', address: '0x9edEe892f7E3fbB4039132F693aD74A37A6A6189', personality: 'creator' }
];

const AMOUNT_PER_AGENT = '2.50'; // USDC per agent
const SOURCE_WALLET = 'YOUR_PLATFORM_WALLET';

async function distributePhase0() {
    console.log('🪄 KarmaCadabra Phase 0 Distribution');
    console.log('====================================');
    console.log(`Funding ${PHASE0_AGENTS.length} agents with ${AMOUNT_PER_AGENT} USDC each`);
    
    // Check for private key
    if (!process.env.SOURCE_PRIVATE_KEY) {
        console.error('❌ Set SOURCE_PRIVATE_KEY environment variable');
        console.log(`Need private key for: ${SOURCE_WALLET}`);
        process.exit(1);
    }
    
    // Setup wallet and provider
    const provider = new ethers.JsonRpcProvider(BASE_CONFIG.rpcUrl);
    const wallet = new ethers.Wallet(process.env.SOURCE_PRIVATE_KEY, provider);
    
    console.log(`💳 Source wallet: ${wallet.address}`);
    
    // Verify wallet address
    if (wallet.address.toLowerCase() !== SOURCE_WALLET.toLowerCase()) {
        console.error('❌ Private key does not match expected source wallet');
        process.exit(1);
    }
    
    // Check balance
    const usdcContract = new ethers.Contract(BASE_CONFIG.usdc, USDC_ABI, wallet);
    const balance = await usdcContract.balanceOf(wallet.address);
    const decimals = await usdcContract.decimals();
    const balanceFormatted = ethers.formatUnits(balance, decimals);
    
    console.log(`💰 Current balance: ${balanceFormatted} USDC`);
    
    const totalNeeded = parseFloat(AMOUNT_PER_AGENT) * PHASE0_AGENTS.length;
    if (parseFloat(balanceFormatted) < totalNeeded) {
        console.error(`❌ Insufficient balance. Need ${totalNeeded} USDC, have ${balanceFormatted} USDC`);
        process.exit(1);
    }
    
    console.log(`✅ Sufficient balance for distribution\n`);
    
    // Distribute to each agent
    const results = [];
    const amountWei = ethers.parseUnits(AMOUNT_PER_AGENT, decimals);
    
    for (const agent of PHASE0_AGENTS) {
        console.log(`📤 Funding ${agent.name} (${agent.personality})...`);
        console.log(`   Address: ${agent.address}`);
        console.log(`   Amount: ${AMOUNT_PER_AGENT} USDC`);
        
        try {
            // Estimate gas
            const gasEstimate = await usdcContract.transfer.estimateGas(agent.address, amountWei);
            const gasLimit = gasEstimate * BigInt(120) / BigInt(100);
            
            // Send transaction
            const tx = await usdcContract.transfer(agent.address, amountWei, { gasLimit });
            console.log(`   TX: ${tx.hash}`);
            
            // Wait for confirmation
            const receipt = await tx.wait();
            console.log(`   ✅ Confirmed in block ${receipt.blockNumber}\n`);
            
            results.push({
                agent: agent.name,
                address: agent.address,
                amount: AMOUNT_PER_AGENT,
                success: true,
                txHash: tx.hash,
                blockNumber: receipt.blockNumber
            });
            
        } catch (error) {
            console.error(`   ❌ Failed: ${error.message}\n`);
            results.push({
                agent: agent.name,
                address: agent.address,
                amount: AMOUNT_PER_AGENT,
                success: false,
                error: error.message
            });
        }
        
        // Wait 2 seconds between transactions
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // Summary
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;
    
    console.log(`📊 Distribution Summary:`);
    console.log(`- Successful: ${successful}/${PHASE0_AGENTS.length}`);
    console.log(`- Failed: ${failed}/${PHASE0_AGENTS.length}`);
    console.log(`- Total distributed: ${successful * parseFloat(AMOUNT_PER_AGENT)} USDC`);
    
    // Save results
    const resultsData = {
        timestamp: new Date().toISOString(),
        phase: 'Phase 0',
        network: 'Base Mainnet',
        sourceWallet: SOURCE_WALLET,
        totalAgents: PHASE0_AGENTS.length,
        amountPerAgent: AMOUNT_PER_AGENT,
        successful,
        failed,
        results
    };
    
    const resultsPath = path.join(__dirname, 'scripts/wallet-management/phase0-results.json');
    await fs.writeFile(resultsPath, JSON.stringify(resultsData, null, 2));
    console.log(`\n💾 Results saved to: ${resultsPath}`);
    
    if (successful === PHASE0_AGENTS.length) {
        console.log(`\n🎉 Phase 0 funding complete! All ${successful} agents funded.`);
        console.log(`\n🚀 Next steps:`);
        console.log(`1. Update terraform/swarm config with funded agent addresses`);
        console.log(`2. Deploy 5-agent swarm to AWS ECS`);
        console.log(`3. Test autonomous EM transactions`);
    } else {
        console.log(`\n⚠️  Partial success: ${successful}/${PHASE0_AGENTS.length} agents funded`);
    }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    distributePhase0().catch(console.error);
}
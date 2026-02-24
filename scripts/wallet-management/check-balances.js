#!/usr/bin/env node
/**
 * KarmaCadabra Balance Checker
 * 
 * Checks USDC balances for source wallet and all agent wallets
 * across multiple networks
 */

import { ethers } from 'ethers';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Network configurations with public RPC endpoints
const NETWORKS = {
    base: {
        chainId: 8453,
        name: 'Base Mainnet',
        rpcUrl: 'https://mainnet.base.org',
        usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    },
    polygon: {
        chainId: 137,
        name: 'Polygon Mainnet', 
        rpcUrl: 'https://polygon-rpc.com',
        usdc: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
    },
    arbitrum: {
        chainId: 42161,
        name: 'Arbitrum One',
        rpcUrl: 'https://arb1.arbitrum.io/rpc',
        usdc: '0xA0b86991c431e59F77b5B65a5d8E7C73C6fDe5a5'
    }
};

// USDC ABI (minimal)
const USDC_ABI = [
    "function balanceOf(address account) view returns (uint256)",
    "function decimals() view returns (uint8)"
];

/**
 * Check USDC balance for an address on a specific network
 */
async function checkBalance(address, network) {
    try {
        const provider = new ethers.JsonRpcProvider(NETWORKS[network].rpcUrl);
        const usdcContract = new ethers.Contract(NETWORKS[network].usdc, USDC_ABI, provider);
        
        const balance = await usdcContract.balanceOf(address);
        const decimals = await usdcContract.decimals();
        
        return {
            success: true,
            balance: ethers.formatUnits(balance, decimals),
            raw: balance.toString()
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
            balance: '0.00'
        };
    }
}

/**
 * Main balance checking function
 */
async function checkBalances() {
    console.log('💳 KarmaCadabra Balance Checker');
    console.log('===============================');
    
    // Load wallet registry
    const registryPath = path.join(__dirname, '../../terraform/swarm/config/agent-wallets.json');
    
    let registry;
    try {
        registry = JSON.parse(await fs.readFile(registryPath, 'utf8'));
    } catch (error) {
        console.error('❌ Failed to load wallet registry:', error.message);
        console.log('Run: npm run generate-wallets first');
        process.exit(1);
    }
    
    const sourceWallet = registry.funding.sourceWallet;
    console.log(`📊 Checking balances for ${registry.wallets.length} agents + source wallet`);
    console.log(`Source wallet: ${sourceWallet}`);
    
    // Check source wallet balance
    console.log(`\n💰 Source Wallet Balance:`);
    const sourceBalances = {};
    for (const [network, config] of Object.entries(NETWORKS)) {
        const result = await checkBalance(sourceWallet, network);
        sourceBalances[network] = result.balance;
        
        const status = result.success ? '✅' : '❌';
        console.log(`${status} ${config.name}: ${result.balance} USDC`);
        
        if (!result.success) {
            console.log(`   Error: ${result.error}`);
        }
    }
    
    // Calculate total source balance
    const totalSourceUSDC = Object.values(sourceBalances)
        .reduce((sum, balance) => sum + parseFloat(balance), 0);
    console.log(`💰 Total Source Balance: ${totalSourceUSDC.toFixed(2)} USDC`);
    
    // Check if we have enough for distribution
    const requiredAmount = parseFloat(registry.funding.totalBudget);
    if (totalSourceUSDC >= requiredAmount) {
        console.log(`✅ Sufficient funds for distribution (need ${requiredAmount} USDC)`);
    } else {
        console.log(`⚠️  Insufficient funds for full distribution (need ${requiredAmount} USDC)`);
    }
    
    // Check a few agent wallets as examples
    console.log(`\n🤖 Agent Wallet Samples:`);
    const sampleAgents = registry.wallets.slice(0, 5); // First 5 agents
    
    for (const agent of sampleAgents) {
        console.log(`\n👤 ${agent.name} (${agent.personality})`);
        console.log(`   Address: ${agent.address}`);
        
        let totalAgentUSDC = 0;
        for (const [network, config] of Object.entries(NETWORKS)) {
            const result = await checkBalance(agent.address, network);
            const balance = parseFloat(result.balance);
            totalAgentUSDC += balance;
            
            const status = result.success ? '✅' : '❌';
            const balanceFormatted = balance > 0 ? result.balance : '0.00';
            console.log(`   ${status} ${config.name}: ${balanceFormatted} USDC`);
        }
        
        console.log(`   💰 Total: ${totalAgentUSDC.toFixed(2)} USDC`);
    }
    
    // Summary
    console.log(`\n📊 Summary:`);
    console.log(`- Source wallet: ${totalSourceUSDC.toFixed(2)} USDC across ${Object.keys(NETWORKS).length} networks`);
    console.log(`- Target agents: ${registry.wallets.length}`);
    console.log(`- Budget per agent: $${registry.funding.perAgentBudget} USDC`);
    console.log(`- Total distribution needed: $${registry.funding.totalBudget} USDC`);
    
    // Ready status
    if (totalSourceUSDC >= requiredAmount) {
        console.log(`\n🚀 Ready for fund distribution!`);
        console.log(`Next step: npm run distribute-funds`);
        console.log(`Note: Set SOURCE_PRIVATE_KEY environment variable`);
    } else {
        console.log(`\n⏸️  Fund source wallet before distribution`);
        console.log(`Add ${(requiredAmount - totalSourceUSDC).toFixed(2)} more USDC`);
    }
    
    // Save balance report
    const report = {
        timestamp: new Date().toISOString(),
        sourceWallet: {
            address: sourceWallet,
            balances: sourceBalances,
            total: totalSourceUSDC.toFixed(2)
        },
        sampleAgents: sampleAgents.map(agent => ({
            name: agent.name,
            address: agent.address,
            personality: agent.personality,
            // Note: Would need to check all agents for full report
        })),
        summary: {
            totalAgents: registry.wallets.length,
            budgetPerAgent: registry.funding.perAgentBudget,
            totalBudgetNeeded: registry.funding.totalBudget,
            sourceBalanceTotal: totalSourceUSDC.toFixed(2),
            readyForDistribution: totalSourceUSDC >= requiredAmount
        }
    };
    
    const reportPath = path.join(__dirname, 'balance-report.json');
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n💾 Balance report saved to: ${reportPath}`);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    checkBalances().catch(console.error);
}

export { checkBalances };
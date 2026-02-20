#!/usr/bin/env node
/**
 * KarmaCadabra Fund Distribution
 * 
 * Distributes USDC from the source wallet to all agent wallets
 * Supports multi-chain distribution (Base, Polygon, Arbitrum)
 */

import { ethers } from 'ethers';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Network configurations
const NETWORKS = {
    base: {
        chainId: 8453,
        name: 'Base Mainnet',
        rpcUrl: 'https://base-mainnet.infura.io/v3/your-infura-key',
        usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        gasPrice: '0.01' // gwei
    },
    polygon: {
        chainId: 137,
        name: 'Polygon Mainnet',
        rpcUrl: 'https://polygon-mainnet.infura.io/v3/your-infura-key',
        usdc: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', // USDC (6 decimals)
        gasPrice: '30' // gwei
    },
    arbitrum: {
        chainId: 42161,
        name: 'Arbitrum One',
        rpcUrl: 'https://arbitrum-mainnet.infura.io/v3/your-infura-key',
        usdc: '0xA0b86991c431e59F77b5B65a5d8E7C73C6fDe5a5',
        gasPrice: '0.1' // gwei
    }
};

// USDC ABI (just the transfer function)
const USDC_ABI = [
    "function transfer(address to, uint256 amount) returns (bool)",
    "function balanceOf(address account) view returns (uint256)",
    "function decimals() view returns (uint8)"
];

/**
 * Load wallet registry and distribution plan
 */
async function loadConfiguration() {
    const registryPath = path.join(__dirname, '../../terraform/swarm/config/agent-wallets.json');
    const distributionPath = path.join(__dirname, 'distribution-plan.json');
    
    const registry = JSON.parse(await fs.readFile(registryPath, 'utf8'));
    const distributionPlan = JSON.parse(await fs.readFile(distributionPath, 'utf8'));
    
    return { registry, distributionPlan };
}

/**
 * Create provider and source wallet for a network
 */
async function createWalletForNetwork(network, sourcePrivateKey) {
    // For demo purposes, using public RPC endpoints
    // In production, use Infura/Alchemy/QuickNode
    const publicRPCs = {
        base: 'https://mainnet.base.org',
        polygon: 'https://polygon-rpc.com',
        arbitrum: 'https://arb1.arbitrum.io/rpc'
    };
    
    const provider = new ethers.JsonRpcProvider(publicRPCs[network]);
    const wallet = new ethers.Wallet(sourcePrivateKey, provider);
    
    return { provider, wallet };
}

/**
 * Check USDC balance of a wallet
 */
async function checkUSDCBalance(wallet, usdcAddress) {
    const usdcContract = new ethers.Contract(usdcAddress, USDC_ABI, wallet);
    const balance = await usdcContract.balanceOf(wallet.address);
    const decimals = await usdcContract.decimals();
    
    return {
        raw: balance,
        formatted: ethers.formatUnits(balance, decimals),
        decimals: Number(decimals)
    };
}

/**
 * Distribute funds to a single agent wallet
 */
async function distributeFunds(sourceWallet, targetAddress, amount, usdcAddress, networkName) {
    console.log(`📤 Sending ${amount} USDC to ${targetAddress} on ${networkName}...`);
    
    const usdcContract = new ethers.Contract(usdcAddress, USDC_ABI, sourceWallet);
    
    // Get USDC decimals
    const decimals = await usdcContract.decimals();
    const amountWei = ethers.parseUnits(amount, decimals);
    
    try {
        // Estimate gas
        const gasEstimate = await usdcContract.transfer.estimateGas(targetAddress, amountWei);
        const gasLimit = gasEstimate * BigInt(120) / BigInt(100); // 20% buffer
        
        // Send transaction
        const tx = await usdcContract.transfer(targetAddress, amountWei, {
            gasLimit
        });
        
        console.log(`✅ Transaction sent: ${tx.hash}`);
        
        // Wait for confirmation
        const receipt = await tx.wait();
        console.log(`✅ Confirmed in block ${receipt.blockNumber}`);
        
        return {
            success: true,
            hash: tx.hash,
            blockNumber: receipt.blockNumber,
            gasUsed: receipt.gasUsed.toString()
        };
    } catch (error) {
        console.error(`❌ Failed to send to ${targetAddress}: ${error.message}`);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Main distribution function
 */
async function distributeFundsMain() {
    console.log('💰 KarmaCadabra Fund Distribution');
    console.log('=================================');
    
    // Load configuration
    const { registry, distributionPlan } = await loadConfiguration();
    
    console.log(`📊 Loading distribution plan:`);
    console.log(`- Source wallet: ${distributionPlan.sourceWallet}`);
    console.log(`- Total amount: $${distributionPlan.totalAmount} USDC`);
    console.log(`- Transactions: ${distributionPlan.transactions.length}`);
    
    // Check for source private key
    if (!process.env.SOURCE_PRIVATE_KEY) {
        console.error('❌ SOURCE_PRIVATE_KEY environment variable required');
        console.log('Set it with the private key of wallet:', distributionPlan.sourceWallet);
        process.exit(1);
    }
    
    const sourcePrivateKey = process.env.SOURCE_PRIVATE_KEY;
    
    // Verify source wallet address matches
    const sourceWallet = new ethers.Wallet(sourcePrivateKey);
    if (sourceWallet.address.toLowerCase() !== distributionPlan.sourceWallet.toLowerCase()) {
        console.error('❌ Source private key does not match expected wallet address');
        console.error(`Expected: ${distributionPlan.sourceWallet}`);
        console.error(`Got: ${sourceWallet.address}`);
        process.exit(1);
    }
    
    console.log(`✅ Source wallet verified: ${sourceWallet.address}`);
    
    // Group transactions by network
    const transactionsByNetwork = {};
    distributionPlan.transactions.forEach(tx => {
        if (!transactionsByNetwork[tx.network]) {
            transactionsByNetwork[tx.network] = [];
        }
        transactionsByNetwork[tx.network].push(tx);
    });
    
    // Process each network
    const results = { successful: 0, failed: 0, transactions: [] };
    
    for (const [network, transactions] of Object.entries(transactionsByNetwork)) {
        console.log(`\n🔗 Processing ${network} network (${transactions.length} transactions)`);
        
        if (!NETWORKS[network]) {
            console.error(`❌ Unknown network: ${network}`);
            continue;
        }
        
        const networkConfig = NETWORKS[network];
        
        try {
            // Create wallet for this network
            const { provider, wallet } = await createWalletForNetwork(network, sourcePrivateKey);
            
            // Check source wallet USDC balance
            const balance = await checkUSDCBalance(wallet, networkConfig.usdc);
            console.log(`💳 Source wallet balance on ${network}: ${balance.formatted} USDC`);
            
            // Calculate total needed for this network
            const totalNeeded = transactions.reduce((sum, tx) => sum + parseFloat(tx.amount), 0);
            if (parseFloat(balance.formatted) < totalNeeded) {
                console.error(`❌ Insufficient USDC balance on ${network}`);
                console.error(`Need: ${totalNeeded} USDC, Have: ${balance.formatted} USDC`);
                continue;
            }
            
            // Process transactions for this network
            for (const tx of transactions) {
                const result = await distributeFunds(
                    wallet,
                    tx.to,
                    tx.amount,
                    networkConfig.usdc,
                    network
                );
                
                results.transactions.push({
                    network,
                    agentName: tx.agentName,
                    to: tx.to,
                    amount: tx.amount,
                    ...result
                });
                
                if (result.success) {
                    results.successful++;
                } else {
                    results.failed++;
                }
                
                // Wait 2 seconds between transactions to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
        } catch (error) {
            console.error(`❌ Error processing ${network}: ${error.message}`);
        }
    }
    
    // Save results
    const resultsPath = path.join(__dirname, 'distribution-results.json');
    await fs.writeFile(resultsPath, JSON.stringify({
        timestamp: new Date().toISOString(),
        sourceWallet: distributionPlan.sourceWallet,
        summary: {
            totalTransactions: results.transactions.length,
            successful: results.successful,
            failed: results.failed
        },
        transactions: results.transactions
    }, null, 2));
    
    console.log(`\n📋 Distribution Summary:`);
    console.log(`- Successful: ${results.successful}`);
    console.log(`- Failed: ${results.failed}`);
    console.log(`- Results saved to: ${resultsPath}`);
    
    if (results.successful > 0) {
        console.log(`\n🎉 Successfully distributed funds to ${results.successful} agent wallets!`);
        
        // Update wallet registry with new balances (simplified)
        console.log(`\n💡 Next steps:`);
        console.log(`1. Verify balances with: npm run check-balances`);
        console.log(`2. Update terraform/swarm agent configurations with wallet addresses`);
        console.log(`3. Deploy agent swarm with funded wallets`);
    }
    
    if (results.failed > 0) {
        console.log(`\n⚠️  ${results.failed} transactions failed. Check logs above for details.`);
    }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    distributeFundsMain().catch(console.error);
}

export { distributeFundsMain };
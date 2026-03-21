#!/usr/bin/env node
/**
 * KarmaCadabra Wallet Generator
 * 
 * Generates HD wallets for 24 agents using BIP-44 derivation
 * Exports wallet registry with personality mapping
 */

import { ethers } from 'ethers';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const AGENT_COUNT = 24;
const DERIVATION_PATH_BASE = "m/44'/60'/0'/0/"; // BIP-44 Ethereum path

// Personality archetypes from terraform/swarm/templates
const PERSONALITY_ARCHETYPES = [
    'builder',
    'explorer', 
    'analyst',
    'connector',
    'creator',
    'guardian',
    'maverick',
    'strategist',
    'teacher'
];

// Network configuration
const NETWORKS = {
    base: {
        chainId: 8453,
        name: 'Base Mainnet',
        usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    },
    polygon: {
        chainId: 137,
        name: 'Polygon Mainnet',
        usdc: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
    },
    arbitrum: {
        chainId: 42161,
        name: 'Arbitrum One',
        usdc: '0xA0b86991c431e59F77b5B65a5d8E7C73C6fDe5a5'
    }
};

/**
 * Generate deterministic agent name from index
 */
function generateAgentName(index) {
    const names = [
        'aurora', 'blaze', 'cipher', 'drift', 'echo',
        'flux', 'galaxy', 'horizon', 'ion', 'jinx',
        'kinetic', 'lunar', 'matrix', 'nova', 'orbit',
        'prism', 'quantum', 'raven', 'stellar', 'titan',
        'umbra', 'vortex', 'wave', 'xenon'
    ];
    return names[index] || `agent${index}`;
}

/**
 * Generate HD wallet from seed and derivation path
 */
function generateWallet(seed, index) {
    const derivationPath = `${DERIVATION_PATH_BASE}${index}`;
    
    // Create master HDNode from seed
    const masterNode = ethers.HDNodeWallet.fromSeed(seed);
    
    // Derive child wallet at specific path
    const childNode = masterNode.derivePath(derivationPath);
    
    return {
        index,
        name: generateAgentName(index),
        address: childNode.address,
        privateKey: childNode.privateKey,
        derivationPath,
        personality: PERSONALITY_ARCHETYPES[index % PERSONALITY_ARCHETYPES.length]
    };
}

/**
 * Main wallet generation function
 */
async function generateWallets() {
    console.log('🪄 KarmaCadabra Wallet Generator');
    console.log(`Generating ${AGENT_COUNT} HD wallets...`);

    // Use environment variable for seed, or generate a new one
    let seed;
    if (process.env.KARMACADABRA_SEED) {
        seed = ethers.getBytes('0x' + process.env.KARMACADABRA_SEED);
        console.log('✅ Using provided seed from environment');
    } else {
        console.log('⚠️  No KARMACADABRA_SEED found, generating random seed');
        seed = ethers.randomBytes(32);
        console.log(`Generated seed: ${ethers.hexlify(seed)}`);
        console.log('🚨 SAVE THIS SEED - Required to recreate wallets!');
    }

    const wallets = [];
    
    for (let i = 0; i < AGENT_COUNT; i++) {
        const wallet = generateWallet(seed, i);
        wallets.push({
            index: wallet.index,
            name: wallet.name,
            address: wallet.address,
            personality: wallet.personality,
            derivationPath: wallet.derivationPath,
            // Note: Private keys excluded from main registry for security
        });
        
        console.log(`Generated wallet ${i}: ${wallet.name} (${wallet.personality}) - ${wallet.address}`);
    }

    // Create wallet registry
    const walletRegistry = {
        metadata: {
            generated: new Date().toISOString(),
            agentCount: AGENT_COUNT,
            derivationPathBase: DERIVATION_PATH_BASE,
            seedUsed: !!process.env.KARMACADABRA_SEED,
            networks: NETWORKS
        },
        wallets: wallets.map(w => ({
            index: w.index,
            name: w.name,
            address: w.address,
            personality: w.personality,
            balances: {
                base: { usdc: '0.00' },
                polygon: { usdc: '0.00' },
                arbitrum: { usdc: '0.00' }
            }
        })),
        funding: {
            sourceWallet: 'YOUR_PLATFORM_WALLET',
            totalBudget: '200.00',
            perAgentBudget: '8.33',
            distribution: {
                base: '6.67', // 80%
                polygon: '1.25', // 15% 
                arbitrum: '0.41' // 5%
            }
        }
    };

    // Save wallet registry
    const registryPath = path.join(__dirname, '../../terraform/swarm/config/agent-wallets.json');
    await fs.mkdir(path.dirname(registryPath), { recursive: true });
    await fs.writeFile(registryPath, JSON.stringify(walletRegistry, null, 2));
    
    console.log(`✅ Wallet registry saved to: ${registryPath}`);
    
    // Save private keys separately (for distribution script)
    const privateKeysPath = path.join(__dirname, '.keys.json');
    const privateKeys = {};
    for (let i = 0; i < AGENT_COUNT; i++) {
        const wallet = generateWallet(seed, i);
        privateKeys[wallet.address] = {
            name: wallet.name,
            privateKey: wallet.privateKey,
            index: wallet.index
        };
    }
    
    await fs.writeFile(privateKeysPath, JSON.stringify(privateKeys, null, 2));
    console.log(`🔐 Private keys saved to: ${privateKeysPath}`);
    console.log('⚠️  SECURE THIS FILE - Contains private keys!');

    // Generate distribution plan
    const distributionPlan = {
        sourceWallet: 'YOUR_PLATFORM_WALLET',
        totalAmount: '200.00',
        transactions: []
    };

    // Plan base chain distribution  
    for (let i = 0; i < AGENT_COUNT; i++) {
        distributionPlan.transactions.push({
            network: 'base',
            to: wallets[i].address,
            amount: '6.67',
            token: 'USDC',
            agentName: wallets[i].name,
            purpose: 'Primary funding'
        });
    }

    // Plan polygon distribution
    for (let i = 0; i < AGENT_COUNT; i++) {
        distributionPlan.transactions.push({
            network: 'polygon', 
            to: wallets[i].address,
            amount: '1.25',
            token: 'USDC',
            agentName: wallets[i].name,
            purpose: 'Secondary funding'
        });
    }

    const distributionPath = path.join(__dirname, 'distribution-plan.json');
    await fs.writeFile(distributionPath, JSON.stringify(distributionPlan, null, 2));
    console.log(`📋 Distribution plan saved to: ${distributionPath}`);

    console.log(`\n🎯 Summary:`);
    console.log(`- ${AGENT_COUNT} wallets generated`);
    console.log(`- ${PERSONALITY_ARCHETYPES.length} personality types`);
    console.log(`- Registry: ${registryPath}`);
    console.log(`- Distribution plan: ${distributionPath}`);
    console.log(`\n🚀 Ready for fund distribution!`);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    generateWallets().catch(console.error);
}

export { generateWallets };
/**
 * Execution Market — Multi-Chain x402 Payment Flow Test
 *
 * Tests x402 payments across multiple networks and stablecoins:
 * - Base, Polygon, Optimism, Arbitrum
 * - USDC as primary stablecoin
 * - Fibonacci bounties: $0.01, $0.02, $0.03, $0.05, $0.08
 *
 * Usage:
 *   npx tsx test-x402-multi-chain.ts                     # Test all networks
 *   npx tsx test-x402-multi-chain.ts --networks base     # Test specific network
 *   npx tsx test-x402-multi-chain.ts --count 3           # Only first N Fibonacci tasks per chain
 *   npx tsx test-x402-multi-chain.ts --dry-run           # Only verify, don't create tasks
 */

import {
  createPublicClient,
  http,
  formatUnits,
  parseUnits,
  type Hex,
  type Address,
} from 'viem';
import { base, polygon, optimism, arbitrum } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

// =============================================================================
// Network Configuration
// =============================================================================

interface NetworkConfig {
  name: string;
  chain: any;
  chainId: number;
  usdcAddress: Address;
  facilitatorSupported: boolean;
  emTreasury: Address;
}

const NETWORKS: Record<string, NetworkConfig> = {
  base: {
    name: 'Base',
    chain: base,
    chainId: 8453,
    usdcAddress: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    facilitatorSupported: true,
    emTreasury: 'YOUR_TREASURY_WALLET',
  },
  polygon: {
    name: 'Polygon',
    chain: polygon,
    chainId: 137,
    usdcAddress: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
    facilitatorSupported: true,
    emTreasury: 'YOUR_TREASURY_WALLET', // Same treasury
  },
  optimism: {
    name: 'Optimism',
    chain: optimism,
    chainId: 10,
    usdcAddress: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
    facilitatorSupported: true,
    emTreasury: 'YOUR_TREASURY_WALLET',
  },
  arbitrum: {
    name: 'Arbitrum',
    chain: arbitrum,
    chainId: 42161,
    usdcAddress: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
    facilitatorSupported: true,
    emTreasury: 'YOUR_TREASURY_WALLET',
  },
};

// =============================================================================
// Configuration
// =============================================================================

const PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY as Hex;
if (!PRIVATE_KEY) {
  console.error('ERROR: WALLET_PRIVATE_KEY not set in .env.local');
  process.exit(1);
}

const account = privateKeyToAccount(PRIVATE_KEY);
const WALLET_ADDRESS = account.address;

const MCP_SERVER_URL = 'https://mcp.execution.market';
const FACILITATOR_URL = 'https://facilitator.ultravioletadao.xyz';

// Fibonacci bounties for test tasks
const FIBONACCI_BOUNTIES = [0.01, 0.02, 0.03, 0.05, 0.08];
const PLATFORM_FEE_PERCENT = 0.13;

// =============================================================================
// CLI Args
// =============================================================================

function parseArgs(): Record<string, string> {
  const args: Record<string, string> = {};
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      if (['dry-run', 'verify-only'].includes(key)) {
        args[key] = 'true';
      } else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) {
        args[key] = argv[i + 1];
        i++;
      } else {
        args[key] = 'true';
      }
    }
  }
  return args;
}

const CLI_ARGS = parseArgs();
const DRY_RUN = CLI_ARGS['dry-run'] === 'true';
const TASK_COUNT = Math.min(parseInt(CLI_ARGS['count'] || '5', 10), FIBONACCI_BOUNTIES.length);
const SELECTED_NETWORKS = CLI_ARGS['networks'] ? 
  CLI_ARGS['networks'].split(',').map(n => n.trim()) : 
  Object.keys(NETWORKS);

// =============================================================================
// Contract ABIs
// =============================================================================

const ERC20_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'name',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
  },
  {
    name: 'version',
    type: 'function',
    stateMutability: 'view' as const,
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
  },
] as const;

// =============================================================================
// EIP-3009 Signing
// =============================================================================

const TRANSFER_WITH_AUTHORIZATION_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
} as const;

interface EIP3009Authorization {
  from: Address;
  to: Address;
  value: string;
  validAfter: string;
  validBefore: string;
  nonce: Hex;
}

async function signTransferWithAuthorization(
  networkConfig: NetworkConfig,
  to: Address,
  amountUsd: number,
  validForSeconds: number = 3600,
): Promise<{ authorization: EIP3009Authorization; signature: Hex }> {
  const value = parseUnits(amountUsd.toFixed(6), 6);
  const now = Math.floor(Date.now() / 1000);

  // Generate random nonce (bytes32)
  const randomBytes = new Uint8Array(32);
  crypto.getRandomValues(randomBytes);
  const nonce = ('0x' + Array.from(randomBytes).map(b => b.toString(16).padStart(2, '0')).join('')) as Hex;

  const authorization: EIP3009Authorization = {
    from: WALLET_ADDRESS,
    to,
    value: value.toString(),
    validAfter: '0',
    validBefore: (now + validForSeconds).toString(),
    nonce,
  };

  // EIP-712 domain for this network's USDC
  const domain = {
    name: 'USD Coin',
    version: '2',
    chainId: BigInt(networkConfig.chainId),
    verifyingContract: networkConfig.usdcAddress,
  } as const;

  // Sign with EIP-712
  const signature = await account.signTypedData({
    domain,
    types: TRANSFER_WITH_AUTHORIZATION_TYPES,
    primaryType: 'TransferWithAuthorization',
    message: {
      from: authorization.from,
      to: authorization.to,
      value: BigInt(authorization.value),
      validAfter: BigInt(authorization.validAfter),
      validBefore: BigInt(authorization.validBefore),
      nonce: authorization.nonce,
    },
  });

  return { authorization, signature };
}

function buildX402PaymentHeader(
  authorization: EIP3009Authorization,
  signature: Hex,
  networkName: string,
): string {
  const payload = {
    x402Version: 1,
    scheme: 'exact',
    network: networkName.toLowerCase(),
    payload: {
      signature,
      authorization: {
        from: authorization.from,
        to: authorization.to,
        value: authorization.value,
        validAfter: authorization.validAfter,
        validBefore: authorization.validBefore,
        nonce: authorization.nonce,
      },
    },
  };

  const jsonStr = JSON.stringify(payload);
  return Buffer.from(jsonStr).toString('base64');
}

// =============================================================================
// Facilitator Verification
// =============================================================================

async function verifyWithFacilitator(
  networkConfig: NetworkConfig,
  paymentHeader: string,
  amountUsd: number,
): Promise<any> {
  const paymentPayload = JSON.parse(Buffer.from(paymentHeader, 'base64').toString());

  const verifyBody = {
    x402Version: 1,
    paymentPayload,
    paymentRequirements: {
      scheme: 'exact',
      network: networkConfig.name.toLowerCase(),
      maxAmountRequired: parseUnits(amountUsd.toFixed(6), 6).toString(),
      resource: `https://mcp.execution.market/api/v1/tasks`,
      description: `Execution Market task creation on ${networkConfig.name}`,
      mimeType: 'application/json',
      payTo: networkConfig.emTreasury,
      maxTimeoutSeconds: 3600,
      asset: networkConfig.usdcAddress,
      extra: {},
    },
  };

  try {
    const res = await fetch(`${FACILITATOR_URL}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(verifyBody),
    });
    return await res.json();
  } catch (err: any) {
    return { error: err.message };
  }
}

// =============================================================================
// Balance Checking
// =============================================================================

async function checkUsdcBalance(networkConfig: NetworkConfig): Promise<number> {
  const publicClient = createPublicClient({
    chain: networkConfig.chain,
    transport: http(),
  });

  try {
    const balance = await publicClient.readContract({
      address: networkConfig.usdcAddress,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [WALLET_ADDRESS],
    });
    return Number(formatUnits(balance, 6));
  } catch (err: any) {
    console.log(`    Error checking USDC balance: ${err.message?.slice(0, 80)}`);
    return 0;
  }
}

// =============================================================================
// Test Results Storage
// =============================================================================

interface TestResult {
  network: string;
  stablecoin: string;
  fibIndex: number;
  taskId: string | null;
  bountyAmount: number;
  totalWithFee: number;
  facilitatorVerified: boolean;
  facilitatorMessage: string;
  balanceBefore: number;
  balanceAfter?: number;
  error?: string;
  paymentHeader?: string;
}

const testResults: TestResult[] = [];

// =============================================================================
// Main Test Function
// =============================================================================

async function testNetworkPayments(networkConfig: NetworkConfig): Promise<void> {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`  Testing ${networkConfig.name} (Chain ID: ${networkConfig.chainId})`);
  console.log('='.repeat(60));
  
  console.log(`  USDC Address: ${networkConfig.usdcAddress}`);
  console.log(`  Treasury:     ${networkConfig.emTreasury}`);
  
  // Check balance
  const initialBalance = await checkUsdcBalance(networkConfig);
  console.log(`  USDC Balance: $${initialBalance.toFixed(6)}`);
  
  const totalNeeded = FIBONACCI_BOUNTIES
    .slice(0, TASK_COUNT)
    .reduce((sum, bounty) => sum + bounty * (1 + PLATFORM_FEE_PERCENT), 0);
  
  console.log(`  Needed for ${TASK_COUNT} tasks: $${totalNeeded.toFixed(6)}`);
  
  if (initialBalance < totalNeeded) {
    console.log(`  ⚠️  Insufficient balance for full testing`);
  }
  
  // Test each Fibonacci bounty
  for (let i = 0; i < TASK_COUNT; i++) {
    const bounty = FIBONACCI_BOUNTIES[i];
    const totalAmount = Number((bounty * (1 + PLATFORM_FEE_PERCENT)).toFixed(6));
    
    console.log(`\n    [Fib #${i + 1}] $${bounty.toFixed(2)} (+ fee = $${totalAmount.toFixed(2)})`);
    
    const result: TestResult = {
      network: networkConfig.name,
      stablecoin: 'USDC',
      fibIndex: i,
      taskId: null,
      bountyAmount: bounty,
      totalWithFee: totalAmount,
      facilitatorVerified: false,
      facilitatorMessage: '',
      balanceBefore: initialBalance,
    };
    
    try {
      // Sign EIP-3009 authorization
      const { authorization, signature } = await signTransferWithAuthorization(
        networkConfig,
        networkConfig.emTreasury,
        totalAmount,
      );
      
      console.log(`      Signed EIP-3009: nonce=${authorization.nonce.slice(0, 18)}...`);
      
      // Build x402 header
      const paymentHeader = buildX402PaymentHeader(authorization, signature, networkConfig.name);
      result.paymentHeader = paymentHeader;
      console.log(`      X-Payment header: ${paymentHeader.slice(0, 50)}...`);
      
      // Verify with facilitator
      console.log(`      Verifying with facilitator...`);
      const verifyResult = await verifyWithFacilitator(networkConfig, paymentHeader, totalAmount);
      
      if (verifyResult.isValid || verifyResult.valid) {
        result.facilitatorVerified = true;
        result.facilitatorMessage = 'VALID';
        console.log(`      ✅ Facilitator: VALID (payer: ${verifyResult.payer?.slice(0, 10)}...)`);
      } else {
        result.facilitatorVerified = false;
        result.facilitatorMessage = JSON.stringify(verifyResult).slice(0, 100);
        console.log(`      ❌ Facilitator: ${result.facilitatorMessage}`);
      }
      
      // If not dry run, could create actual task here
      if (!DRY_RUN) {
        console.log(`      ⚠️  Task creation not implemented for multi-chain (would need MCP API changes)`);
        // result.taskId = await createTaskViaMCP(...);
      } else {
        console.log(`      ℹ️  Dry run - not creating task`);
      }
      
    } catch (err: any) {
      result.error = err.message?.slice(0, 200);
      console.log(`      ❌ Error: ${result.error}`);
    }
    
    testResults.push(result);
  }
  
  // Final balance check
  const finalBalance = await checkUsdcBalance(networkConfig);
  console.log(`\n  Final USDC Balance: $${finalBalance.toFixed(6)} (change: ${(finalBalance - initialBalance).toFixed(6)})`);
  
  // Update results with final balance
  testResults.filter(r => r.network === networkConfig.name).forEach(r => {
    r.balanceAfter = finalBalance;
  });
}

// =============================================================================
// Results Documentation
// =============================================================================

async function writeResults(): Promise<void> {
  const docsDir = resolve(__dirname, '../docs/planning');
  const outputFile = resolve(docsDir, 'PAYMENT-TEST-RESULTS.md');
  
  let content = `# Multi-Chain x402 Payment Test Results\n\n`;
  content += `**Test Date:** ${new Date().toISOString()}\n`;
  content += `**Wallet:** ${WALLET_ADDRESS}\n`;
  content += `**Test Count:** ${TASK_COUNT} Fibonacci tasks per network\n`;
  content += `**Networks Tested:** ${SELECTED_NETWORKS.join(', ')}\n\n`;
  
  // Summary table
  content += `## Summary\n\n`;
  content += `| Network | Tasks | Verified | Errors | Total Bounty | Balance Change |\n`;
  content += `|---------|-------|----------|--------|--------------|-----------------|\n`;
  
  for (const networkName of SELECTED_NETWORKS) {
    const networkResults = testResults.filter(r => r.network === NETWORKS[networkName]?.name);
    const verified = networkResults.filter(r => r.facilitatorVerified).length;
    const errors = networkResults.filter(r => r.error).length;
    const totalBounty = networkResults.reduce((sum, r) => sum + r.bountyAmount, 0);
    const balanceChange = networkResults.length > 0 ? 
      ((networkResults[0].balanceAfter || 0) - networkResults[0].balanceBefore) : 0;
    
    content += `| ${NETWORKS[networkName]?.name || networkName} | ${networkResults.length} | ${verified}/${networkResults.length} | ${errors} | $${totalBounty.toFixed(2)} | $${balanceChange.toFixed(6)} |\n`;
  }
  
  content += `\n## Detailed Results\n\n`;
  
  for (const networkName of SELECTED_NETWORKS) {
    const networkConfig = NETWORKS[networkName];
    if (!networkConfig) continue;
    
    const networkResults = testResults.filter(r => r.network === networkConfig.name);
    
    content += `### ${networkConfig.name} (Chain ID: ${networkConfig.chainId})\n\n`;
    content += `**USDC Address:** \`${networkConfig.usdcAddress}\`\n`;
    content += `**Treasury:** \`${networkConfig.emTreasury}\`\n\n`;
    
    content += `| Fib # | Bounty | Total w/Fee | Task ID | Facilitator | Error |\n`;
    content += `|-------|--------|-------------|---------|-------------|-------|\n`;
    
    for (const result of networkResults) {
      const facilitatorStatus = result.facilitatorVerified ? '✅' : '❌';
      const taskId = result.taskId ? result.taskId.slice(0, 8) + '...' : 'N/A';
      const error = result.error ? result.error.slice(0, 30) + '...' : '';
      
      content += `| ${result.fibIndex + 1} | $${result.bountyAmount.toFixed(2)} | $${result.totalWithFee.toFixed(2)} | ${taskId} | ${facilitatorStatus} | ${error} |\n`;
    }
    
    content += `\n`;
  }
  
  // Technical details
  content += `## Technical Details\n\n`;
  content += `### Network Configuration\n\n`;
  content += `\`\`\`json\n`;
  content += JSON.stringify(NETWORKS, null, 2);
  content += `\n\`\`\`\n\n`;
  
  content += `### Test Configuration\n\n`;
  content += `- **Fibonacci bounties:** ${FIBONACCI_BOUNTIES.map(b => `$${b.toFixed(2)}`).join(', ')}\n`;
  content += `- **Platform fee:** ${(PLATFORM_FEE_PERCENT * 100)}%\n`;
  content += `- **Tasks per network:** ${TASK_COUNT}\n`;
  content += `- **Dry run mode:** ${DRY_RUN ? 'Yes' : 'No'}\n\n`;
  
  content += `### Key Findings\n\n`;
  
  const totalResults = testResults.length;
  const totalVerified = testResults.filter(r => r.facilitatorVerified).length;
  const totalErrors = testResults.filter(r => r.error).length;
  
  content += `- **Total tests:** ${totalResults}\n`;
  content += `- **Facilitator verifications:** ${totalVerified}/${totalResults} (${((totalVerified/totalResults)*100).toFixed(1)}%)\n`;
  content += `- **Errors encountered:** ${totalErrors}/${totalResults} (${((totalErrors/totalResults)*100).toFixed(1)}%)\n`;
  
  const networksWithErrors = new Set(testResults.filter(r => r.error).map(r => r.network));
  if (networksWithErrors.size > 0) {
    content += `- **Networks with issues:** ${Array.from(networksWithErrors).join(', ')}\n`;
  }
  
  content += `\n### Important Notes\n\n`;
  content += `1. **No funds actually moved** - EIP-3009 authorizations are signed but not executed until worker completion and agent approval\n`;
  content += `2. **Base is the primary network** - Other networks may have limited MCP API support\n`;
  content += `3. **Facilitator verification** tests the payment authorization without settling\n`;
  
  if (DRY_RUN) {
    content += `4. **This was a dry run** - No tasks were actually created\n`;
  }
  
  // Ensure docs directory exists
  await import('fs/promises').then(fs => fs.mkdir(docsDir, { recursive: true }));
  
  // Write results
  await import('fs/promises').then(fs => fs.writeFile(outputFile, content));
  
  console.log(`\n📄 Results written to: ${outputFile}`);
}

// =============================================================================
// Main
// =============================================================================

async function main(): Promise<void> {
  console.log('\n' + '='.repeat(80));
  console.log('  Execution Market — Multi-Chain x402 Payment Test');
  console.log('='.repeat(80));
  
  console.log(`\n  Wallet:           ${WALLET_ADDRESS}`);
  console.log(`  Networks:         ${SELECTED_NETWORKS.join(', ')}`);
  console.log(`  Tasks per chain:  ${TASK_COUNT} (Fibonacci bounties)`);
  console.log(`  Bounties:         ${FIBONACCI_BOUNTIES.slice(0, TASK_COUNT).map(b => `$${b.toFixed(2)}`).join(', ')}`);
  console.log(`  Mode:             ${DRY_RUN ? 'Dry run (verify only)' : 'Full test'}`);
  
  // Validate selected networks
  for (const networkName of SELECTED_NETWORKS) {
    if (!NETWORKS[networkName]) {
      console.error(`\nERROR: Unknown network '${networkName}'`);
      console.error(`Available networks: ${Object.keys(NETWORKS).join(', ')}`);
      process.exit(1);
    }
  }
  
  // Test each selected network
  for (const networkName of SELECTED_NETWORKS) {
    const networkConfig = NETWORKS[networkName];
    await testNetworkPayments(networkConfig);
  }
  
  // Write results
  await writeResults();
  
  console.log('\n' + '='.repeat(80));
  console.log('  Multi-Chain Test Complete');
  console.log('='.repeat(80));
  console.log('');
}

// =============================================================================
// Entry Point
// =============================================================================

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('\nFATAL ERROR:', err.message || err);
    if (err.stack) console.error(err.stack);
    process.exit(1);
  });
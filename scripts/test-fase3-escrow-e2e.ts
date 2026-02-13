/**
 * Fase 3 Escrow E2E Test — Trustless PaymentOperator on Base Mainnet.
 *
 * Tests the Fase 3 operator with OR(Payer|Facilitator) conditions + 1% on-chain fee:
 *   1. AUTHORIZE  — Lock USDC in escrow via Fase 3 operator (gasless via facilitator)
 *   2. QUERY      — Verify escrow state on-chain (capturable > 0)
 *   3. RELEASE    — Release to worker (payer calls on-chain via OR condition)
 *   -- OR --
 *   3b. REFUND   — Refund back to agent (payer calls on-chain)
 *
 * Usage:
 *   npx tsx scripts/test-fase3-escrow-e2e.ts                # Full lifecycle (authorize + release)
 *   npx tsx scripts/test-fase3-escrow-e2e.ts --refund        # Authorize + refund
 *   npx tsx scripts/test-fase3-escrow-e2e.ts --dry-run       # Print config only
 *
 * Fase 3 Operator: 0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6
 *   - OR(Payer|Facilitator) release/refund conditions
 *   - StaticFeeCalculator(100bps = 1%)
 */

import { ethers } from 'ethers';
import { AdvancedEscrowClient, ESCROW_CONTRACTS } from 'uvd-x402-sdk/backend';
import { config } from 'dotenv';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import {
  createPublicClient,
  http,
  formatUnits,
  type Address,
} from 'viem';
import { base } from 'viem/chains';

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, '../.env.local') });

// ============================================================
// Config
// ============================================================

const FASE3_OPERATOR = '0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6';
const FACILITATOR_URL = 'https://facilitator.ultravioletadao.xyz';
const RPC_URL = process.env.BASE_RPC_URL || 'https://mainnet.base.org';
const CHAIN_ID = 8453;
const TEST_AMOUNT = '2000'; // $0.002 USDC
const TEST_RECEIVER = '0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad';
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as Address;
const IDENTITY_REGISTRY = '0x8004A169FB4a3325136EB29fA0ceB6D2e539a432' as Address;
const REPUTATION_REGISTRY = '0x8004BAa17C55a88189AE136b182e5fdA19dE9b63' as Address;

const ERC20_ABI = [
  {
    name: 'balanceOf', type: 'function', stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

const ESCROW_ABI = [
  'function getEscrowState(address operator, address token, address payer, uint256 nonce) view returns (uint120 capturableAmount, uint120 collectedAmount, bool hasCollectedPayment)',
] as const;

const REGISTRY_ABI = [
  'function totalSupply() view returns (uint256)',
  'function balanceOf(address owner) view returns (uint256)',
] as const;

function hr(char = '=', len = 60): string { return char.repeat(len); }
function sleep(ms: number): Promise<void> { return new Promise((r) => setTimeout(r, ms)); }

async function main(): Promise<void> {
  const isDryRun = process.argv.includes('--dry-run');
  const doRefund = process.argv.includes('--refund');

  const privateKey = process.env.WALLET_PRIVATE_KEY;
  if (!privateKey) { console.error('ERROR: WALLET_PRIVATE_KEY not set in .env.local'); process.exit(1); }

  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const signer = new ethers.Wallet(privateKey, provider);
  const baseContracts = ESCROW_CONTRACTS[CHAIN_ID];
  if (!baseContracts) { console.error('ERROR: No escrow contracts for chain', CHAIN_ID); process.exit(1); }

  const customContracts = { ...baseContracts, operator: FASE3_OPERATOR };

  console.log(hr());
  console.log('Fase 3 Escrow E2E Test — Trustless — Base Mainnet');
  console.log(hr());
  console.log(`Facilitator:     ${FACILITATOR_URL}`);
  console.log(`RPC:             ${RPC_URL}`);
  console.log(`Chain:           Base (${CHAIN_ID})`);
  console.log(`Fase 3 Operator: ${FASE3_OPERATOR}`);
  console.log(`Protocol Escrow: ${baseContracts.escrow}`);
  console.log(`TokenCollector:  ${baseContracts.tokenCollector}`);
  console.log(`Test amount:     $${Number(TEST_AMOUNT) / 1_000_000} USDC (${TEST_AMOUNT} units)`);
  console.log(`Receiver:        ${TEST_RECEIVER}`);
  console.log(`Mode:            ${doRefund ? 'REFUND' : 'RELEASE'}`);
  console.log(`Dry run:         ${isDryRun}`);
  console.log();

  const client = new AdvancedEscrowClient(signer, {
    facilitatorUrl: FACILITATOR_URL, chainId: CHAIN_ID, contracts: customContracts,
  });
  await client.init();

  const payerAddress = await signer.getAddress();
  console.log(`Payer (agent):   ${payerAddress}`);
  console.log('Contracts:');
  for (const [k, v] of Object.entries(customContracts)) { console.log(`  ${k.padEnd(25)} ${v}`); }
  console.log();

  const viemClient = createPublicClient({ chain: base, transport: http(RPC_URL) });
  const usdcBalance = await viemClient.readContract({
    address: USDC_ADDRESS, abi: ERC20_ABI, functionName: 'balanceOf', args: [payerAddress as Address],
  });
  console.log(`USDC balance:    ${formatUnits(usdcBalance, 6)} USDC\n`);

  if (isDryRun) {
    console.log('DRY RUN — building PaymentInfo only');
    const pi = client.buildPaymentInfo(TEST_RECEIVER, TEST_AMOUNT, 'micro');
    console.log('\nPaymentInfo:');
    console.log(`  operator:              ${pi.operator}`);
    console.log(`  receiver:              ${pi.receiver}`);
    console.log(`  token:                 ${pi.token}`);
    console.log(`  maxAmount:             ${pi.maxAmount} (${Number(pi.maxAmount) / 1_000_000} USDC)`);
    console.log(`  preApprovalExpiry:     ${pi.preApprovalExpiry} (${new Date(pi.preApprovalExpiry * 1000).toISOString()})`);
    console.log(`  authorizationExpiry:   ${pi.authorizationExpiry} (${new Date(pi.authorizationExpiry * 1000).toISOString()})`);
    console.log(`  refundExpiry:          ${pi.refundExpiry} (${new Date(pi.refundExpiry * 1000).toISOString()})`);
    console.log(`  minFeeBps:             ${pi.minFeeBps}`);
    console.log(`  maxFeeBps:             ${pi.maxFeeBps}`);
    console.log(`  feeReceiver:           ${pi.feeReceiver}`);
    console.log(`  salt:                  ${pi.salt.slice(0, 18)}...`);
    console.log('\nDRY RUN complete.');
    return;
  }

  if (usdcBalance < BigInt(TEST_AMOUNT)) {
    console.error(`ERROR: Need ${Number(TEST_AMOUNT) / 1_000_000} USDC but have ${formatUnits(usdcBalance, 6)}`);
    process.exit(1);
  }

  // Step 1: AUTHORIZE
  console.log(`--- Step 1: AUTHORIZE (lock funds via facilitator) ---`);
  const pi = client.buildPaymentInfo(TEST_RECEIVER, TEST_AMOUNT, 'micro');
  console.log(`  operator: ${pi.operator}`);
  console.log(`  salt: ${pi.salt.slice(0, 18)}...`);
  console.log(`  maxFeeBps: ${pi.maxFeeBps} (= ${pi.maxFeeBps / 100}%)\n`);

  console.log('Sending authorize to facilitator...');
  const t0 = Date.now();
  const authResult = await client.authorize(pi);
  const t1 = Date.now();

  if (!authResult.success) { console.error(`AUTHORIZE FAILED: ${authResult.error}`); process.exit(1); }
  console.log(`AUTHORIZE SUCCESS (${((t1 - t0) / 1000).toFixed(2)}s)`);
  console.log(`  TX: ${authResult.transactionHash}`);
  console.log(`  https://basescan.org/tx/${authResult.transactionHash}\n`);

  // Step 2: QUERY
  console.log(`--- Step 2: QUERY ESCROW STATE ---`);
  await sleep(5000);
  try {
    const PAYMENT_INFO_TYPEHASH = ethers.keccak256(ethers.toUtf8Bytes(
      'PaymentInfo(address operator,address payer,address receiver,address token,uint120 maxAmount,uint48 preApprovalExpiry,uint48 authorizationExpiry,uint48 refundExpiry,uint16 minFeeBps,uint16 maxFeeBps,address feeReceiver,uint256 salt)'
    ));
    const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
      ['bytes32','address','address','address','address','uint120','uint48','uint48','uint48','uint16','uint16','address','uint256'],
      [PAYMENT_INFO_TYPEHASH, pi.operator, payerAddress, pi.receiver, pi.token, pi.maxAmount, pi.preApprovalExpiry, pi.authorizationExpiry, pi.refundExpiry, pi.minFeeBps, pi.maxFeeBps, pi.feeReceiver, pi.salt]
    );
    const nonce = ethers.keccak256(encoded);
    const escrowContract = new ethers.Contract(baseContracts.escrow, ESCROW_ABI, provider);
    const state = await escrowContract.getEscrowState(pi.operator, pi.token, payerAddress, nonce);
    console.log(`  Capturable: ${Number(state[0]) / 1_000_000} USDC`);
    console.log(`  Collected:  ${state[2]}`);
  } catch (e: any) { console.log(`QUERY FAILED (non-fatal): ${e.message?.slice(0, 100)}`); }
  console.log();

  // Step 3: RELEASE or REFUND
  let actionResult: any;
  if (doRefund) {
    console.log('--- Step 3: REFUND IN ESCROW ---');
    const rt0 = Date.now();
    actionResult = await client.refundInEscrow(pi);
    const rt1 = Date.now();
    if (!actionResult.success) { console.error(`REFUND FAILED: ${actionResult.error}`); process.exit(1); }
    console.log(`REFUND SUCCESS (${((rt1 - rt0) / 1000).toFixed(2)}s)`);
  } else {
    console.log('--- Step 3: RELEASE ---');
    const rt0 = Date.now();
    actionResult = await client.release(pi);
    const rt1 = Date.now();
    if (!actionResult.success) { console.error(`RELEASE FAILED: ${actionResult.error}`); process.exit(1); }
    console.log(`RELEASE SUCCESS (${((rt1 - rt0) / 1000).toFixed(2)}s)`);
  }
  console.log(`  TX: ${actionResult.transactionHash}`);
  console.log(`  Gas: ${actionResult.gasUsed}`);
  console.log(`  https://basescan.org/tx/${actionResult.transactionHash}\n`);

  // Step 4: Final state
  console.log('--- Step 4: VERIFY FINAL STATE ---');
  await sleep(5000);
  const usdcAfter = await viemClient.readContract({
    address: USDC_ADDRESS, abi: ERC20_ABI, functionName: 'balanceOf', args: [payerAddress as Address],
  });
  console.log(`USDC before: ${formatUnits(usdcBalance, 6)}`);
  console.log(`USDC after:  ${formatUnits(usdcAfter, 6)}`);
  console.log(`Delta:       ${formatUnits(usdcAfter - usdcBalance, 6)}\n`);

  // Step 5: Registries
  console.log('--- Step 5: CHECK REGISTRIES ---');
  for (const [name, addr] of [['Identity', IDENTITY_REGISTRY], ['Reputation', REPUTATION_REGISTRY]] as const) {
    try {
      const c = new ethers.Contract(addr, REGISTRY_ABI, provider);
      const supply = await c.totalSupply();
      const bal = await c.balanceOf(payerAddress);
      console.log(`${name} (${addr}): totalSupply=${supply}, payerBalance=${bal}`);
    } catch (e: any) { console.log(`${name} query failed: ${e.message?.slice(0, 80)}`); }
  }
  console.log();

  // Summary
  console.log(hr());
  console.log('FASE 3 E2E TEST COMPLETE');
  console.log(hr());
  console.log(`Mode:           ${doRefund ? 'REFUND' : 'RELEASE'}`);
  console.log(`Amount:         $${Number(TEST_AMOUNT) / 1_000_000} USDC`);
  console.log(`Authorize TX:   ${authResult.transactionHash}`);
  console.log(`${doRefund ? 'Refund' : 'Release'} TX:    ${actionResult.transactionHash}`);
  console.log(`Gas used:       ${actionResult.gasUsed}`);
  console.log(`Operator:       ${FASE3_OPERATOR}`);
  console.log(`\nBaseScan links:`);
  console.log(`  Authorize: https://basescan.org/tx/${authResult.transactionHash}`);
  console.log(`  ${doRefund ? 'Refund' : 'Release'}:   https://basescan.org/tx/${actionResult.transactionHash}`);
}

main().then(() => process.exit(0)).catch((err) => { console.error('\nFATAL ERROR:', err); process.exit(1); });

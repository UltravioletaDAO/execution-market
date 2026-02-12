/**
 * Deploy PaymentOperator for Execution Market on Base Mainnet
 *
 * This script deploys a PaymentOperator via the x402r factory contracts.
 *
 * Fase 2 (default): Facilitator-only release/refund, no protocol fees.
 * Fase 3 (--fase3):  OR(Payer, Facilitator) release/refund + StaticFeeCalculator (1% to BackTrack).
 *
 * Usage:
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --dry-run
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase3
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase3 --dry-run
 *
 * Environment:
 *   PRIVATE_KEY  - Wallet with ETH on Base for gas (~$2-5)
 *   RPC_URL      - (optional) Base RPC URL, defaults to https://mainnet.base.org
 */

import { createPublicClient, createWalletClient, http, parseAbi, getAddress, type Hex, type Address } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env.local" });

// ============================================================
// Configuration
// ============================================================

const FACILITATOR_ADDRESS: Address = "0x103040545AC5031A11E8C03dd11324C7333a13C7";
const ZERO_ADDRESS: Address = "0x0000000000000000000000000000000000000000";

// Base Mainnet x402r contract addresses (from @x402r/core config)
const ADDRESSES = {
  // Factories
  paymentOperatorFactory: "0x3D0837fF8Ea36F417261577b9BA568400A840260" as Address,
  staticAddressConditionFactory: "0x206D4DbB6E7b876e4B5EFAAD2a04e7d7813FB6ba" as Address,
  escrowPeriodFactory: "0x12EDefd4549c53497689067f165c0f101796Eb6D" as Address,
  orConditionFactory: "0x1e52a74cE6b69F04a506eF815743E1052A1BD28F" as Address,
  staticFeeCalculatorFactory: "0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0" as Address,

  // Protocol singletons
  authCaptureEscrow: "0xb9488351E48b23D798f24e8174514F28B741Eb4f" as Address,
  protocolFeeConfig: "0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6" as Address,
  usdcTvlLimit: "0x67B63Af4bcdCD3E4263d9995aB04563fbC229944" as Address,
  tokenCollector: "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8" as Address,

  // Condition singletons
  payerCondition: "0x7254b68D7262FE82e0638927C23bBFe3cc3E7E10" as Address,
  receiverCondition: "0x6926c05193c714ED4bA3867Ee93d6816Fdc14128" as Address,
  alwaysTrueCondition: "0xBAF68176FF94CAdD403EF7FbB776bbca548AC09D" as Address,

  // Existing Fase 2 deployment (StaticAddressCondition for Facilitator)
  facilitatorCondition: "0x9d03c03c15563E72CF2186E9FDB859A00ea661fc" as Address,

  // EM-specific
  emTreasury: "YOUR_TREASURY_WALLET" as Address,
};

// TODO: Get actual address from Ali Abdoli (BackTrack/x402r)
const BACKTRACK_TREASURY: Address = "0x0000000000000000000000000000000000000000";

// Fase 3: 1% protocol fee to BackTrack (100 basis points)
const BACKTRACK_FEE_BPS = 100;

// ============================================================
// ABIs (minimal, only what we need)
// ============================================================

const StaticAddressConditionFactoryABI = parseAbi([
  "function deploy(address designatedAddress) external returns (address)",
  "function getDeployed(address designatedAddress) external view returns (address)",
]);

const EscrowPeriodFactoryABI = parseAbi([
  "function deploy(uint256 escrowPeriodSeconds, bytes32 authorizedCodehash) external returns (address)",
  "function getDeployed(uint256 escrowPeriodSeconds, bytes32 authorizedCodehash) external view returns (address)",
]);

const PaymentOperatorFactoryABI = parseAbi([
  "function deployOperator((address feeRecipient, address feeCalculator, address authorizeCondition, address authorizeRecorder, address chargeCondition, address chargeRecorder, address releaseCondition, address releaseRecorder, address refundInEscrowCondition, address refundInEscrowRecorder, address refundPostEscrowCondition, address refundPostEscrowRecorder) config) external returns (address)",
  "function getOperator((address feeRecipient, address feeCalculator, address authorizeCondition, address authorizeRecorder, address chargeCondition, address chargeRecorder, address releaseCondition, address releaseRecorder, address refundInEscrowCondition, address refundInEscrowRecorder, address refundPostEscrowCondition, address refundPostEscrowRecorder) config) external view returns (address)",
]);

const OrConditionFactoryABI = parseAbi([
  "function deploy(address conditionA, address conditionB) external returns (address)",
  "function getDeployed(address conditionA, address conditionB) external view returns (address)",
]);

const StaticFeeCalculatorFactoryABI = parseAbi([
  "function deploy(address feeRecipient, uint16 feeBps) external returns (address)",
  "function getDeployed(address feeRecipient, uint16 feeBps) external view returns (address)",
]);

// ============================================================
// Main
// ============================================================

async function main() {
  const isDryRun = process.argv.includes("--dry-run");
  const isFase3 = process.argv.includes("--fase3");

  // Get private key
  const privateKey = (process.env.PRIVATE_KEY || process.env.WALLET_PRIVATE_KEY) as Hex | undefined;
  if (!privateKey) {
    console.error("ERROR: Set PRIVATE_KEY or WALLET_PRIVATE_KEY environment variable");
    process.exit(1);
  }

  const account = privateKeyToAccount(privateKey);
  const rpcUrl = process.env.RPC_URL || "https://mainnet.base.org";

  console.log("=".repeat(60));
  console.log(`Deploy PaymentOperator for Execution Market (${isFase3 ? "Fase 3" : "Fase 2"})`);
  console.log("=".repeat(60));
  console.log(`Network:      Base Mainnet (chain ${base.id})`);
  console.log(`RPC:          ${rpcUrl}`);
  console.log(`Deployer:     ${account.address}`);
  console.log(`Facilitator:  ${FACILITATOR_ADDRESS}`);
  console.log(`Mode:         ${isFase3 ? "Fase 3 — OR(Payer, Facilitator) + StaticFeeCalculator" : "Fase 2 — Facilitator-only"}`);
  console.log(`Dry run:      ${isDryRun}`);
  console.log("");

  if (isFase3 && BACKTRACK_TREASURY === ZERO_ADDRESS) {
    console.warn("WARNING: BACKTRACK_TREASURY is address(0). Fee revenue will be unclaimable.");
    console.warn("         Get the real address from Ali Abdoli before deploying to production.\n");
  }

  const publicClient = createPublicClient({
    chain: base,
    transport: http(rpcUrl),
  });

  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http(rpcUrl),
  });

  // Check deployer ETH balance
  const balance = await publicClient.getBalance({ address: account.address });
  const ethBalance = Number(balance) / 1e18;
  console.log(`Deployer ETH: ${ethBalance.toFixed(6)} ETH`);
  if (ethBalance < 0.001) {
    console.error("ERROR: Insufficient ETH for gas. Need at least 0.001 ETH.");
    process.exit(1);
  }

  if (isFase3) {
    await deployFase3(publicClient, walletClient, isDryRun);
  } else {
    await deployFase2(publicClient, walletClient, isDryRun);
  }
}

// ============================================================
// Fase 2: Facilitator-only release/refund, no protocol fees
// ============================================================

async function deployFase2(
  publicClient: ReturnType<typeof createPublicClient>,
  walletClient: ReturnType<typeof createWalletClient>,
  isDryRun: boolean,
) {
  // ============================================================
  // Step 1: Deploy StaticAddressCondition for Facilitator
  // ============================================================
  console.log("\n--- Step 1: StaticAddressCondition(Facilitator) ---");

  let facilitatorCondition: Address;
  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.staticAddressConditionFactory,
      abi: StaticAddressConditionFactoryABI,
      functionName: "getDeployed",
      args: [FACILITATOR_ADDRESS],
    });

    if (existing && existing !== ZERO_ADDRESS) {
      facilitatorCondition = existing;
      console.log(`Already deployed at: ${facilitatorCondition}`);
    } else {
      throw new Error("Not deployed");
    }
  } catch {
    if (isDryRun) {
      console.log("DRY RUN: Would deploy StaticAddressCondition(Facilitator)");
      facilitatorCondition = "0x_DRY_RUN_CONDITION" as Address;
    } else {
      console.log("Deploying StaticAddressCondition for Facilitator...");
      const hash = await walletClient.writeContract({
        address: ADDRESSES.staticAddressConditionFactory,
        abi: StaticAddressConditionFactoryABI,
        functionName: "deploy",
        args: [FACILITATOR_ADDRESS],
      });
      console.log(`TX: ${hash}`);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

      facilitatorCondition = await publicClient.readContract({
        address: ADDRESSES.staticAddressConditionFactory,
        abi: StaticAddressConditionFactoryABI,
        functionName: "getDeployed",
        args: [FACILITATOR_ADDRESS],
      });
      console.log(`Deployed at: ${facilitatorCondition}`);
    }
  }

  // ============================================================
  // Step 2: Deploy PaymentOperator
  // ============================================================
  console.log("\n--- Step 2: PaymentOperator ---");

  const operatorConfig = {
    feeRecipient: ADDRESSES.emTreasury,
    feeCalculator: ZERO_ADDRESS,
    authorizeCondition: ADDRESSES.usdcTvlLimit,
    authorizeRecorder: ZERO_ADDRESS,
    chargeCondition: ZERO_ADDRESS,
    chargeRecorder: ZERO_ADDRESS,
    releaseCondition: facilitatorCondition,
    releaseRecorder: ZERO_ADDRESS,
    refundInEscrowCondition: facilitatorCondition,
    refundInEscrowRecorder: ZERO_ADDRESS,
    refundPostEscrowCondition: ZERO_ADDRESS,
    refundPostEscrowRecorder: ZERO_ADDRESS,
  };

  logOperatorConfig(operatorConfig, {
    [facilitatorCondition]: "(Facilitator-only)",
    [ADDRESSES.usdcTvlLimit]: "(UsdcTvlLimit)",
    [ADDRESSES.emTreasury]: "(EM Treasury)",
  });

  const operatorAddress = await deployOrGetOperator(publicClient, walletClient, operatorConfig, isDryRun);

  // Summary
  printSummary({
    mode: "Fase 2 — Facilitator-only",
    facilitatorCondition,
    operatorAddress,
  });
}

// ============================================================
// Fase 3: OR(Payer, Facilitator) + StaticFeeCalculator
// ============================================================

async function deployFase3(
  publicClient: ReturnType<typeof createPublicClient>,
  walletClient: ReturnType<typeof createWalletClient>,
  isDryRun: boolean,
) {
  // ============================================================
  // Step 1: Deploy StaticFeeCalculator
  // ============================================================
  console.log("\n--- Step 1: StaticFeeCalculator(BackTrack, 100bps) ---");

  let feeCalculator: Address;
  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.staticFeeCalculatorFactory,
      abi: StaticFeeCalculatorFactoryABI,
      functionName: "getDeployed",
      args: [BACKTRACK_TREASURY, BACKTRACK_FEE_BPS],
    });

    if (existing && existing !== ZERO_ADDRESS) {
      feeCalculator = existing;
      console.log(`Already deployed at: ${feeCalculator}`);
    } else {
      throw new Error("Not deployed");
    }
  } catch {
    if (isDryRun) {
      console.log("DRY RUN: Would deploy StaticFeeCalculator");
      console.log(`  feeRecipient: ${BACKTRACK_TREASURY}`);
      console.log(`  feeBps:       ${BACKTRACK_FEE_BPS} (${BACKTRACK_FEE_BPS / 100}%)`);
      feeCalculator = "0x_DRY_RUN_FEE_CALC" as Address;
    } else {
      console.log("Deploying StaticFeeCalculator...");
      console.log(`  feeRecipient: ${BACKTRACK_TREASURY}`);
      console.log(`  feeBps:       ${BACKTRACK_FEE_BPS} (${BACKTRACK_FEE_BPS / 100}%)`);
      const hash = await walletClient.writeContract({
        address: ADDRESSES.staticFeeCalculatorFactory,
        abi: StaticFeeCalculatorFactoryABI,
        functionName: "deploy",
        args: [BACKTRACK_TREASURY, BACKTRACK_FEE_BPS],
      });
      console.log(`TX: ${hash}`);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

      feeCalculator = await publicClient.readContract({
        address: ADDRESSES.staticFeeCalculatorFactory,
        abi: StaticFeeCalculatorFactoryABI,
        functionName: "getDeployed",
        args: [BACKTRACK_TREASURY, BACKTRACK_FEE_BPS],
      });
      console.log(`Deployed at: ${feeCalculator}`);
    }
  }

  // ============================================================
  // Step 2: Deploy OrCondition(PayerCondition, FacilitatorCondition)
  // ============================================================
  console.log("\n--- Step 2: OrCondition(Payer, Facilitator) ---");

  let orCondition: Address;
  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.orConditionFactory,
      abi: OrConditionFactoryABI,
      functionName: "getDeployed",
      args: [ADDRESSES.payerCondition, ADDRESSES.facilitatorCondition],
    });

    if (existing && existing !== ZERO_ADDRESS) {
      orCondition = existing;
      console.log(`Already deployed at: ${orCondition}`);
    } else {
      throw new Error("Not deployed");
    }
  } catch {
    if (isDryRun) {
      console.log("DRY RUN: Would deploy OrCondition");
      console.log(`  conditionA: ${ADDRESSES.payerCondition} (PayerCondition)`);
      console.log(`  conditionB: ${ADDRESSES.facilitatorCondition} (FacilitatorCondition)`);
      orCondition = "0x_DRY_RUN_OR_COND" as Address;
    } else {
      console.log("Deploying OrCondition...");
      console.log(`  conditionA: ${ADDRESSES.payerCondition} (PayerCondition)`);
      console.log(`  conditionB: ${ADDRESSES.facilitatorCondition} (FacilitatorCondition)`);
      const hash = await walletClient.writeContract({
        address: ADDRESSES.orConditionFactory,
        abi: OrConditionFactoryABI,
        functionName: "deploy",
        args: [ADDRESSES.payerCondition, ADDRESSES.facilitatorCondition],
      });
      console.log(`TX: ${hash}`);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

      orCondition = await publicClient.readContract({
        address: ADDRESSES.orConditionFactory,
        abi: OrConditionFactoryABI,
        functionName: "getDeployed",
        args: [ADDRESSES.payerCondition, ADDRESSES.facilitatorCondition],
      });
      console.log(`Deployed at: ${orCondition}`);
    }
  }

  // ============================================================
  // Step 3: Deploy PaymentOperator with Fase 3 config
  // ============================================================
  console.log("\n--- Step 3: PaymentOperator (Fase 3) ---");

  // Fase 3 operator config:
  // - feeRecipient: EM treasury (receives EM-level fees)
  // - feeCalculator: StaticFeeCalculator (1% to BackTrack treasury)
  // - authorizeCondition: UsdcTvlLimit (protocol safety)
  // - authorizeRecorder: address(0)
  // - chargeCondition/Recorder: address(0) (not used by EM)
  // - releaseCondition: OR(Payer, Facilitator) — payer OR facilitator can release
  // - releaseRecorder: address(0)
  // - refundInEscrowCondition: OR(Payer, Facilitator) — payer OR facilitator can refund
  // - refundInEscrowRecorder: address(0)
  // - refundPostEscrowCondition: address(0)
  // - refundPostEscrowRecorder: address(0)

  const operatorConfig = {
    feeRecipient: ADDRESSES.emTreasury,
    feeCalculator: feeCalculator,
    authorizeCondition: ADDRESSES.usdcTvlLimit,
    authorizeRecorder: ZERO_ADDRESS,
    chargeCondition: ZERO_ADDRESS,
    chargeRecorder: ZERO_ADDRESS,
    releaseCondition: orCondition,
    releaseRecorder: ZERO_ADDRESS,
    refundInEscrowCondition: orCondition,
    refundInEscrowRecorder: ZERO_ADDRESS,
    refundPostEscrowCondition: ZERO_ADDRESS,
    refundPostEscrowRecorder: ZERO_ADDRESS,
  };

  logOperatorConfig(operatorConfig, {
    [feeCalculator]: `(StaticFeeCalculator ${BACKTRACK_FEE_BPS}bps)`,
    [orCondition]: "(OR: Payer | Facilitator)",
    [ADDRESSES.usdcTvlLimit]: "(UsdcTvlLimit)",
    [ADDRESSES.emTreasury]: "(EM Treasury)",
  });

  const operatorAddress = await deployOrGetOperator(publicClient, walletClient, operatorConfig, isDryRun);

  // Summary
  printSummary({
    mode: "Fase 3 — OR(Payer, Facilitator) + StaticFeeCalculator",
    feeCalculator,
    orCondition,
    operatorAddress,
  });
}

// ============================================================
// Shared helpers
// ============================================================

function logOperatorConfig(config: Record<string, Address>, labels: Record<string, string>) {
  console.log("Operator config:");
  for (const [key, val] of Object.entries(config)) {
    const label = val === ZERO_ADDRESS ? "(permissive)" : (labels[val] || "");
    console.log(`  ${key.padEnd(30)} ${val} ${label}`);
  }
}

async function deployOrGetOperator(
  publicClient: ReturnType<typeof createPublicClient>,
  walletClient: ReturnType<typeof createWalletClient>,
  config: Record<string, Address>,
  isDryRun: boolean,
): Promise<Address> {
  const configTuple = [
    config.feeRecipient,
    config.feeCalculator,
    config.authorizeCondition,
    config.authorizeRecorder,
    config.chargeCondition,
    config.chargeRecorder,
    config.releaseCondition,
    config.releaseRecorder,
    config.refundInEscrowCondition,
    config.refundInEscrowRecorder,
    config.refundPostEscrowCondition,
    config.refundPostEscrowRecorder,
  ] as const;

  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.paymentOperatorFactory,
      abi: PaymentOperatorFactoryABI,
      functionName: "getOperator",
      args: [configTuple],
    });

    if (existing && existing !== ZERO_ADDRESS) {
      console.log(`\nAlready deployed at: ${existing}`);
      return existing;
    }
    throw new Error("Not deployed");
  } catch {
    if (isDryRun) {
      console.log("\nDRY RUN: Would deploy PaymentOperator");
      return "0x_DRY_RUN_OPERATOR" as Address;
    }

    console.log("\nDeploying PaymentOperator...");
    const hash = await walletClient.writeContract({
      address: ADDRESSES.paymentOperatorFactory,
      abi: PaymentOperatorFactoryABI,
      functionName: "deployOperator",
      args: [configTuple],
    });
    console.log(`TX: ${hash}`);
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

    const deployed = await publicClient.readContract({
      address: ADDRESSES.paymentOperatorFactory,
      abi: PaymentOperatorFactoryABI,
      functionName: "getOperator",
      args: [configTuple],
    });
    console.log(`Deployed at: ${deployed}`);
    return deployed;
  }
}

function printSummary(params: {
  mode: string;
  facilitatorCondition?: Address;
  feeCalculator?: Address;
  orCondition?: Address;
  operatorAddress: Address;
}) {
  console.log("\n" + "=".repeat(60));
  console.log("DEPLOYMENT SUMMARY");
  console.log("=".repeat(60));
  console.log(`Mode:                      ${params.mode}`);
  console.log(`Network:                   Base Mainnet (${base.id})`);
  if (params.facilitatorCondition) {
    console.log(`StaticAddressCondition:    ${params.facilitatorCondition}`);
  }
  if (params.feeCalculator) {
    console.log(`StaticFeeCalculator:       ${params.feeCalculator}`);
  }
  if (params.orCondition) {
    console.log(`OrCondition:               ${params.orCondition}`);
  }
  console.log(`PaymentOperator:           ${params.operatorAddress}`);
  console.log(`AuthCaptureEscrow:         ${ADDRESSES.authCaptureEscrow}`);
  console.log(`TokenCollector:            ${ADDRESSES.tokenCollector}`);
  console.log(`Facilitator (authorized):  ${FACILITATOR_ADDRESS}`);
  console.log(`EM Treasury (feeRecipient):${ADDRESSES.emTreasury}`);
  console.log("");
  console.log("Next steps:");
  console.log("1. Register operatorAddress in facilitator addresses.rs");
  console.log("2. Rebuild + redeploy facilitator");
  console.log("3. Test escrow lifecycle: authorize -> release / refundInEscrow");
  console.log("");
  console.log("Facilitator addresses.rs entry:");
  console.log(`  payment_operator: Some("${params.operatorAddress}"),`);
  console.log(`  token_collector: Some("${ADDRESSES.tokenCollector}"),`);
}

main().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});

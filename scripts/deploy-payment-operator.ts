/**
 * Deploy PaymentOperator for Execution Market on Base Mainnet
 *
 * This script deploys a PaymentOperator via the x402r factory contracts.
 *
 * Fase 2 (default): Facilitator-only release/refund, no protocol fees.
 * Fase 3 (--fase3):  OR(Payer, Facilitator) release/refund + StaticFeeCalculator (1% operator fee to EM treasury).
 * Fase 3 Clean (--fase3-clean): OR(Payer, Facilitator) release/refund, feeCalculator=address(0) (no on-chain operator fee).
 *                                Reuses existing OrCondition. x402r earns protocol fees via ProtocolFeeConfig, not operator fees.
 * Fase 4 (--fase4):  SECURE operator — OR(Payer|Facilitator) release, Facilitator-ONLY refund, feeCalculator=address(0).
 *                    Fixes security vulnerability: payer can no longer call refundInEscrow() directly on-chain.
 *
 * Usage:
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --dry-run
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase3
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase3 --dry-run
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase3-clean
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase3-clean --dry-run
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase4
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --fase4 --dry-run
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

  // Condition singletons (verified on-chain — have bytecode)
  payerCondition: "0x7254b68D1AaAbd118C8A8b15756b4654c10a16d2" as Address,
  receiverCondition: "0x6926c05193c714ED4bA3867Ee93d6816Fdc14128" as Address,
  alwaysTrueCondition: "0xBAF68176FF94CAdD403EF7FbB776bbca548AC09D" as Address,

  // Existing Fase 2 deployment (StaticAddressCondition for Facilitator)
  facilitatorCondition: "0x9d03c03c15563E72CF2186E9FDB859A00ea661fc" as Address,

  // Existing Fase 3 deployment: OrCondition(PayerCondition, FacilitatorCondition)
  orConditionPayerFacilitator: "0xb365717C35004089996F72939b0C5b32Fa2ef8aE" as Address,

  // EM-specific
  emTreasury: "YOUR_TREASURY_WALLET" as Address,
};

// Fase 3: 1% operator fee (100 basis points)
// FEE_RECIPIENT is set on the PaymentOperator (already = EM treasury).
// StaticFeeCalculator only takes feeBps, NOT a recipient address.
// Ali confirmed: "The configurable fee options are for you not us."
// BackTrack collects their own fees via ProtocolFeeConfig (currently 0% on Base).
const OPERATOR_FEE_BPS = 100;

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
  "function deploy(address[] conditions) external returns (address)",
  "function getDeployed(address[] conditions) external view returns (address)",
]);

const StaticFeeCalculatorFactoryABI = parseAbi([
  "function deploy(uint256 feeBps) external returns (address)",
  "function getDeployed(uint256 feeBps) external view returns (address)",
]);

// PaymentOperator read-only ABI for on-chain verification
const PaymentOperatorReadABI = parseAbi([
  "function FEE_CALCULATOR() external view returns (address)",
  "function RELEASE_CONDITION() external view returns (address)",
  "function REFUND_IN_ESCROW_CONDITION() external view returns (address)",
]);

// ============================================================
// Main
// ============================================================

async function main() {
  const isDryRun = process.argv.includes("--dry-run");
  const isFase3 = process.argv.includes("--fase3");
  const isFase3Clean = process.argv.includes("--fase3-clean");
  const isFase4 = process.argv.includes("--fase4");

  const modeLabel = isFase4
    ? "Fase 4 (Secure)"
    : isFase3Clean
      ? "Fase 3 Clean"
      : isFase3
        ? "Fase 3"
        : "Fase 2";

  const modeDescription = isFase4
    ? "Fase 4 — OR(Payer, Facilitator) release, Facilitator-ONLY refund, feeCalculator=address(0)"
    : isFase3Clean
      ? "Fase 3 Clean — OR(Payer, Facilitator), feeCalculator=address(0)"
      : isFase3
        ? "Fase 3 — OR(Payer, Facilitator) + StaticFeeCalculator"
        : "Fase 2 — Facilitator-only";

  // Get private key
  const privateKey = (process.env.PRIVATE_KEY || process.env.WALLET_PRIVATE_KEY) as Hex | undefined;
  if (!privateKey) {
    console.error("ERROR: Set PRIVATE_KEY or WALLET_PRIVATE_KEY environment variable");
    process.exit(1);
  }

  const account = privateKeyToAccount(privateKey);
  const rpcUrl = process.env.RPC_URL || "https://mainnet.base.org";

  console.log("=".repeat(60));
  console.log(`Deploy PaymentOperator for Execution Market (${modeLabel})`);
  console.log("=".repeat(60));
  console.log(`Network:      Base Mainnet (chain ${base.id})`);
  console.log(`RPC:          ${rpcUrl}`);
  console.log(`Deployer:     ${account.address}`);
  console.log(`Facilitator:  ${FACILITATOR_ADDRESS}`);
  console.log(`Mode:         ${modeDescription}`);
  console.log(`Dry run:      ${isDryRun}`);
  console.log("");

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

  if (isFase4) {
    await deployFase4(publicClient, walletClient, isDryRun);
  } else if (isFase3Clean) {
    await deployFase3Clean(publicClient, walletClient, isDryRun);
  } else if (isFase3) {
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
  console.log(`\n--- Step 1: StaticFeeCalculator(${OPERATOR_FEE_BPS}bps = ${OPERATOR_FEE_BPS / 100}%) ---`);
  console.log(`  Fee goes to FEE_RECIPIENT on operator (EM treasury ${ADDRESSES.emTreasury})`);

  let feeCalculator: Address;
  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.staticFeeCalculatorFactory,
      abi: StaticFeeCalculatorFactoryABI,
      functionName: "getDeployed",
      args: [BigInt(OPERATOR_FEE_BPS)],
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
      console.log(`  feeBps: ${OPERATOR_FEE_BPS} (${OPERATOR_FEE_BPS / 100}%)`);
      feeCalculator = "0x_DRY_RUN_FEE_CALC" as Address;
    } else {
      console.log("Deploying StaticFeeCalculator...");
      console.log(`  feeBps: ${OPERATOR_FEE_BPS} (${OPERATOR_FEE_BPS / 100}%)`);
      const hash = await walletClient.writeContract({
        address: ADDRESSES.staticFeeCalculatorFactory,
        abi: StaticFeeCalculatorFactoryABI,
        functionName: "deploy",
        args: [BigInt(OPERATOR_FEE_BPS)],
      });
      console.log(`TX: ${hash}`);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

      // Wait for RPC to index, then look up via factory
      feeCalculator = await publicClient.readContract({
        address: ADDRESSES.staticFeeCalculatorFactory,
        abi: StaticFeeCalculatorFactoryABI,
        functionName: "getDeployed",
        args: [BigInt(OPERATOR_FEE_BPS)],
      });

      // Fallback: extract from TX receipt logs if getDeployed returns zero
      if (!feeCalculator || feeCalculator === ZERO_ADDRESS) {
        console.log("  getDeployed() returned zero — extracting from TX logs...");
        const deployed = extractDeployedAddress(receipt);
        if (deployed) {
          feeCalculator = deployed;
        } else {
          console.error("FATAL: Could not determine deployed address from TX receipt");
          process.exit(1);
        }
      }
      console.log(`Deployed at: ${feeCalculator}`);
    }
  }

  // ============================================================
  // Step 2: Deploy OrCondition(PayerCondition, FacilitatorCondition)
  // ============================================================
  console.log("\n--- Step 2: OrCondition(Payer, Facilitator) ---");

  const orConditions: Address[] = [ADDRESSES.payerCondition, ADDRESSES.facilitatorCondition];

  let orCondition: Address;
  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.orConditionFactory,
      abi: OrConditionFactoryABI,
      functionName: "getDeployed",
      args: [orConditions],
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
      console.log(`  conditions[0]: ${ADDRESSES.payerCondition} (PayerCondition)`);
      console.log(`  conditions[1]: ${ADDRESSES.facilitatorCondition} (StaticAddressCondition(Facilitator))`);
      orCondition = "0x_DRY_RUN_OR_COND" as Address;
    } else {
      console.log("Deploying OrCondition...");
      console.log(`  conditions[0]: ${ADDRESSES.payerCondition} (PayerCondition)`);
      console.log(`  conditions[1]: ${ADDRESSES.facilitatorCondition} (StaticAddressCondition(Facilitator))`);
      const hash = await walletClient.writeContract({
        address: ADDRESSES.orConditionFactory,
        abi: OrConditionFactoryABI,
        functionName: "deploy",
        args: [orConditions],
      });
      console.log(`TX: ${hash}`);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

      // Wait for RPC to index, then look up via factory
      orCondition = await publicClient.readContract({
        address: ADDRESSES.orConditionFactory,
        abi: OrConditionFactoryABI,
        functionName: "getDeployed",
        args: [orConditions],
      });

      // Fallback: extract from TX receipt logs if getDeployed returns zero
      if (!orCondition || orCondition === ZERO_ADDRESS) {
        console.log("  getDeployed() returned zero — extracting from TX logs...");
        const deployed = extractDeployedAddress(receipt);
        if (deployed) {
          orCondition = deployed;
        } else {
          console.error("FATAL: Could not determine deployed address from TX receipt");
          process.exit(1);
        }
      }
      console.log(`Deployed at: ${orCondition}`);
    }
  }

  // ============================================================
  // Step 3: Deploy PaymentOperator with Fase 3 config
  // ============================================================
  console.log("\n--- Step 3: PaymentOperator (Fase 3) ---");

  // CRITICAL: Validate that Steps 1 & 2 produced real addresses
  if (feeCalculator === ZERO_ADDRESS) {
    console.error("FATAL: StaticFeeCalculator address is zero — cannot deploy PaymentOperator with wrong config");
    process.exit(1);
  }
  if (orCondition === ZERO_ADDRESS) {
    console.error("FATAL: OrCondition address is zero — cannot deploy PaymentOperator with wrong config");
    process.exit(1);
  }

  // Fase 3 operator config:
  // - feeRecipient: EM treasury (receives 1% on-chain operator fee)
  // - feeCalculator: StaticFeeCalculator (1% = 100 BPS)
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
    [feeCalculator]: `(StaticFeeCalculator ${OPERATOR_FEE_BPS}bps)`,
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
// Fase 3 Clean: OR(Payer, Facilitator), feeCalculator=address(0)
// No on-chain operator fee. Reuses existing OrCondition.
// ============================================================

async function deployFase3Clean(
  publicClient: ReturnType<typeof createPublicClient>,
  walletClient: ReturnType<typeof createWalletClient>,
  isDryRun: boolean,
) {
  // ============================================================
  // Step 1: Verify OrCondition exists on-chain (reuse, no deploy)
  // ============================================================
  console.log("\n--- Step 1: Verify existing OrCondition(Payer, Facilitator) ---");
  console.log(`  Expected: ${ADDRESSES.orConditionPayerFacilitator}`);

  const orCondition = ADDRESSES.orConditionPayerFacilitator;

  if (!isDryRun) {
    const bytecode = await publicClient.getCode({ address: orCondition });
    if (!bytecode || bytecode === "0x") {
      console.error(`FATAL: OrCondition at ${orCondition} has no bytecode — is this the right address?`);
      process.exit(1);
    }
    console.log(`  Verified: contract exists (${bytecode.length / 2 - 1} bytes)`);
  } else {
    console.log(`  DRY RUN: Would verify bytecode at ${orCondition}`);
  }

  // ============================================================
  // Step 2: Deploy PaymentOperator with feeCalculator=address(0)
  // ============================================================
  console.log("\n--- Step 2: PaymentOperator (Fase 3 Clean) ---");

  // Fase 3 Clean config:
  // - feeRecipient: EM Treasury — required by factory (can't be address(0)),
  //   but no fee is actually charged because feeCalculator=address(0)
  // - feeCalculator: address(0) — NO on-chain operator fee
  // - authorizeCondition: UsdcTvlLimit (protocol safety)
  // - releaseCondition: OR(Payer, Facilitator) — payer OR facilitator can release
  // - refundInEscrowCondition: OR(Payer, Facilitator) — payer OR facilitator can refund
  // - Everything else: address(0) (permissive/unused)
  // Note: Only ProtocolFeeConfig (controlled by x402r team) can take on-chain fees.

  const operatorConfig = {
    feeRecipient: ADDRESSES.emTreasury,  // Factory requires non-zero; no fee charged since calculator=0
    feeCalculator: ZERO_ADDRESS,
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
    [orCondition]: "(OR: Payer | Facilitator)",
    [ADDRESSES.usdcTvlLimit]: "(UsdcTvlLimit)",
  });

  const operatorAddress = await deployOrGetOperator(publicClient, walletClient, operatorConfig, isDryRun);

  // ============================================================
  // Step 3: On-chain verification
  // ============================================================
  if (!isDryRun && operatorAddress !== ("0x_DRY_RUN_OPERATOR" as Address)) {
    console.log("\n--- Step 3: On-chain verification ---");

    const feeCalc = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "FEE_CALCULATOR",
    });
    const releaseCond = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "RELEASE_CONDITION",
    });
    const refundCond = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "REFUND_IN_ESCROW_CONDITION",
    });

    const checks = [
      { name: "FEE_CALCULATOR() == address(0)", actual: feeCalc, expected: ZERO_ADDRESS },
      { name: "RELEASE_CONDITION() == OrCondition", actual: releaseCond, expected: orCondition },
      { name: "REFUND_IN_ESCROW_CONDITION() == OrCondition", actual: refundCond, expected: orCondition },
    ];

    let allPassed = true;
    for (const check of checks) {
      const passed = check.actual.toLowerCase() === check.expected.toLowerCase();
      console.log(`  ${passed ? "PASS" : "FAIL"}: ${check.name}`);
      console.log(`         got:      ${check.actual}`);
      console.log(`         expected: ${check.expected}`);
      if (!passed) allPassed = false;
    }

    if (!allPassed) {
      console.error("\nFATAL: On-chain verification failed — operator config does not match expected values");
      process.exit(1);
    }
    console.log("\n  All on-chain checks passed.");
  }

  // Summary
  printSummary({
    mode: "Fase 3 Clean — OR(Payer, Facilitator), feeCalculator=address(0)",
    orCondition,
    operatorAddress,
  });
}

// ============================================================
// Fase 4: SECURE — OR(Payer, Facilitator) release, Facilitator-ONLY refund
// Fixes vulnerability: payer can no longer call refundInEscrow() directly.
// feeCalculator=address(0), no on-chain operator fee.
// ============================================================

async function deployFase4(
  publicClient: ReturnType<typeof createPublicClient>,
  walletClient: ReturnType<typeof createWalletClient>,
  isDryRun: boolean,
) {
  // ============================================================
  // Step 1: Verify existing conditions on-chain (reuse, no deploy)
  // ============================================================
  console.log("\n--- Step 1: Verify existing conditions ---");
  console.log(`  OrCondition(Payer, Facilitator):    ${ADDRESSES.orConditionPayerFacilitator}`);
  console.log(`  StaticAddressCondition(Facilitator): ${ADDRESSES.facilitatorCondition}`);

  const orCondition = ADDRESSES.orConditionPayerFacilitator;
  const facilitatorOnly = ADDRESSES.facilitatorCondition;

  if (!isDryRun) {
    // Verify OrCondition bytecode
    const orBytecode = await publicClient.getCode({ address: orCondition });
    if (!orBytecode || orBytecode === "0x") {
      console.error(`FATAL: OrCondition at ${orCondition} has no bytecode`);
      process.exit(1);
    }
    console.log(`  OrCondition verified: contract exists (${orBytecode.length / 2 - 1} bytes)`);

    // Verify StaticAddressCondition(Facilitator) bytecode
    const facBytecode = await publicClient.getCode({ address: facilitatorOnly });
    if (!facBytecode || facBytecode === "0x") {
      console.error(`FATAL: StaticAddressCondition at ${facilitatorOnly} has no bytecode`);
      process.exit(1);
    }
    console.log(`  FacilitatorCondition verified: contract exists (${facBytecode.length / 2 - 1} bytes)`);
  } else {
    console.log(`  DRY RUN: Would verify bytecode at both addresses`);
  }

  // ============================================================
  // Step 2: Deploy PaymentOperator with SECURE config
  // ============================================================
  console.log("\n--- Step 2: PaymentOperator (Fase 4 — Secure) ---");

  // Fase 4 Secure config:
  // - feeRecipient: EM Treasury — required by factory (non-zero), no fee charged (calculator=0)
  // - feeCalculator: address(0) — NO on-chain operator fee
  // - authorizeCondition: UsdcTvlLimit (protocol safety)
  // - releaseCondition: OR(Payer, Facilitator) — payer OR facilitator can release
  // - refundInEscrowCondition: StaticAddressCondition(Facilitator) — ONLY facilitator can refund
  //   (THIS IS THE KEY SECURITY FIX: payer cannot refund directly on-chain)
  // - Everything else: address(0) (permissive/unused)

  const operatorConfig = {
    feeRecipient: ADDRESSES.emTreasury,  // Factory requires non-zero; no fee since calculator=0
    feeCalculator: ZERO_ADDRESS,
    authorizeCondition: ADDRESSES.usdcTvlLimit,
    authorizeRecorder: ZERO_ADDRESS,
    chargeCondition: ZERO_ADDRESS,
    chargeRecorder: ZERO_ADDRESS,
    releaseCondition: orCondition,           // OR(Payer | Facilitator) — unchanged
    releaseRecorder: ZERO_ADDRESS,
    refundInEscrowCondition: facilitatorOnly, // Facilitator-ONLY (SECURITY FIX)
    refundInEscrowRecorder: ZERO_ADDRESS,
    refundPostEscrowCondition: ZERO_ADDRESS,
    refundPostEscrowRecorder: ZERO_ADDRESS,
  };

  logOperatorConfig(operatorConfig, {
    [orCondition]: "(OR: Payer | Facilitator)",
    [facilitatorOnly]: "(Facilitator-ONLY — SECURE)",
    [ADDRESSES.usdcTvlLimit]: "(UsdcTvlLimit)",
  });

  const operatorAddress = await deployOrGetOperator(publicClient, walletClient, operatorConfig, isDryRun);

  // ============================================================
  // Step 3: On-chain verification
  // ============================================================
  if (!isDryRun && operatorAddress !== ("0x_DRY_RUN_OPERATOR" as Address)) {
    console.log("\n--- Step 3: On-chain verification ---");

    const feeCalc = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "FEE_CALCULATOR",
    });
    const releaseCond = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "RELEASE_CONDITION",
    });
    const refundCond = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "REFUND_IN_ESCROW_CONDITION",
    });

    const checks = [
      { name: "FEE_CALCULATOR() == address(0)", actual: feeCalc, expected: ZERO_ADDRESS },
      { name: "RELEASE_CONDITION() == OrCondition(Payer|Facilitator)", actual: releaseCond, expected: orCondition },
      { name: "REFUND_IN_ESCROW_CONDITION() == StaticAddressCondition(Facilitator)", actual: refundCond, expected: facilitatorOnly },
    ];

    let allPassed = true;
    for (const check of checks) {
      const passed = check.actual.toLowerCase() === check.expected.toLowerCase();
      console.log(`  ${passed ? "PASS" : "FAIL"}: ${check.name}`);
      console.log(`         got:      ${check.actual}`);
      console.log(`         expected: ${check.expected}`);
      if (!passed) allPassed = false;
    }

    if (!allPassed) {
      console.error("\nFATAL: On-chain verification failed — operator config does not match expected values");
      process.exit(1);
    }
    console.log("\n  All on-chain checks passed.");

    // KEY SECURITY VERIFICATION: Confirm refund condition is NOT the OR condition
    if (refundCond.toLowerCase() === orCondition.toLowerCase()) {
      console.error("\nSECURITY ALERT: REFUND_IN_ESCROW_CONDITION is OrCondition — payer can still refund directly!");
      console.error("This defeats the purpose of Fase 4. DO NOT use this operator.");
      process.exit(1);
    }
    console.log("  SECURITY: Refund is Facilitator-only (payer CANNOT refund directly).");
  }

  // Summary
  printSummary({
    mode: "Fase 4 (Secure) — OR(Payer|Facilitator) release, Facilitator-ONLY refund",
    orCondition,
    operatorAddress,
  });

  console.log("");
  console.log("SECURITY NOTE:");
  console.log("  - Release: OR(Payer, Facilitator) — both can release (no change)");
  console.log(`  - Refund:  Facilitator-ONLY (${facilitatorOnly})`);
  console.log("  - Payer CANNOT call refundInEscrow() directly on-chain");
  console.log("  - This prevents frontrunning attacks where payer refunds after worker delivers");
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

    // Wait for RPC to index, then look up via factory
    let deployed = await publicClient.readContract({
      address: ADDRESSES.paymentOperatorFactory,
      abi: PaymentOperatorFactoryABI,
      functionName: "getOperator",
      args: [configTuple],
    });

    // Fallback: extract from TX receipt logs if getOperator returns zero
    if (!deployed || deployed === ZERO_ADDRESS) {
      console.log("  getOperator() returned zero — extracting from TX logs...");
      const fromLogs = extractDeployedAddress(receipt);
      if (fromLogs) {
        deployed = fromLogs;
      } else {
        console.error("FATAL: Could not determine deployed address from TX receipt");
        process.exit(1);
      }
    }
    console.log(`Deployed at: ${deployed}`);
    return deployed;
  }
}

/**
 * Extract the deployed contract address from a CREATE2 factory TX receipt.
 * Factories typically emit an event with the deployed address in the first topic/data.
 * We look for a 20-byte address in the log topics (after the event signature).
 */
function extractDeployedAddress(receipt: { logs: Array<{ topics: string[]; data: string; address: string }> }): Address | null {
  for (const log of receipt.logs) {
    // CREATE2 factories typically have the deployed address in topics[1] or topics[2]
    for (let i = 1; i < log.topics.length; i++) {
      const topic = log.topics[i];
      if (topic && topic.length === 66) { // 0x + 64 hex chars
        const addr = getAddress("0x" + topic.slice(26)); // last 20 bytes
        // Verify it's not a known factory or zero address
        if (addr !== ZERO_ADDRESS && addr !== log.address) {
          return addr;
        }
      }
    }
  }
  return null;
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

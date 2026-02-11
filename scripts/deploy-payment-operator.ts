/**
 * Deploy PaymentOperator for Execution Market on Base Mainnet
 *
 * This script deploys a PaymentOperator via the x402r factory contracts.
 * The operator is configured so ONLY the Facilitator can call release/refund.
 *
 * Usage:
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts
 *   PRIVATE_KEY=0x... npx tsx deploy-payment-operator.ts --dry-run
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

  // Protocol singletons
  authCaptureEscrow: "0xb9488351E48b23D798f24e8174514F28B741Eb4f" as Address,
  protocolFeeConfig: "0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6" as Address,
  usdcTvlLimit: "0x67B63Af4bcdCD3E4263d9995aB04563fbC229944" as Address,
  tokenCollector: "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8" as Address,

  // Condition singletons
  payerCondition: "0x7254b68D1AaAbd118C8A8b15756b4654c10a16d2" as Address,
  receiverCondition: "0x6926c05193c714ED4bA3867Ee93d6816Fdc14128" as Address,
  alwaysTrueCondition: "0xBAF68176FF94CAdD403EF7FbB776bbca548AC09D" as Address,

  // EM-specific
  emTreasury: "YOUR_TREASURY_WALLET" as Address,
};

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

// ============================================================
// Main
// ============================================================

async function main() {
  const isDryRun = process.argv.includes("--dry-run");

  // Get private key
  const privateKey = (process.env.PRIVATE_KEY || process.env.WALLET_PRIVATE_KEY) as Hex | undefined;
  if (!privateKey) {
    console.error("ERROR: Set PRIVATE_KEY or WALLET_PRIVATE_KEY environment variable");
    process.exit(1);
  }

  const account = privateKeyToAccount(privateKey);
  const rpcUrl = process.env.RPC_URL || "https://mainnet.base.org";

  console.log("=".repeat(60));
  console.log("Deploy PaymentOperator for Execution Market");
  console.log("=".repeat(60));
  console.log(`Network:      Base Mainnet (chain ${base.id})`);
  console.log(`RPC:          ${rpcUrl}`);
  console.log(`Deployer:     ${account.address}`);
  console.log(`Facilitator:  ${FACILITATOR_ADDRESS}`);
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

  // ============================================================
  // Step 1: Deploy StaticAddressCondition for Facilitator
  // ============================================================
  console.log("\n--- Step 1: StaticAddressCondition(Facilitator) ---");

  // Check if already deployed
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

      // Read back the deployed address
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

  // EM operator config:
  // - feeRecipient: EM treasury (receives operator fees if any)
  // - feeCalculator: address(0) (no operator fee — we charge 8% ourselves)
  // - authorizeCondition: UsdcTvlLimit (protocol safety)
  // - authorizeRecorder: address(0) (no escrow period tracking)
  // - chargeCondition/Recorder: address(0) (not used by EM)
  // - releaseCondition: StaticAddressCondition(Facilitator) — ONLY facilitator can release
  // - releaseRecorder: address(0)
  // - refundInEscrowCondition: StaticAddressCondition(Facilitator) — ONLY facilitator can refund
  // - refundInEscrowRecorder: address(0)
  // - refundPostEscrowCondition: address(0) (not used initially)
  // - refundPostEscrowRecorder: address(0)

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

  console.log("Operator config:");
  for (const [key, val] of Object.entries(operatorConfig)) {
    const label =
      val === ZERO_ADDRESS
        ? "(permissive)"
        : val === facilitatorCondition
          ? "(Facilitator-only)"
          : val === ADDRESSES.usdcTvlLimit
            ? "(UsdcTvlLimit)"
            : val === ADDRESSES.emTreasury
              ? "(EM Treasury)"
              : "";
    console.log(`  ${key.padEnd(30)} ${val} ${label}`);
  }

  // Check if already deployed
  let operatorAddress: Address;
  const configTuple = [
    operatorConfig.feeRecipient,
    operatorConfig.feeCalculator,
    operatorConfig.authorizeCondition,
    operatorConfig.authorizeRecorder,
    operatorConfig.chargeCondition,
    operatorConfig.chargeRecorder,
    operatorConfig.releaseCondition,
    operatorConfig.releaseRecorder,
    operatorConfig.refundInEscrowCondition,
    operatorConfig.refundInEscrowRecorder,
    operatorConfig.refundPostEscrowCondition,
    operatorConfig.refundPostEscrowRecorder,
  ] as const;

  try {
    const existing = await publicClient.readContract({
      address: ADDRESSES.paymentOperatorFactory,
      abi: PaymentOperatorFactoryABI,
      functionName: "getOperator",
      args: [configTuple],
    });

    if (existing && existing !== ZERO_ADDRESS) {
      operatorAddress = existing;
      console.log(`\nAlready deployed at: ${operatorAddress}`);
    } else {
      throw new Error("Not deployed");
    }
  } catch {
    if (isDryRun) {
      console.log("\nDRY RUN: Would deploy PaymentOperator");
      operatorAddress = "0x_DRY_RUN_OPERATOR" as Address;
    } else {
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

      // Read back
      operatorAddress = await publicClient.readContract({
        address: ADDRESSES.paymentOperatorFactory,
        abi: PaymentOperatorFactoryABI,
        functionName: "getOperator",
        args: [configTuple],
      });
      console.log(`Deployed at: ${operatorAddress}`);
    }
  }

  // ============================================================
  // Summary
  // ============================================================
  console.log("\n" + "=".repeat(60));
  console.log("DEPLOYMENT SUMMARY");
  console.log("=".repeat(60));
  console.log(`Network:                   Base Mainnet (${base.id})`);
  console.log(`StaticAddressCondition:    ${facilitatorCondition}`);
  console.log(`PaymentOperator:           ${operatorAddress}`);
  console.log(`AuthCaptureEscrow:         ${ADDRESSES.authCaptureEscrow}`);
  console.log(`TokenCollector:            ${ADDRESSES.tokenCollector}`);
  console.log(`Facilitator (authorized):  ${FACILITATOR_ADDRESS}`);
  console.log(`EM Treasury (feeRecipient):${ADDRESSES.emTreasury}`);
  console.log("");
  console.log("Next steps:");
  console.log("1. Register operatorAddress in facilitator addresses.rs");
  console.log("2. Rebuild + redeploy facilitator");
  console.log("3. Test escrow lifecycle: authorize → release / refundInEscrow");
  console.log("");
  console.log("Facilitator addresses.rs entry:");
  console.log(`  payment_operator: Some("${operatorAddress}"),`);
  console.log(`  token_collector: Some("${ADDRESSES.tokenCollector}"),`);
}

main().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});

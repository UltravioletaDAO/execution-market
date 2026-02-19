/**
 * Deploy PaymentOperator for Execution Market (Multi-chain)
 *
 * This script deploys a PaymentOperator via the x402r factory contracts on any supported network.
 *
 * Supported networks: base, ethereum, polygon, arbitrum, celo, monad, avalanche, optimism
 *
 * Fase 2 (default): Facilitator-only release/refund, no protocol fees. (Base only — legacy)
 * Fase 3 (--fase3):  OR(Payer, Facilitator) + StaticFeeCalculator. (Base only — legacy)
 * Fase 3 Clean (--fase3-clean): OR(Payer, Facilitator), feeCalculator=address(0). (Base only — legacy)
 * Fase 4 (--fase4):  SECURE — OR(Payer|Facilitator) release, Facilitator-ONLY refund. (Base only — legacy)
 * Fase 5 (--fase5):  TRUSTLESS FEE SPLIT — OR(Payer|Facilitator) release, Facilitator-ONLY refund,
 *                    StaticFeeCalculator(1300 BPS = 13%). At release, escrow auto-splits: worker gets 87%,
 *                    operator holds 13%. distributeFees() flushes operator balance to EM treasury.
 *                    Auto-deploys missing conditions (FacilitatorCondition, OrCondition) on new chains.
 *                    MULTI-CHAIN: works on all 8 supported networks.
 *
 * Usage:
 *   npx tsx deploy-payment-operator.ts --fase5 --network base --dry-run
 *   npx tsx deploy-payment-operator.ts --fase5 --network ethereum
 *   npx tsx deploy-payment-operator.ts --fase5 --network polygon --dry-run
 *   npx tsx deploy-payment-operator.ts --fase5 --network arbitrum
 *   npx tsx deploy-payment-operator.ts --fase2                          # Base only (legacy)
 *
 * Environment:
 *   PRIVATE_KEY  - Wallet with native tokens on target chain for gas (~$2-5)
 *   RPC_URL      - (optional) Override RPC URL for target chain
 */

import { createPublicClient, createWalletClient, http, parseAbi, getAddress, defineChain, type Hex, type Address, type Chain } from "viem";
import { base, mainnet, polygon, arbitrum, celo, avalanche, optimism } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env.local" });

// ============================================================
// Configuration
// ============================================================

const FACILITATOR_ADDRESS: Address = "0x103040545AC5031A11E8C03dd11324C7333a13C7";
const ZERO_ADDRESS: Address = "0x0000000000000000000000000000000000000000";

// EM-specific constant (same on all chains)
const EM_TREASURY: Address = "0xaE07cEB6b395BC685a776a0b4c489E8d9cE9A6ad";

// Custom Monad chain definition (not in viem yet)
const monad: Chain = defineChain({
  id: 143,
  name: "Monad",
  nativeCurrency: { name: "MON", symbol: "MON", decimals: 18 },
  rpcUrls: { default: { http: ["https://rpc.monad.xyz"] } },
});

// Per-chain x402r infrastructure addresses (from @x402r/sdk source of truth)
// Sub-factory addresses are DIFFERENT per chain (not CREATE2-identical).
// Pattern: Arb/Celo/Monad/Avax/Op share identical addresses. Ethereum and Polygon each unique.
type ChainConfig = {
  chain: Chain;
  rpcUrl: string;
  escrow: Address;
  paymentOperatorFactory: Address;
  staticAddressConditionFactory: Address;
  orConditionFactory: Address;
  staticFeeCalculatorFactory: Address;
  protocolFeeConfig: Address;
  usdcTvlLimit: Address;
  tokenCollector: Address;
  payerCondition: Address;
  // Existing deployments on Base (may not exist on other chains)
  facilitatorCondition?: Address;
  orConditionPayerFacilitator?: Address;
};

const CHAIN_CONFIGS: Record<string, ChainConfig> = {
  base: {
    chain: base,
    rpcUrl: "https://mainnet.base.org",
    escrow: "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
    paymentOperatorFactory: "0x3D0837fF8Ea36F417261577b9BA568400A840260",
    staticAddressConditionFactory: "0x206D4DbB6E7b876e4B5EFAAD2a04e7d7813FB6ba",
    orConditionFactory: "0x1e52a74cE6b69F04a506eF815743E1052A1BD28F",
    staticFeeCalculatorFactory: "0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0",
    protocolFeeConfig: "0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6",
    usdcTvlLimit: "0x67B63Af4bcdCD3E4263d9995aB04563fbC229944",
    tokenCollector: "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8",
    payerCondition: "0x7254b68D1AaAbd118C8A8b15756b4654c10a16d2",
    // Existing Base deployments
    facilitatorCondition: "0x9d03c03c15563E72CF2186E9FDB859A00ea661fc",
    orConditionPayerFacilitator: "0xb365717C35004089996F72939b0C5b32Fa2ef8aE",
  },
  ethereum: {
    chain: mainnet,
    rpcUrl: "https://eth.llamarpc.com",
    escrow: "0xc1256Bb30bd0cdDa07D8C8Cf67a59105f2EA1b98",
    paymentOperatorFactory: "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8",
    staticAddressConditionFactory: "0x6a7E26c3A78a7B1eFF9Dd28d51B2a15df3208B84",
    orConditionFactory: "0x32471d31910A009273a812dE0894D9F0AdeF4834",
    staticFeeCalculatorFactory: "0xc5a96DaBd3F0E485CEEA7Bf912fC5834A6DE2267",
    protocolFeeConfig: "0xb33D6502EdBbC47201cd1E53C49d703EC0a660b8",
    usdcTvlLimit: "0x785cC83DEa3d46D5509f3bf7496EAb26D42EE610",
    tokenCollector: "0xE78648e7af7B1BaDE717FF6E410B922F92adE80f",
    payerCondition: "0xB68C023365EB08021E12f7f7f11a03282443863A",
  },
  polygon: {
    chain: polygon,
    rpcUrl: "https://polygon-bor-rpc.publicnode.com",
    escrow: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    paymentOperatorFactory: "0xb33D6502EdBbC47201cd1E53C49d703EC0a660b8",
    staticAddressConditionFactory: "0xc5a96DaBd3F0E485CEEA7Bf912fC5834A6DE2267",
    orConditionFactory: "0x19a798c7F66E6401f6004b732dA604196952e843",
    staticFeeCalculatorFactory: "0xe968AA7530b9C3336FED14FD5D5D4dD3Cf82655D",
    protocolFeeConfig: "0xE78648e7af7B1BaDE717FF6E410B922F92adE80f",
    usdcTvlLimit: "0xdc0D800007ceAcfF1299b926CE22b4D4EDce6ce7",
    tokenCollector: "0xc1256Bb30bd0cdDa07D8C8Cf67a59105f2EA1b98",
    payerCondition: "0x2714EA3e839Ac50F52B2e2a5788F614cACeE5316",
  },
  arbitrum: {
    chain: arbitrum,
    rpcUrl: "https://arb1.arbitrum.io/rpc",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
    paymentOperatorFactory: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    staticAddressConditionFactory: "0x0DdF51E62DDD41B5f67BEaF2DCE9F2E99E2C5aF5",
    orConditionFactory: "0xe968AA7530b9C3336FED14FD5D5D4dD3Cf82655D",
    staticFeeCalculatorFactory: "0x89257cA1114139C3332bb73655BC2e4C924aC678",
    protocolFeeConfig: "0xD979dBfBdA5f4b16AAF60Eaab32A44f352076838",
    usdcTvlLimit: "0x9B16ff5bcF5C0B2c31Cd17032a306E91CA67F546",
    tokenCollector: "0x230fd3A171750FA45db2976121376b7F47Cba308",
    payerCondition: "0xed02d3E5167BCc9582D851885A89b050AB816a56",
  },
  celo: {
    chain: celo,
    rpcUrl: "https://forno.celo.org",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
    paymentOperatorFactory: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    staticAddressConditionFactory: "0x0DdF51E62DDD41B5f67BEaF2DCE9F2E99E2C5aF5",
    orConditionFactory: "0xe968AA7530b9C3336FED14FD5D5D4dD3Cf82655D",
    staticFeeCalculatorFactory: "0x89257cA1114139C3332bb73655BC2e4C924aC678",
    protocolFeeConfig: "0xD979dBfBdA5f4b16AAF60Eaab32A44f352076838",
    usdcTvlLimit: "0x9B16ff5bcF5C0B2c31Cd17032a306E91CA67F546",
    tokenCollector: "0x230fd3A171750FA45db2976121376b7F47Cba308",
    payerCondition: "0xed02d3E5167BCc9582D851885A89b050AB816a56",
  },
  monad: {
    chain: monad,
    rpcUrl: "https://rpc.monad.xyz",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
    paymentOperatorFactory: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    staticAddressConditionFactory: "0x0DdF51E62DDD41B5f67BEaF2DCE9F2E99E2C5aF5",
    orConditionFactory: "0xe968AA7530b9C3336FED14FD5D5D4dD3Cf82655D",
    staticFeeCalculatorFactory: "0x89257cA1114139C3332bb73655BC2e4C924aC678",
    protocolFeeConfig: "0xD979dBfBdA5f4b16AAF60Eaab32A44f352076838",
    usdcTvlLimit: "0xA50F51254E8B08899EdB76Bd24b4DC6A61ba7dE7",
    tokenCollector: "0x230fd3A171750FA45db2976121376b7F47Cba308",
    payerCondition: "0xed02d3E5167BCc9582D851885A89b050AB816a56",
  },
  avalanche: {
    chain: avalanche,
    rpcUrl: "https://api.avax.network/ext/bc/C/rpc",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
    paymentOperatorFactory: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    staticAddressConditionFactory: "0x0DdF51E62DDD41B5f67BEaF2DCE9F2E99E2C5aF5",
    orConditionFactory: "0xe968AA7530b9C3336FED14FD5D5D4dD3Cf82655D",
    staticFeeCalculatorFactory: "0x89257cA1114139C3332bb73655BC2e4C924aC678",
    protocolFeeConfig: "0xD979dBfBdA5f4b16AAF60Eaab32A44f352076838",
    usdcTvlLimit: "0x9B16ff5bcF5C0B2c31Cd17032a306E91CA67F546",
    tokenCollector: "0x230fd3A171750FA45db2976121376b7F47Cba308",
    payerCondition: "0xed02d3E5167BCc9582D851885A89b050AB816a56",
  },
  optimism: {
    chain: optimism,
    rpcUrl: "https://mainnet.optimism.io",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
    paymentOperatorFactory: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
    staticAddressConditionFactory: "0x0DdF51E62DDD41B5f67BEaF2DCE9F2E99E2C5aF5",
    orConditionFactory: "0xe968AA7530b9C3336FED14FD5D5D4dD3Cf82655D",
    staticFeeCalculatorFactory: "0x89257cA1114139C3332bb73655BC2e4C924aC678",
    protocolFeeConfig: "0xD979dBfBdA5f4b16AAF60Eaab32A44f352076838",
    usdcTvlLimit: "0x9B16ff5bcF5C0B2c31Cd17032a306E91CA67F546",
    tokenCollector: "0x230fd3A171750FA45db2976121376b7F47Cba308",
    payerCondition: "0xed02d3E5167BCc9582D851885A89b050AB816a56",
  },
};

// Legacy: Base-only ADDRESSES alias for backward compat with Fase 2/3/4 functions
const ADDRESSES = {
  ...CHAIN_CONFIGS.base,
  escrowPeriodFactory: "0x12EDefd4549c53497689067f165c0f101796Eb6D" as Address,
  authCaptureEscrow: CHAIN_CONFIGS.base.escrow,
  receiverCondition: "0x6926c05193c714ED4bA3867Ee93d6816Fdc14128" as Address,
  alwaysTrueCondition: "0xBAF68176FF94CAdD403EF7FbB776bbca548AC09D" as Address,
  emTreasury: EM_TREASURY,
};

// Fase 3: 1% operator fee (100 basis points)
// FEE_RECIPIENT is set on the PaymentOperator (already = EM treasury).
// StaticFeeCalculator only takes feeBps, NOT a recipient address.
// Ali confirmed: "The configurable fee options are for you not us."
// BackTrack collects their own fees via ProtocolFeeConfig (currently 0% on Base).
const OPERATOR_FEE_BPS = 100;

// Fase 5: 13% operator fee (1300 basis points) — trustless fee split (standard DeFi convention)
// Fee is 13% of the TOTAL locked amount. Lock formula: ceil(bounty * 10000 / 8700).
// Agent pays bounty / 0.87 (e.g. $0.114943 for $0.10 bounty):
//   - 13% of $0.114943 = $0.014942 (fee to operator → treasury via distributeFees)
//   - 87% of $0.114943 = $0.100001 (net to worker, >= bounty guaranteed)
// Rounding: <=1 unit (0.000001 USDC) variance in worker's favor. Standard for on-chain fee math.
const FASE5_FEE_BPS = 1300;

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
  "function FEE_RECIPIENT() external view returns (address)",
  "function RELEASE_CONDITION() external view returns (address)",
  "function REFUND_IN_ESCROW_CONDITION() external view returns (address)",
]);

// StaticFeeCalculator read-only ABI
const StaticFeeCalculatorReadABI = parseAbi([
  "function FEE_BPS() external view returns (uint256)",
]);

// ============================================================
// Main
// ============================================================

async function main() {
  const isDryRun = process.argv.includes("--dry-run");
  const isFase3 = process.argv.includes("--fase3");
  const isFase3Clean = process.argv.includes("--fase3-clean");
  const isFase4 = process.argv.includes("--fase4");
  const isFase5 = process.argv.includes("--fase5");

  // Parse --network flag (default: base)
  const networkIdx = process.argv.indexOf("--network");
  const networkName = networkIdx >= 0 && process.argv[networkIdx + 1]
    ? process.argv[networkIdx + 1]
    : "base";

  const chainConfig = CHAIN_CONFIGS[networkName];
  if (!chainConfig) {
    console.error(`ERROR: Unknown network '${networkName}'. Supported: ${Object.keys(CHAIN_CONFIGS).join(", ")}`);
    process.exit(1);
  }

  // Legacy modes (Fase 2/3/4) only work on Base
  if (!isFase5 && networkName !== "base") {
    console.error(`ERROR: Fase 2/3/4 modes only work on Base. Use --fase5 for multi-chain deployment.`);
    process.exit(1);
  }

  const modeLabel = isFase5
    ? "Fase 5 (Trustless Fee Split)"
    : isFase4
      ? "Fase 4 (Secure)"
      : isFase3Clean
        ? "Fase 3 Clean"
        : isFase3
          ? "Fase 3"
          : "Fase 2";

  const modeDescription = isFase5
    ? `Fase 5 — OR(Payer, Facilitator) release, Facilitator-ONLY refund, StaticFeeCalculator(${FASE5_FEE_BPS}bps)`
    : isFase4
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
  const rpcUrl = process.env.RPC_URL || process.env.X402_RPC_URL || chainConfig.rpcUrl;

  console.log("=".repeat(60));
  console.log(`Deploy PaymentOperator for Execution Market (${modeLabel})`);
  console.log("=".repeat(60));
  console.log(`Network:      ${networkName} (chain ${chainConfig.chain.id})`);
  console.log(`RPC:          ${rpcUrl}`);
  console.log(`Deployer:     ${account.address}`);
  console.log(`Facilitator:  ${FACILITATOR_ADDRESS}`);
  console.log(`Mode:         ${modeDescription}`);
  console.log(`Dry run:      ${isDryRun}`);
  console.log("");

  const publicClient = createPublicClient({
    chain: chainConfig.chain,
    transport: http(rpcUrl),
  });

  const walletClient = createWalletClient({
    account,
    chain: chainConfig.chain,
    transport: http(rpcUrl),
  });

  // Check deployer native balance
  const balance = await publicClient.getBalance({ address: account.address });
  const nativeBalance = Number(balance) / 1e18;
  console.log(`Deployer balance: ${nativeBalance.toFixed(6)} ${chainConfig.chain.nativeCurrency.symbol}`);
  if (nativeBalance < 0.001) {
    console.error(`ERROR: Insufficient ${chainConfig.chain.nativeCurrency.symbol} for gas. Need at least 0.001.`);
    process.exit(1);
  }

  if (isFase5) {
    await deployFase5(publicClient, walletClient, isDryRun, chainConfig, networkName);
  } else if (isFase4) {
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
// Fase 5: Trustless Fee Split — StaticFeeCalculator(1150 BPS) + Secure refund
// At release(), escrow auto-splits: worker gets 88.5%, operator holds 11.5%.
// distributeFees(token) flushes operator balance to EM treasury.
// ============================================================

async function deployFase5(
  publicClient: ReturnType<typeof createPublicClient>,
  walletClient: ReturnType<typeof createWalletClient>,
  isDryRun: boolean,
  chainConfig: ChainConfig = CHAIN_CONFIGS.base,
  networkName: string = "base",
) {
  // ============================================================
  // Pre-check: Verify all required factories exist on-chain
  // (Prevents wasted TXs if BackTrack hasn't deployed sub-factories yet)
  // ============================================================
  console.log("\n--- Pre-check: Verifying factory contracts on-chain ---");
  const factoriesToCheck = [
    { name: "StaticFeeCalculatorFactory", addr: chainConfig.staticFeeCalculatorFactory },
    { name: "StaticAddressConditionFactory", addr: chainConfig.staticAddressConditionFactory },
    { name: "OrConditionFactory", addr: chainConfig.orConditionFactory },
    { name: "PaymentOperatorFactory", addr: chainConfig.paymentOperatorFactory },
  ];
  for (const f of factoriesToCheck) {
    const code = await publicClient.getCode({ address: f.addr });
    if (!code || code === "0x" || code.length <= 2) {
      console.error(`FATAL: ${f.name} at ${f.addr} has no bytecode on ${networkName}.`);
      console.error(`  BackTrack has not deployed this factory on ${networkName} yet.`);
      console.error(`  Ask Ali to deploy sub-factories before deploying EM operators.`);
      process.exit(1);
    }
    console.log(`  ${f.name}: OK (${(code.length - 2) / 2} bytes)`);
  }
  console.log("  All factories verified.\n");

  // ============================================================
  // Step 1: Deploy or reuse StaticFeeCalculator
  // ============================================================
  console.log(`\n--- Step 1: StaticFeeCalculator(${FASE5_FEE_BPS}bps = ${FASE5_FEE_BPS / 100}%) ---`);
  console.log(`  Fee goes to FEE_RECIPIENT on operator (EM treasury ${EM_TREASURY})`);

  let feeCalculator: Address;
  try {
    const existing = await publicClient.readContract({
      address: chainConfig.staticFeeCalculatorFactory,
      abi: StaticFeeCalculatorFactoryABI,
      functionName: "getDeployed",
      args: [BigInt(FASE5_FEE_BPS)],
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
      console.log(`  feeBps: ${FASE5_FEE_BPS} (${FASE5_FEE_BPS / 100}%)`);
      feeCalculator = "0x_DRY_RUN_FEE_CALC" as Address;
    } else {
      console.log("Deploying StaticFeeCalculator...");
      console.log(`  feeBps: ${FASE5_FEE_BPS} (${FASE5_FEE_BPS / 100}%)`);
      const hash = await walletClient.writeContract({
        address: chainConfig.staticFeeCalculatorFactory,
        abi: StaticFeeCalculatorFactoryABI,
        functionName: "deploy",
        args: [BigInt(FASE5_FEE_BPS)],
      });
      console.log(`TX: ${hash}`);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

      feeCalculator = await publicClient.readContract({
        address: chainConfig.staticFeeCalculatorFactory,
        abi: StaticFeeCalculatorFactoryABI,
        functionName: "getDeployed",
        args: [BigInt(FASE5_FEE_BPS)],
      });

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
  // Step 2: Deploy or reuse FacilitatorCondition + OrCondition
  // On Base these already exist; on new chains we deploy them.
  // ============================================================
  console.log("\n--- Step 2: Conditions (FacilitatorCondition + OrCondition) ---");

  let facilitatorOnly: Address;
  let orCondition: Address;

  if (chainConfig.facilitatorCondition && chainConfig.orConditionPayerFacilitator) {
    // Reuse existing deployments (Base)
    facilitatorOnly = chainConfig.facilitatorCondition;
    orCondition = chainConfig.orConditionPayerFacilitator;
    console.log(`  Using existing FacilitatorCondition: ${facilitatorOnly}`);
    console.log(`  Using existing OrCondition:          ${orCondition}`);

    if (!isDryRun) {
      const orBytecode = await publicClient.getCode({ address: orCondition });
      if (!orBytecode || orBytecode === "0x") {
        console.error(`FATAL: OrCondition at ${orCondition} has no bytecode`);
        process.exit(1);
      }
      console.log(`  OrCondition verified: contract exists (${orBytecode.length / 2 - 1} bytes)`);

      const facBytecode = await publicClient.getCode({ address: facilitatorOnly });
      if (!facBytecode || facBytecode === "0x") {
        console.error(`FATAL: StaticAddressCondition at ${facilitatorOnly} has no bytecode`);
        process.exit(1);
      }
      console.log(`  FacilitatorCondition verified: contract exists (${facBytecode.length / 2 - 1} bytes)`);
    }
  } else {
    // New chain — deploy FacilitatorCondition then OrCondition
    console.log(`  New chain (${networkName}) — deploying conditions...`);

    // Step 2a: StaticAddressCondition(Facilitator)
    console.log(`\n  --- Step 2a: StaticAddressCondition(Facilitator) ---`);
    try {
      const existing = await publicClient.readContract({
        address: chainConfig.staticAddressConditionFactory,
        abi: StaticAddressConditionFactoryABI,
        functionName: "getDeployed",
        args: [FACILITATOR_ADDRESS],
      });
      if (existing && existing !== ZERO_ADDRESS) {
        facilitatorOnly = existing;
        console.log(`  Already deployed at: ${facilitatorOnly}`);
      } else {
        throw new Error("Not deployed");
      }
    } catch {
      if (isDryRun) {
        console.log("  DRY RUN: Would deploy StaticAddressCondition(Facilitator)");
        facilitatorOnly = "0x_DRY_RUN_FAC_COND" as Address;
      } else {
        console.log("  Deploying StaticAddressCondition for Facilitator...");
        const hash = await walletClient.writeContract({
          address: chainConfig.staticAddressConditionFactory,
          abi: StaticAddressConditionFactoryABI,
          functionName: "deploy",
          args: [FACILITATOR_ADDRESS],
        });
        console.log(`  TX: ${hash}`);
        const receipt = await publicClient.waitForTransactionReceipt({ hash });
        console.log(`  Gas used: ${receipt.gasUsed} (${receipt.status})`);

        facilitatorOnly = await publicClient.readContract({
          address: chainConfig.staticAddressConditionFactory,
          abi: StaticAddressConditionFactoryABI,
          functionName: "getDeployed",
          args: [FACILITATOR_ADDRESS],
        });

        if (!facilitatorOnly || facilitatorOnly === ZERO_ADDRESS) {
          const deployed = extractDeployedAddress(receipt);
          if (deployed) {
            facilitatorOnly = deployed;
          } else {
            console.error("FATAL: Could not determine FacilitatorCondition address");
            process.exit(1);
          }
        }
        console.log(`  Deployed at: ${facilitatorOnly}`);
      }
    }

    // Step 2b: OrCondition(PayerCondition, FacilitatorCondition)
    console.log(`\n  --- Step 2b: OrCondition(Payer, Facilitator) ---`);
    const orConditions: Address[] = [chainConfig.payerCondition, facilitatorOnly];
    try {
      const existing = await publicClient.readContract({
        address: chainConfig.orConditionFactory,
        abi: OrConditionFactoryABI,
        functionName: "getDeployed",
        args: [orConditions],
      });
      if (existing && existing !== ZERO_ADDRESS) {
        orCondition = existing;
        console.log(`  Already deployed at: ${orCondition}`);
      } else {
        throw new Error("Not deployed");
      }
    } catch {
      if (isDryRun) {
        console.log("  DRY RUN: Would deploy OrCondition(Payer, Facilitator)");
        console.log(`    conditions[0]: ${chainConfig.payerCondition} (PayerCondition)`);
        console.log(`    conditions[1]: ${facilitatorOnly} (FacilitatorCondition)`);
        orCondition = "0x_DRY_RUN_OR_COND" as Address;
      } else {
        console.log("  Deploying OrCondition...");
        console.log(`    conditions[0]: ${chainConfig.payerCondition} (PayerCondition)`);
        console.log(`    conditions[1]: ${facilitatorOnly} (FacilitatorCondition)`);
        const hash = await walletClient.writeContract({
          address: chainConfig.orConditionFactory,
          abi: OrConditionFactoryABI,
          functionName: "deploy",
          args: [orConditions],
        });
        console.log(`  TX: ${hash}`);
        const receipt = await publicClient.waitForTransactionReceipt({ hash });
        console.log(`  Gas used: ${receipt.gasUsed} (${receipt.status})`);

        orCondition = await publicClient.readContract({
          address: chainConfig.orConditionFactory,
          abi: OrConditionFactoryABI,
          functionName: "getDeployed",
          args: [orConditions],
        });

        if (!orCondition || orCondition === ZERO_ADDRESS) {
          const deployed = extractDeployedAddress(receipt);
          if (deployed) {
            orCondition = deployed;
          } else {
            console.error("FATAL: Could not determine OrCondition address");
            process.exit(1);
          }
        }
        console.log(`  Deployed at: ${orCondition}`);
      }
    }
  }

  // ============================================================
  // Step 3: Deploy PaymentOperator with Fase 5 config
  // ============================================================
  console.log("\n--- Step 3: PaymentOperator (Fase 5 — Trustless Fee Split) ---");

  if (feeCalculator === ZERO_ADDRESS) {
    console.error("FATAL: StaticFeeCalculator address is zero — cannot deploy Fase 5 operator");
    process.exit(1);
  }

  const operatorConfig = {
    feeRecipient: EM_TREASURY,
    feeCalculator: feeCalculator,
    authorizeCondition: chainConfig.usdcTvlLimit,
    authorizeRecorder: ZERO_ADDRESS,
    chargeCondition: ZERO_ADDRESS,
    chargeRecorder: ZERO_ADDRESS,
    releaseCondition: orCondition,
    releaseRecorder: ZERO_ADDRESS,
    refundInEscrowCondition: facilitatorOnly,
    refundInEscrowRecorder: ZERO_ADDRESS,
    refundPostEscrowCondition: ZERO_ADDRESS,
    refundPostEscrowRecorder: ZERO_ADDRESS,
  };

  logOperatorConfig(operatorConfig, {
    [feeCalculator]: `(StaticFeeCalculator ${FASE5_FEE_BPS}bps)`,
    [orCondition]: "(OR: Payer | Facilitator)",
    [facilitatorOnly]: "(Facilitator-ONLY — SECURE)",
    [chainConfig.usdcTvlLimit]: "(UsdcTvlLimit)",
    [EM_TREASURY]: "(EM Treasury)",
  });

  const operatorAddress = await deployOrGetOperator(publicClient, walletClient, operatorConfig, isDryRun, chainConfig);

  // ============================================================
  // Step 4: On-chain verification
  // ============================================================
  if (!isDryRun && operatorAddress !== ("0x_DRY_RUN_OPERATOR" as Address)) {
    console.log("\n--- Step 4: On-chain verification ---");

    const feeCalc = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "FEE_CALCULATOR",
    });
    const feeRecipient = await publicClient.readContract({
      address: operatorAddress,
      abi: PaymentOperatorReadABI,
      functionName: "FEE_RECIPIENT",
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

    const feeBps = await publicClient.readContract({
      address: feeCalc,
      abi: StaticFeeCalculatorReadABI,
      functionName: "FEE_BPS",
    });

    const checks = [
      { name: `FEE_CALCULATOR() != address(0)`, actual: feeCalc, expected: feeCalculator },
      { name: `FEE_RECIPIENT() == EM Treasury`, actual: feeRecipient, expected: EM_TREASURY },
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

    const bpsMatch = Number(feeBps) === FASE5_FEE_BPS;
    console.log(`  ${bpsMatch ? "PASS" : "FAIL"}: FEE_BPS() == ${FASE5_FEE_BPS}`);
    console.log(`         got:      ${feeBps}`);
    console.log(`         expected: ${FASE5_FEE_BPS}`);
    if (!bpsMatch) allPassed = false;

    if (!allPassed) {
      console.error("\nFATAL: On-chain verification failed — operator config does not match expected values");
      process.exit(1);
    }
    console.log("\n  All on-chain checks passed.");

    if (refundCond.toLowerCase() === orCondition.toLowerCase()) {
      console.error("\nSECURITY ALERT: REFUND_IN_ESCROW_CONDITION is OrCondition — payer can still refund directly!");
      process.exit(1);
    }
    console.log("  SECURITY: Refund is Facilitator-only (payer CANNOT refund directly).");
  }

  // Summary
  printSummary({
    mode: `Fase 5 (Trustless Fee Split) — StaticFeeCalculator(${FASE5_FEE_BPS}bps), Facilitator-ONLY refund`,
    feeCalculator,
    orCondition,
    operatorAddress,
    networkName,
    chainId: chainConfig.chain.id,
    escrow: chainConfig.escrow,
    tokenCollector: chainConfig.tokenCollector,
  });

  console.log("");
  console.log("FEE SPLIT DETAILS:");
  console.log(`  - Fee calculator: StaticFeeCalculator(${FASE5_FEE_BPS} BPS = ${FASE5_FEE_BPS / 100}%)`);
  console.log(`  - At release: worker gets ${100 - FASE5_FEE_BPS / 100}%, operator holds ${FASE5_FEE_BPS / 100}%`);
  console.log(`  - distributeFees(USDC) flushes operator balance to EM treasury`);
  console.log("  - Release: OR(Payer, Facilitator)");
  console.log(`  - Refund:  Facilitator-ONLY (${facilitatorOnly})`);
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
  chainConfig: ChainConfig = CHAIN_CONFIGS.base,
): Promise<Address> {
  const factoryAddress = chainConfig.paymentOperatorFactory;
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
      address: factoryAddress,
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
      address: factoryAddress,
      abi: PaymentOperatorFactoryABI,
      functionName: "deployOperator",
      args: [configTuple],
    });
    console.log(`TX: ${hash}`);
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    console.log(`Gas used: ${receipt.gasUsed} (${receipt.status})`);

    // Wait for RPC to index, then look up via factory
    let deployed = await publicClient.readContract({
      address: factoryAddress,
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
  networkName?: string;
  chainId?: number;
  escrow?: Address;
  tokenCollector?: Address;
}) {
  const networkLabel = params.networkName || "base";
  const chainId = params.chainId || base.id;
  const escrow = params.escrow || CHAIN_CONFIGS.base.escrow;
  const tokenCollector = params.tokenCollector || CHAIN_CONFIGS.base.tokenCollector;

  console.log("\n" + "=".repeat(60));
  console.log("DEPLOYMENT SUMMARY");
  console.log("=".repeat(60));
  console.log(`Mode:                      ${params.mode}`);
  console.log(`Network:                   ${networkLabel} (chain ${chainId})`);
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
  console.log(`AuthCaptureEscrow:         ${escrow}`);
  console.log(`TokenCollector:            ${tokenCollector}`);
  console.log(`Facilitator (authorized):  ${FACILITATOR_ADDRESS}`);
  console.log(`EM Treasury (feeRecipient):${EM_TREASURY}`);
  console.log("");
  console.log("Next steps:");
  console.log("1. Register operatorAddress in facilitator addresses.rs");
  console.log("2. Rebuild + redeploy facilitator");
  console.log("3. Test escrow lifecycle: authorize -> release / refundInEscrow");
  console.log(`4. Update NETWORK_CONFIG['${networkLabel}']['operator'] in sdk_client.py`);
  console.log("");
  console.log("Facilitator addresses.rs entry:");
  console.log(`  payment_operator: Some("${params.operatorAddress}"),`);
  console.log(`  token_collector: Some("${tokenCollector}"),`);
}

main().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});

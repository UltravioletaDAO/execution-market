/**
 * verify-operator-config.ts — READ-ONLY on-chain verification of EM PaymentOperators.
 *
 * For each of the 9 EVM chains with deployed Fase 5 operators, this script:
 *   1. Checks bytecode exists at the operator address
 *   2. Reads FEE_CALCULATOR() → fee calculator contract
 *   3. Reads FEE_BPS() on the fee calculator → must equal 1300 (13%)
 *   4. Reads RELEASE_CONDITION() and REFUND_IN_ESCROW_CONDITION()
 *   5. Prints PASS / FAIL per chain
 *
 * No transactions, no signing, no private keys required.
 * Uses public RPCs (override via env vars for reliability).
 *
 * Usage: cd scripts && npx tsx verify-operator-config.ts
 *
 * Phase 2 Security Remediation — SC-005 + SC-013
 */

import { createPublicClient, http, defineChain, type Chain, type Address } from "viem";
import { base, mainnet, polygon, arbitrum, celo, avalanche, optimism } from "viem/chains";
import * as dotenv from "dotenv";

dotenv.config({ path: "../.env.local" });

// ============================================================
// Chain definitions for chains not in viem
// ============================================================

const monad: Chain = defineChain({
  id: 143,
  name: "Monad",
  nativeCurrency: { name: "MON", symbol: "MON", decimals: 18 },
  rpcUrls: { default: { http: ["https://rpc.monad.xyz"] } },
});

const skaleBase: Chain = defineChain({
  id: 1187947933,
  name: "SKALE Base",
  nativeCurrency: { name: "CREDIT", symbol: "CREDIT", decimals: 18 },
  rpcUrls: { default: { http: ["https://skale-base.skalenodes.com/v1/base"] } },
});

// ============================================================
// Operator config — canonical addresses from CLAUDE.md / sdk_client.py
// ============================================================

const EXPECTED_FEE_BPS = 1300n;

type OperatorConfig = {
  chain: Chain;
  rpcUrl: string;
  operator: Address;
  escrow: Address;
};

const OPERATORS: Record<string, OperatorConfig> = {
  base: {
    chain: base,
    rpcUrl: process.env.BASE_MAINNET_RPC_URL || "https://mainnet.base.org",
    operator: "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb",
    escrow: "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
  },
  ethereum: {
    chain: mainnet,
    rpcUrl: process.env.ETHEREUM_RPC_URL || "https://ethereum-rpc.publicnode.com",
    operator: "0x69B67962ffb7c5C7078ff348a87DF604dfA8001b",
    escrow: "0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0",
  },
  polygon: {
    chain: polygon,
    rpcUrl: process.env.POLYGON_RPC_URL || "https://polygon-bor-rpc.publicnode.com",
    operator: "0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e",
    escrow: "0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6",
  },
  arbitrum: {
    chain: arbitrum,
    rpcUrl: process.env.ARBITRUM_RPC_URL || "https://arb1.arbitrum.io/rpc",
    operator: "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
  },
  avalanche: {
    chain: avalanche,
    rpcUrl: process.env.AVALANCHE_RPC_URL || "https://api.avax.network/ext/bc/C/rpc",
    operator: "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
  },
  celo: {
    chain: celo,
    rpcUrl: process.env.CELO_RPC_URL || "https://forno.celo.org",
    operator: "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
  },
  monad: {
    chain: monad,
    rpcUrl: process.env.MONAD_RPC_URL || "https://rpc.monad.xyz",
    operator: "0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
  },
  optimism: {
    chain: optimism,
    rpcUrl: process.env.OPTIMISM_RPC_URL || "https://mainnet.optimism.io",
    operator: "0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e",
    escrow: "0x320a3c35F131E5D2Fb36af56345726B298936037",
  },
  skale: {
    chain: skaleBase,
    rpcUrl: process.env.SKALE_RPC_URL || "https://skale-base.skalenodes.com/v1/base",
    operator: "0x43E46d4587fCCc382285C52012227555ed78D183",
    escrow: "0xBC151792f80C0EB1973d56b0235e6bee2A60e245",
  },
};

// ============================================================
// ABI fragments — minimal read-only
// ============================================================

const OPERATOR_ABI = [
  { name: "FEE_CALCULATOR", type: "function", stateMutability: "view", inputs: [], outputs: [{ type: "address" }] },
  { name: "RELEASE_CONDITION", type: "function", stateMutability: "view", inputs: [], outputs: [{ type: "address" }] },
  { name: "REFUND_IN_ESCROW_CONDITION", type: "function", stateMutability: "view", inputs: [], outputs: [{ type: "address" }] },
] as const;

const FEE_CALC_ABI = [
  { name: "FEE_BPS", type: "function", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
] as const;

// ============================================================
// Known address cross-references for mismatch detection
// ============================================================

// X402R_REFERENCE.md lists the Ethereum escrow as 0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0.
// sdk_client.py also lists it as 0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0.
// Base staticFeeCalculatorFactory is ALSO 0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0.
// This is a known address collision flagged in the audit (SC-013).
const KNOWN_COLLISIONS: Record<string, string> = {
  "0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0": "Ethereum escrow AND Base staticFeeCalculatorFactory share this address (different chains, safe but confusing)",
};

// ============================================================
// Verification logic
// ============================================================

interface VerifyResult {
  name: string;
  pass: boolean;
  bytecodePresent: boolean;
  feeCalculator: string | null;
  feeBps: bigint | null;
  releaseCondition: string | null;
  refundCondition: string | null;
  errors: string[];
  warnings: string[];
}

async function verifyOperator(name: string, config: OperatorConfig): Promise<VerifyResult> {
  const result: VerifyResult = {
    name,
    pass: true,
    bytecodePresent: false,
    feeCalculator: null,
    feeBps: null,
    releaseCondition: null,
    refundCondition: null,
    errors: [],
    warnings: [],
  };

  const client = createPublicClient({
    chain: config.chain,
    transport: http(config.rpcUrl),
  });

  // Step 1: Check bytecode exists at operator
  try {
    const code = await client.getCode({ address: config.operator });
    if (!code || code === "0x") {
      result.errors.push(`No bytecode at operator ${config.operator}`);
      result.pass = false;
      return result;
    }
    result.bytecodePresent = true;
  } catch (e: any) {
    result.errors.push(`RPC error checking bytecode: ${e.message?.substring(0, 100)}`);
    result.pass = false;
    return result;
  }

  // Step 2: Check bytecode at escrow
  try {
    const escrowCode = await client.getCode({ address: config.escrow });
    if (!escrowCode || escrowCode === "0x") {
      result.errors.push(`No bytecode at escrow ${config.escrow}`);
      result.pass = false;
    }
  } catch (e: any) {
    result.errors.push(`RPC error checking escrow bytecode: ${e.message?.substring(0, 100)}`);
  }

  // Step 3: Read FEE_CALCULATOR
  try {
    const feeCalcAddr = await client.readContract({
      address: config.operator,
      abi: OPERATOR_ABI,
      functionName: "FEE_CALCULATOR",
    }) as Address;
    result.feeCalculator = feeCalcAddr;

    // Step 3b: Read FEE_BPS from fee calculator
    try {
      const feeBps = await client.readContract({
        address: feeCalcAddr,
        abi: FEE_CALC_ABI,
        functionName: "FEE_BPS",
      }) as bigint;
      result.feeBps = feeBps;

      if (feeBps !== EXPECTED_FEE_BPS) {
        result.errors.push(`FEE_BPS mismatch: got ${feeBps}, expected ${EXPECTED_FEE_BPS}`);
        result.pass = false;
      }
    } catch (e: any) {
      result.errors.push(`Failed to read FEE_BPS from ${feeCalcAddr}: ${e.message?.substring(0, 100)}`);
      result.pass = false;
    }
  } catch (e: any) {
    result.errors.push(`Failed to read FEE_CALCULATOR: ${e.message?.substring(0, 100)}`);
    result.pass = false;
  }

  // Step 4: Read RELEASE_CONDITION
  try {
    const releaseCond = await client.readContract({
      address: config.operator,
      abi: OPERATOR_ABI,
      functionName: "RELEASE_CONDITION",
    }) as Address;
    result.releaseCondition = releaseCond;
  } catch (e: any) {
    result.warnings.push(`Failed to read RELEASE_CONDITION: ${e.message?.substring(0, 100)}`);
  }

  // Step 5: Read REFUND_IN_ESCROW_CONDITION
  try {
    const refundCond = await client.readContract({
      address: config.operator,
      abi: OPERATOR_ABI,
      functionName: "REFUND_IN_ESCROW_CONDITION",
    }) as Address;
    result.refundCondition = refundCond;
  } catch (e: any) {
    result.warnings.push(`Failed to read REFUND_IN_ESCROW_CONDITION: ${e.message?.substring(0, 100)}`);
  }

  // Step 6: Check known address collisions
  for (const addr of [config.operator, config.escrow]) {
    const collision = KNOWN_COLLISIONS[addr];
    if (collision) {
      result.warnings.push(`Known address collision: ${collision}`);
    }
  }

  return result;
}

// ============================================================
// Main
// ============================================================

async function main() {
  console.log("=== EM PaymentOperator On-Chain Verification ===");
  console.log(`Expected FEE_BPS: ${EXPECTED_FEE_BPS} (13%)`);
  console.log(`Chains to verify: ${Object.keys(OPERATORS).length}\n`);

  let passCount = 0;
  let failCount = 0;

  for (const [name, config] of Object.entries(OPERATORS)) {
    process.stdout.write(`[${name}] Verifying ${config.operator.substring(0, 10)}... `);

    try {
      const result = await verifyOperator(name, config);

      if (result.pass) {
        passCount++;
        console.log(`PASS (FEE_BPS=${result.feeBps})`);
      } else {
        failCount++;
        console.log("FAIL");
        for (const err of result.errors) {
          console.log(`  ERROR: ${err}`);
        }
      }

      for (const warn of result.warnings) {
        console.log(`  WARN: ${warn}`);
      }

      if (result.feeCalculator) {
        console.log(`  FEE_CALCULATOR: ${result.feeCalculator}`);
      }
      if (result.releaseCondition) {
        console.log(`  RELEASE_CONDITION: ${result.releaseCondition}`);
      }
      if (result.refundCondition) {
        console.log(`  REFUND_IN_ESCROW_CONDITION: ${result.refundCondition}`);
      }
    } catch (e: any) {
      failCount++;
      console.log(`FAIL (unhandled: ${e.message?.substring(0, 100)})`);
    }

    console.log();
  }

  // Summary
  console.log("=== Summary ===");
  console.log(`PASS: ${passCount}/${Object.keys(OPERATORS).length}`);
  console.log(`FAIL: ${failCount}/${Object.keys(OPERATORS).length}`);

  if (failCount > 0) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});

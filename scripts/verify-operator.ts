import { createPublicClient, http, parseAbi } from "viem";
import { base } from "viem/chains";

const client = createPublicClient({
  chain: base,
  transport: http("https://mainnet.base.org", { timeout: 30_000, retryCount: 3, retryDelay: 2000 }),
});

const newOp = "0x030353642B936c9D4213caD7BcB0fB8a1489cBe5" as const;
const oldOp = "0xd5149049e7c212ce5436a9581b4307EB9595df95" as const;
const EXPECTED_FACILITATOR = "0x9d03c03c15563E72CF2186E9FDB859A00ea661fc";
const EXPECTED_OR = "0xb365717C35004089996F72939b0C5b32Fa2ef8aE";

const abi = parseAbi([
  "function FEE_CALCULATOR() external view returns (address)",
  "function RELEASE_CONDITION() external view returns (address)",
  "function REFUND_IN_ESCROW_CONDITION() external view returns (address)",
  "function AUTHORIZE_CONDITION() external view returns (address)",
  "function FEE_RECIPIENT() external view returns (address)",
  "function ESCROW() external view returns (address)",
]);

async function readAll(label: string, addr: typeof newOp | typeof oldOp) {
  console.log(`\n=== ${label} (${addr}) ===`);
  for (const fn of ["FEE_CALCULATOR", "RELEASE_CONDITION", "REFUND_IN_ESCROW_CONDITION", "AUTHORIZE_CONDITION", "FEE_RECIPIENT", "ESCROW"] as const) {
    try {
      const result = await client.readContract({ address: addr, abi, functionName: fn });
      console.log(`  ${fn}: ${result}`);
    } catch (e: any) {
      console.log(`  ${fn}: ERROR — ${e.shortMessage?.slice(0, 100) || e.message?.slice(0, 100)}`);
    }
  }
}

await readAll("NEW Fase 4 Secure", newOp);
await readAll("OLD Fase 3 Clean (reference)", oldOp);

// Security check
console.log("\n=== SECURITY VERIFICATION ===");
try {
  const refund = await client.readContract({ address: newOp, abi, functionName: "REFUND_IN_ESCROW_CONDITION" });
  if (refund.toLowerCase() === EXPECTED_FACILITATOR.toLowerCase()) {
    console.log("PASS: refundInEscrow = FacilitatorOnly (SECURE)");
  } else if (refund.toLowerCase() === EXPECTED_OR.toLowerCase()) {
    console.log("FAIL: refundInEscrow = OrCondition (VULNERABLE!)");
  } else {
    console.log("UNKNOWN: refundInEscrow = " + refund);
  }
} catch {
  console.log("COULD NOT READ refundInEscrowCondition — RPC may be rate limiting");
}

process.exit(0);

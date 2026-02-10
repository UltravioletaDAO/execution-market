/**
 * DEPRECATED: ChambaEscrow deployment script.
 *
 * ChambaEscrow has been replaced by the x402 Facilitator (gasless, EIP-3009).
 * All payment operations now go through `uvd-x402-sdk` + Facilitator.
 *
 * This script is preserved for reference only. Do NOT run it.
 * Source code archived at: _archive/contracts/ChambaEscrow.sol
 *
 * For current escrow operations, see:
 *   - mcp_server/integrations/x402/sdk_client.py
 *   - https://facilitator.ultravioletadao.xyz
 */

async function main() {
  console.error("ERROR: ChambaEscrow deployment is DEPRECATED.");
  console.error("All payments now use the x402 Facilitator (gasless, EIP-3009).");
  console.error("See: mcp_server/integrations/x402/sdk_client.py");
  process.exit(1);
}

main().catch(console.error);

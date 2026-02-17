/**
 * DEPRECATED: Legacy escrow deployment script.
 *
 * The legacy custom escrow has been replaced by the x402 Facilitator (gasless, EIP-3009).
 * All payment operations now go through `uvd-x402-sdk` + Facilitator.
 *
 * This script is preserved for reference only. Do NOT run it.
 * Source code archived at: _archive/contracts/
 *
 * For current escrow operations, see:
 *   - mcp_server/integrations/x402/sdk_client.py
 *   - https://facilitator.ultravioletadao.xyz
 */

async function main() {
  console.error("ERROR: Legacy escrow deployment is DEPRECATED.");
  console.error("All payments now use the x402 Facilitator (gasless, EIP-3009).");
  console.error("See: mcp_server/integrations/x402/sdk_client.py");
  process.exit(1);
}

main().catch(console.error);

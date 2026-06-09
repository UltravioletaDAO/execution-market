/**
 * Phase 3 — em-robot-skill registration entry point.
 *
 * The main OWS MCP server (`src/server.ts`) calls `registerEmRobotSkill(server)`
 * to attach the five robot tools. Splitting into a function lets a future
 * `skill enable / disable` flow gate the registration without rewriting
 * `server.ts`.
 *
 * Tools registered (Phase 3.2 – 3.6):
 *   - robot_accept_task
 *   - robot_scan_barcode
 *   - robot_open_payshell_session
 *   - robot_sign_voucher_tick
 *   - robot_close_payshell_session
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { registerAcceptTask } from "./accept.js";
import { registerClosePayshellSession } from "./payshell_close.js";
import { registerOpenPayshellSession } from "./payshell_open.js";
import { registerScanBarcode } from "./scan.js";
import { registerSignVoucherTick } from "./voucher_tick.js";

export function registerEmRobotSkill(server: McpServer): void {
  registerAcceptTask(server);
  registerScanBarcode(server);
  registerOpenPayshellSession(server);
  registerSignVoucherTick(server);
  registerClosePayshellSession(server);
}

export { assertZeroSolBalance, requireCinematicZeroSol } from "./_fee_payer.js";
export { serializeVoucher } from "./voucher_tick.js";

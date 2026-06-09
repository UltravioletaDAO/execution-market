/**
 * Phase 3.2 — `robot_accept_task` tool.
 *
 * The robot applies to a published Execution Market task. Per the master plan
 * the call goes **through pay.sh** (`EM_PAYSHELL_URL`) which forwards to the
 * Python backend; pay.sh treats EM REST routes as pass-through and only
 * intercepts payment-channel paths. So the same URL host serves both worlds.
 *
 * The actual endpoint is `POST /api/v1/tasks/{id}/applications` — the master
 * plan wording "POST /accept" is shorthand. The applications endpoint creates
 * the application row that the publisher then assigns via `em_assign_task`.
 *
 * Idempotency: the EM backend deduplicates by (task_id, wallet). Calling the
 * tool twice with the same wallet returns the existing row's `application_id`
 * rather than a 409.
 *
 * Security notes:
 *   - The wallet's private key never leaves the OWS vault — the signed
 *     request flows through `signedRequest()` in `_http.ts`.
 *   - The optional `auto_assign` flag is OFF by default. Auto-assign relies
 *     on the publisher's policy and only succeeds if the publisher allows
 *     first-come applications. For Scenario B/C (browser worker) the human
 *     publisher taps "Assign" in the dashboard.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import {
  debugLog,
  getApiBase,
  resolveSolanaAccount,
  signedRequest,
} from "./_http.js";

export function registerAcceptTask(server: McpServer): void {
  server.registerTool(
    "robot_accept_task",
    {
      title: "Robot — Accept Task",
      description:
        "Apply to an Execution Market task as a worker using the robot's OWS Solana wallet. " +
        "Posts to /api/v1/tasks/{id}/applications via the pay.sh proxy. " +
        "Returns the application_id and (if auto_assign succeeded) the assignment status. " +
        "Re-running with the same wallet is a no-op — the existing application is returned.",
      inputSchema: {
        wallet: z
          .string()
          .describe("OWS wallet name — must have a solana: account"),
        task_id: z
          .string()
          .describe("EM task UUID returned by em_publish_task"),
        message: z
          .string()
          .optional()
          .describe(
            "Optional cover message visible to the publisher (max ~280 chars)",
          ),
        auto_assign: z
          .boolean()
          .optional()
          .describe(
            "Ask the EM backend to auto-assign if the publisher allows it (default false)",
          ),
        passphrase: z
          .string()
          .optional()
          .describe("Wallet passphrase if set during creation"),
      },
    },
    async ({ wallet, task_id, message, auto_assign, passphrase }) => {
      try {
        const account = resolveSolanaAccount(wallet);
        const url = `${getApiBase()}/api/v1/tasks/${task_id}/applications`;
        const body = {
          wallet_address: account.address,
          chain: "solana",
          message: message ?? "robot worker — em-robot-skill",
          auto_assign: auto_assign ?? false,
        };
        debugLog("accept.request", { url, body });

        const resp = await signedRequest({
          walletName: wallet,
          passphrase,
          method: "POST",
          url,
          body,
          taskId: task_id,
        });
        debugLog("accept.response", {
          status: resp.status,
          body: resp.body,
        });

        if (resp.status >= 400) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "task_not_assignable",
                    status: resp.status,
                    body: resp.body,
                    hint:
                      resp.status === 401
                        ? "wallet signature rejected — confirm OWS wallet matches the registered worker pubkey"
                        : resp.status === 404
                          ? "task not found — verify task_id is correct and task is still in published state"
                          : resp.status === 409
                            ? "already applied with this wallet (idempotent — see body.application_id)"
                            : undefined,
                  },
                  null,
                  2,
                ),
              },
            ],
            isError: resp.status !== 409,
          };
        }

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  success: true,
                  task_id,
                  wallet: account.address,
                  application: resp.body,
                  next_step:
                    "Wait for publisher to assign you. Then call robot_open_payshell_session to open the MPP channel.",
                },
                null,
                2,
              ),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  success: false,
                  error:
                    err instanceof Error && err.message.includes("solana")
                      ? "no_solana_account"
                      : err instanceof Error && err.message.includes("EM_PAYSHELL_URL")
                        ? "config_missing"
                        : "internal_error",
                  message:
                    err instanceof Error ? err.message : String(err),
                },
                null,
                2,
              ),
            },
          ],
          isError: true,
        };
      }
    },
  );
}

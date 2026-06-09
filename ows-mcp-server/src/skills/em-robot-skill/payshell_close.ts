/**
 * Phase 3.6 — `robot_close_payshell_session` tool.
 *
 * Closes an MPP channel and triggers pay.sh's `settleAndFinalize` +
 * `distribute` instructions (atomic 87 % worker / 13 % treasury split, plus
 * refund of any unused cap to the original payer). Per spec the close call
 * is a simple HTTP POST against pay.sh — pay.sh consumes the last accepted
 * voucher as the `finalCumulative` and submits the on-chain settlement.
 *
 * The robot does NOT sign the settlement transaction. Settlement signing is
 * pay.sh's responsibility (the facilitator key signs the on-chain
 * instruction). The robot only needs to authenticate the close request.
 *
 * Idempotency: calling close twice returns the same tx hash. pay.sh stores
 * the settlement result on the channel record.
 *
 * What gets returned:
 *   - `settlement_tx_hash` — Solana tx signature (base58). Visible on
 *     Solscan / Surfpool Studio.
 *   - `final_cumulative_uusdc` — what pay.sh actually settled (may differ
 *     from the last voucher if the channel was already past expiry).
 *   - `refund_uusdc` — unused cap returned to payer.
 *   - `distribution` — per-recipient amounts (worker, treasury).
 *
 * The Execution Market backend mirrors this event through the taxímetro SSE
 * relay (Phase 2.8) and `on_settlement_complete` in `task_channel_binding.py`
 * — which is what flips the task to COMPLETED.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import {
  debugLog,
  getPayshellBase,
  resolveSolanaAccount,
  signedRequest,
} from "./_http.js";

export function registerClosePayshellSession(server: McpServer): void {
  server.registerTool(
    "robot_close_payshell_session",
    {
      title: "Robot — Close pay.sh MPP Session",
      description:
        "Close an MPP channel. pay.sh runs settleAndFinalize + distribute atomically " +
        "(87% worker / 13% treasury + refund unused cap). Returns the settlement tx hash. " +
        "Idempotent — calling twice yields the same hash.",
      inputSchema: {
        wallet: z
          .string()
          .describe(
            "OWS wallet — used to auth the close request (must match channel payee)",
          ),
        channel_id: z.string().describe("Base58 channel id"),
        final_cumulative_micro_usdc: z
          .union([z.number(), z.string()])
          .optional()
          .describe(
            "If provided, overrides pay.sh's internal counter (useful for forcing a finalisation slightly above the last voucher). Defaults to whatever pay.sh has accepted.",
          ),
        passphrase: z.string().optional(),
      },
    },
    async ({
      wallet,
      channel_id,
      final_cumulative_micro_usdc,
      passphrase,
    }) => {
      try {
        const account = resolveSolanaAccount(wallet);
        const url = `${getPayshellBase()}/_sessions/${channel_id}/close`;
        const body: Record<string, unknown> = {
          channelId: channel_id,
          signer: account.address,
        };
        if (final_cumulative_micro_usdc !== undefined) {
          body.finalCumulativeMicroUsdc = String(
            final_cumulative_micro_usdc,
          );
        }
        debugLog("close.request", { url, body });

        const resp = await signedRequest({
          walletName: wallet,
          passphrase,
          method: "POST",
          url,
          body,
        });

        if (resp.status >= 400) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "close_rejected",
                    status: resp.status,
                    body: resp.body,
                    hint:
                      resp.status === 404
                        ? "channel not found — already settled?"
                        : resp.status === 409
                          ? "channel already closed (idempotent — see body.settlement_tx_hash)"
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

        const parsed = (resp.body ?? {}) as Record<string, unknown>;
        const txHash =
          (parsed.settlementTxHash as string | undefined) ??
          (parsed.tx_hash as string | undefined) ??
          (parsed.signature as string | undefined) ??
          null;
        if (!txHash) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "settlement_no_tx_hash",
                    body: parsed,
                    hint:
                      "close succeeded but no tx hash returned — see docs/runbooks/payshell-ops.md §Settlement event never arrived",
                  },
                  null,
                  2,
                ),
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  success: true,
                  channel_id,
                  settlement_tx_hash: txHash,
                  final_cumulative_uusdc:
                    parsed.finalCumulativeUusdc ??
                    parsed.final_cumulative_uusdc ??
                    null,
                  refund_uusdc:
                    parsed.refundUusdc ?? parsed.refund_uusdc ?? null,
                  distribution: parsed.distribution ?? null,
                  next_step:
                    "EM backend will mirror the settlement_complete event and transition the task to COMPLETED.",
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
                  error: "internal_error",
                  message: err instanceof Error ? err.message : String(err),
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

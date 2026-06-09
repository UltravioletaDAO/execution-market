/**
 * Phase 3.3 — `robot_scan_barcode` tool (mock-friendly).
 *
 * In the demo the robot scans a QR or barcode on a physical item (per D-22
 * scenario A) or pretends to (scenarios B/C/D). We do NOT pull in a camera or
 * image-decoding library — the tool accepts a `payload` field that the caller
 * already extracted, so:
 *   - Real robot: cv2 / native scanner produces text, passes it here
 *   - Simulator: caller injects the expected `payload` string directly
 *   - Browser scenario B/C: WorkerConsole.tsx uses BarcodeDetector / Quagga
 *     and passes the decoded string
 *
 * The tool then POSTs the scan as an evidence submission to the EM backend,
 * so the publisher can verify (or the arbiter can score) it later.
 *
 * Why no image decoder here: keeping the skill stateless and dep-free means
 * Saul can run it from a humanoid robot, a CLI laptop, or a browser fetch —
 * the same wire shape. Image decoding belongs in the worker process that
 * already has camera access; the skill's only job is the auth-signed POST.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import {
  debugLog,
  getApiBase,
  resolveSolanaAccount,
  signedRequest,
} from "./_http.js";

export function registerScanBarcode(server: McpServer): void {
  server.registerTool(
    "robot_scan_barcode",
    {
      title: "Robot — Submit Barcode/QR Scan as Evidence",
      description:
        "Submit a decoded barcode/QR payload as evidence for an Execution Market task. " +
        "Image decoding is the caller's responsibility (real robot uses on-board CV, " +
        "simulator injects the expected payload directly). " +
        "Returns the evidence submission id on success.",
      inputSchema: {
        wallet: z
          .string()
          .describe("OWS wallet name — must match the worker assigned to this task"),
        task_id: z.string().describe("EM task UUID"),
        payload: z
          .string()
          .describe(
            "Decoded barcode/QR text. Caller already ran image → text decoding.",
          ),
        expected_payload: z
          .string()
          .optional()
          .describe(
            "Optional client-side sanity check — if provided and payload differs, the tool returns an error WITHOUT calling the backend (saves a round-trip in dev).",
          ),
        evidence_type: z
          .enum(["barcode", "qr_code", "json_response"])
          .optional()
          .default("barcode")
          .describe("Evidence type tag used by the EM verifier"),
        passphrase: z.string().optional(),
      },
    },
    async ({
      wallet,
      task_id,
      payload,
      expected_payload,
      evidence_type,
      passphrase,
    }) => {
      try {
        if (expected_payload && expected_payload !== payload) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "payload_mismatch",
                    expected: expected_payload,
                    got: payload,
                    hint: "client-side sanity check failed — no backend call issued",
                  },
                  null,
                  2,
                ),
              },
            ],
            isError: true,
          };
        }

        const account = resolveSolanaAccount(wallet);
        const url = `${getApiBase()}/api/v1/tasks/${task_id}/submissions`;
        const body = {
          worker_wallet: account.address,
          chain: "solana",
          evidence: {
            [evidence_type ?? "barcode"]: {
              decoded_payload: payload,
              decoded_at: new Date().toISOString(),
              source: "em-robot-skill/scan",
            },
          },
        };
        debugLog("scan.request", { url, payload_preview: payload.slice(0, 40) });

        const resp = await signedRequest({
          walletName: wallet,
          passphrase,
          method: "POST",
          url,
          body,
          taskId: task_id,
        });
        debugLog("scan.response", {
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
                    error: "submission_rejected",
                    status: resp.status,
                    body: resp.body,
                    hint:
                      resp.status === 403
                        ? "wallet is not the assigned worker for this task"
                        : resp.status === 404
                          ? "task not found"
                          : resp.status === 422
                            ? "evidence schema validation failed — check evidence_type"
                            : undefined,
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
                  verified: true,
                  task_id,
                  evidence_type: evidence_type ?? "barcode",
                  payload_length: payload.length,
                  submission: resp.body,
                  next_step:
                    "Continue with robot_open_payshell_session if not already opened.",
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

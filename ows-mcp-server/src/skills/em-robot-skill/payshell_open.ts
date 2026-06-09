/**
 * Phase 3.4 — `robot_open_payshell_session` tool.
 *
 * Opens an MPP payment channel against the pay.sh proxy. Flow (per Solana
 * Foundation pay.sh CLI / spec `[[SOLANA_MPP_specs_pr201]]` §3.4):
 *
 *   1. Robot GETs a pay.sh-protected endpoint with `X-EM-Task-Id` header.
 *      pay.sh, finding no active session, responds **402 Payment Required**
 *      with a JSON challenge in the `Payment-Required` (or `Www-Authenticate`)
 *      header describing the cap, mint, splits, payer/payee, and the canonical
 *      `OpenChannelAuth` message to sign.
 *
 *   2. Robot signs the challenge message with its OWS Solana Ed25519 key.
 *      No on-chain TX — the signature is a credential. Fee sponsorship means
 *      pay.sh's embedded facilitator adds its own signature and pays SOL gas.
 *
 *   3. Robot retries the original GET with `X-Payment` header carrying the
 *      base64-encoded signed envelope. pay.sh validates, opens the PDA
 *      escrow on-chain (settles atomic split via `splits` map), and returns
 *      `channelId` plus the original protected endpoint response.
 *
 * We surface every step in the tool output so the demo dashboard / cinematic
 * UI can show the exact moment the channel opened (taxímetro starts ticking
 * from `acceptedCumulative=0`).
 *
 * Cinematic precondition: robot wallet has 0 SOL. Asserted via
 * `requireCinematicZeroSol()` from `_fee_payer.ts`. Operator can bypass with
 * `EM_ROBOT_SKILL_ALLOW_SOL=1` (we still proceed, just lose the cinematic
 * status flag in the response).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as ows from "@open-wallet-standard/core";

import {
  assertZeroSolBalance,
} from "./_fee_payer.js";
import {
  debugLog,
  getPayshellBase,
  resolveSolanaAccount,
} from "./_http.js";

interface PayshellChallenge {
  scheme: string;
  network: string;
  version?: string;
  x402Version?: number;
  channelId?: string;
  payTo?: string;
  asset?: string;
  mint?: string;
  cap?: string | number;
  capUusdc?: string | number;
  splits?: Record<string, number>;
  expiresAt?: number;
  canonical?: string;
  challenge?: string;
  rpcUrl?: string;
}

function parseChallengeFromHeaders(headers: Headers): PayshellChallenge | null {
  const raw =
    headers.get("payment-required") ??
    headers.get("x-payment-required") ??
    headers.get("www-authenticate");
  if (!raw) return null;
  try {
    if (raw.startsWith("{")) {
      return JSON.parse(raw) as PayshellChallenge;
    }
    const match = raw.match(/x402\s+(.+)$/i);
    if (match) {
      return JSON.parse(match[1]) as PayshellChallenge;
    }
  } catch (e) {
    debugLog("open.parse_challenge_failed", String(e));
  }
  return null;
}

async function parseChallengeFromBody(resp: Response): Promise<PayshellChallenge | null> {
  const contentType = resp.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return null;
  try {
    const body = (await resp.clone().json()) as PayshellChallenge;
    if (body && typeof body === "object") return body;
  } catch (e) {
    debugLog("open.body_parse_failed", String(e));
  }
  return null;
}

export function registerOpenPayshellSession(server: McpServer): void {
  server.registerTool(
    "robot_open_payshell_session",
    {
      title: "Robot — Open pay.sh MPP Session",
      description:
        "Open an MPP payment channel against the pay.sh proxy. " +
        "Performs the x402 402-challenge handshake, signs OpenChannelAuth via OWS Solana Ed25519, " +
        "and receives a channelId. Server pays SOL gas (fee sponsorship), robot wallet stays 0 SOL.",
      inputSchema: {
        wallet: z
          .string()
          .describe("OWS wallet name — Solana account is used"),
        task_id: z
          .string()
          .describe("EM task UUID — included as X-EM-Task-Id for channel binding"),
        endpoint: z
          .string()
          .optional()
          .default("/hello")
          .describe(
            "Protected endpoint to hit. Default /hello is pay.sh's smoke-test handler.",
          ),
        passphrase: z.string().optional(),
        assert_zero_sol: z
          .boolean()
          .optional()
          .default(true)
          .describe(
            "Verify the robot wallet has 0 SOL before opening. Disable for non-cinematic flows.",
          ),
      },
    },
    async ({ wallet, task_id, endpoint, passphrase, assert_zero_sol }) => {
      try {
        const account = resolveSolanaAccount(wallet);

        let balanceCheck: Awaited<ReturnType<typeof assertZeroSolBalance>> | null = null;
        if (assert_zero_sol !== false) {
          balanceCheck = await assertZeroSolBalance(wallet);
          if (!balanceCheck.cinematic && process.env.EM_ROBOT_SKILL_ALLOW_SOL !== "1") {
            return {
              content: [
                {
                  type: "text" as const,
                  text: JSON.stringify(
                    {
                      success: false,
                      error: "non_cinematic_balance",
                      lamports: balanceCheck.lamports,
                      hint:
                        "robot wallet must be 0 SOL for fee sponsorship demo. " +
                        "Set EM_ROBOT_SKILL_ALLOW_SOL=1 to bypass.",
                    },
                    null,
                    2,
                  ),
                },
              ],
              isError: true,
            };
          }
        }

        const base = getPayshellBase();
        const url = `${base}${endpoint.startsWith("/") ? endpoint : "/" + endpoint}`;

        // Step 1: provoke the 402 challenge.
        const probeHeaders: Record<string, string> = {
          "X-EM-Task-Id": task_id,
          "X-EM-Worker-Wallet": account.address,
          "X-EM-Worker-Chain": "solana",
          Accept: "application/json",
        };
        debugLog("open.probe", { url, taskId: task_id });
        const probe = await fetch(url, { method: "GET", headers: probeHeaders });

        if (probe.status !== 402) {
          if (probe.status >= 200 && probe.status < 300) {
            // Either pay.sh already had an open session, or the endpoint is
            // unprotected — surface that so the caller doesn't double-open.
            const body = await probe.json().catch(() => ({}));
            return {
              content: [
                {
                  type: "text" as const,
                  text: JSON.stringify(
                    {
                      success: true,
                      already_open: true,
                      task_id,
                      wallet: account.address,
                      body,
                      hint:
                        "pay.sh responded 200 without challenge — session may already be open",
                    },
                    null,
                    2,
                  ),
                },
              ],
            };
          }
          const errBody = await probe.text().catch(() => "");
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "payshell_unreachable",
                    status: probe.status,
                    body: errBody.slice(0, 500),
                    hint:
                      "expected 402 Payment Required, got " +
                      probe.status +
                      " — check EM_PAYSHELL_URL points at pay.sh proxy",
                  },
                  null,
                  2,
                ),
              },
            ],
            isError: true,
          };
        }

        const challenge =
          parseChallengeFromHeaders(probe.headers) ??
          (await parseChallengeFromBody(probe));
        if (!challenge) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "challenge_parse_failed",
                    hint: "pay.sh returned 402 but no challenge was readable",
                  },
                  null,
                  2,
                ),
              },
            ],
            isError: true,
          };
        }

        const messageToSign =
          challenge.canonical ?? challenge.challenge ?? JSON.stringify(challenge);
        debugLog("open.signing_challenge", {
          length: messageToSign.length,
          scheme: challenge.scheme,
        });

        // Step 2: sign with OWS Solana Ed25519.
        const sig = ows.signMessage(
          wallet,
          "solana",
          messageToSign,
          passphrase ?? undefined,
        );

        // Step 3: assemble the X-Payment envelope and retry.
        const envelope = {
          x402Version: challenge.x402Version ?? 1,
          scheme: challenge.scheme ?? "mpp-session",
          network: challenge.network ?? "solana",
          payload: {
            signer: account.address,
            signature: sig.signature,
            message: messageToSign,
            payee: account.address,
            taskId: task_id,
          },
        };
        const paymentHeader = Buffer.from(JSON.stringify(envelope), "utf8").toString(
          "base64",
        );

        const settledHeaders: Record<string, string> = {
          ...probeHeaders,
          "X-Payment": paymentHeader,
        };
        debugLog("open.retry_with_payment", { url });
        const settled = await fetch(url, {
          method: "GET",
          headers: settledHeaders,
        });

        if (settled.status >= 400) {
          const errBody = await settled.text().catch(() => "");
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "payshell_open_rejected",
                    status: settled.status,
                    body: errBody.slice(0, 500),
                  },
                  null,
                  2,
                ),
              },
            ],
            isError: true,
          };
        }

        const channelId =
          settled.headers.get("x-payment-response-channel-id") ??
          settled.headers.get("x-payshell-channel-id") ??
          challenge.channelId ??
          null;

        const responseBody = await settled
          .json()
          .catch(() => ({ note: "non-JSON pay.sh response" }));

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  success: true,
                  task_id,
                  wallet: account.address,
                  channel_id: channelId,
                  cap_uusdc: challenge.capUusdc ?? challenge.cap ?? null,
                  splits: challenge.splits ?? null,
                  expires_at: challenge.expiresAt ?? null,
                  fee_sponsorship: balanceCheck?.cinematic
                    ? "active — robot wallet 0 SOL"
                    : balanceCheck?.warning ?? "unknown",
                  payshell_response: responseBody,
                  next_step:
                    "Call robot_sign_voucher_tick repeatedly while doing the work, then robot_close_payshell_session.",
                },
                null,
                2,
              ),
            },
          ],
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  success: false,
                  error: msg.includes("EM_PAYSHELL_URL")
                    ? "config_missing"
                    : msg.includes("solana")
                      ? "no_solana_account"
                      : "internal_error",
                  message: msg,
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

/**
 * Phase 3.5 — `robot_sign_voucher_tick` (single tick — caller drives cadence).
 *
 * Per `[[SOLANA_MPP_specs_pr201]]` §4 ("Voucher"), an MPP voucher is a 48-byte
 * Borsh-serialised struct:
 *
 *   struct Voucher {
 *     channel_id:           Pubkey  (32 bytes)
 *     cumulative_micro_usdc: u64    ( 8 bytes, little-endian)
 *     expires_at:           i64    ( 8 bytes, little-endian, unix seconds)
 *   }
 *
 * The worker signs the **bytes themselves** (Ed25519 over the 48 raw bytes —
 * no domain-separation tag because the channel_id already disambiguates).
 * pay.sh validates the signature against the worker pubkey it learned at
 * channel-open time.
 *
 * Why we serialise manually instead of pulling in `borsh` or `@solana/spl-*`:
 * the layout is fixed and tiny, and the skill is deliberately dep-light so it
 * runs anywhere (CLI laptop, robot embedded node, browser worker). Manual
 * DataView writes give us byte-for-byte determinism without 50 KB of deps.
 *
 * Cadence: NOT controlled by this tool. The caller (a CLI loop, a
 * WorkerConsole React component, the bundled `robot-sim.ts`) decides how
 * often to invoke. The tool is a single tick. This is a deliberate choice
 * matching the MCP request/response model — a server-side loop would tie up
 * the agent's MCP context for the duration of the work.
 *
 * Idempotency: pay.sh dedupes by `(channel_id, cumulative)`. Two ticks with
 * the same cumulative are a no-op success. A regression (lower cumulative
 * than already accepted) is rejected by pay.sh — surface the rejection so
 * the caller can adjust its counter.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import bs58 from "bs58";
import * as ows from "@open-wallet-standard/core";

import { debugLog, getPayshellBase, resolveSolanaAccount } from "./_http.js";

const VOUCHER_BYTES = 48;
const CHANNEL_ID_BYTES = 32;

/**
 * Serialise the 48-byte voucher payload exactly as pay.sh expects.
 * Throws if the inputs would produce an out-of-range or wrong-length result —
 * these are programmer errors, fail loudly.
 */
export function serializeVoucher(
  channelIdBase58: string,
  cumulativeMicroUsdc: bigint,
  expiresAtUnixSeconds: bigint,
): Uint8Array {
  const channelBytes = bs58.decode(channelIdBase58);
  if (channelBytes.length !== CHANNEL_ID_BYTES) {
    throw new Error(
      `channel_id must decode to ${CHANNEL_ID_BYTES} bytes, got ${channelBytes.length}`,
    );
  }
  if (cumulativeMicroUsdc < 0n || cumulativeMicroUsdc > 0xffffffffffffffffn) {
    throw new Error(
      `cumulative_micro_usdc out of u64 range: ${cumulativeMicroUsdc}`,
    );
  }
  // i64 range (signed): -9223372036854775808 .. 9223372036854775807
  const I64_MAX = 0x7fffffffffffffffn;
  const I64_MIN = -(I64_MAX + 1n);
  if (expiresAtUnixSeconds < I64_MIN || expiresAtUnixSeconds > I64_MAX) {
    throw new Error(
      `expires_at out of i64 range: ${expiresAtUnixSeconds}`,
    );
  }

  const out = new Uint8Array(VOUCHER_BYTES);
  out.set(channelBytes, 0);

  const view = new DataView(out.buffer);
  view.setBigUint64(CHANNEL_ID_BYTES, cumulativeMicroUsdc, true);
  view.setBigInt64(CHANNEL_ID_BYTES + 8, expiresAtUnixSeconds, true);
  return out;
}

export function registerSignVoucherTick(server: McpServer): void {
  server.registerTool(
    "robot_sign_voucher_tick",
    {
      title: "Robot — Sign a Single Voucher Tick",
      description:
        "Sign a single MPP voucher (48 bytes Borsh) and POST it to pay.sh. " +
        "Cumulative micro-USDC counter MUST be monotonically increasing across calls. " +
        "Caller drives cadence (e.g. one tick per second).",
      inputSchema: {
        wallet: z.string(),
        channel_id: z
          .string()
          .describe("Base58 channel id returned by robot_open_payshell_session"),
        cumulative_micro_usdc: z
          .union([z.number(), z.string()])
          .describe(
            "Cumulative spent so far in micro-USDC (1 USDC = 1e6). Monotonic.",
          ),
        expires_at_unix: z
          .union([z.number(), z.string()])
          .optional()
          .describe(
            "Voucher expiry unix-seconds. Defaults to now + 60 if omitted.",
          ),
        passphrase: z.string().optional(),
      },
    },
    async ({
      wallet,
      channel_id,
      cumulative_micro_usdc,
      expires_at_unix,
      passphrase,
    }) => {
      try {
        const account = resolveSolanaAccount(wallet);
        const cumulative = BigInt(cumulative_micro_usdc);
        const expiresAt =
          expires_at_unix !== undefined
            ? BigInt(expires_at_unix)
            : BigInt(Math.floor(Date.now() / 1000) + 60);

        const voucherBytes = serializeVoucher(
          channel_id,
          cumulative,
          expiresAt,
        );

        // OWS Solana sign accepts a string OR a typed array via the SDK
        // depending on version. We base64-encode to be transport-safe across
        // the native bindings while preserving exact bytes.
        const voucherBase64 = Buffer.from(voucherBytes).toString("base64");
        const sig = ows.signMessage(
          wallet,
          "solana",
          voucherBase64,
          passphrase ?? undefined,
        );

        const url = `${getPayshellBase()}/_sessions/${channel_id}/voucher`;
        const body = {
          channelId: channel_id,
          cumulativeMicroUsdc: cumulative.toString(),
          expiresAt: Number(expiresAt),
          signer: account.address,
          signature: sig.signature,
          voucherBytesBase64: voucherBase64,
        };
        debugLog("voucher.post", {
          url,
          cumulative: cumulative.toString(),
          expiresAt: Number(expiresAt),
        });

        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const contentType = resp.headers.get("content-type") ?? "";
        const respBody = contentType.includes("application/json")
          ? await resp.json().catch(() => ({}))
          : await resp.text().catch(() => "");

        if (resp.status >= 400) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(
                  {
                    success: false,
                    error: "voucher_rejected",
                    status: resp.status,
                    body: respBody,
                    hint:
                      resp.status === 409
                        ? "cumulative regressed below accepted value — increase counter"
                        : resp.status === 410
                          ? "voucher expired — bump expires_at_unix and retry"
                          : resp.status === 401
                            ? "signature invalid — confirm wallet matches channel payee"
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
                  channel_id,
                  cumulative_micro_usdc: cumulative.toString(),
                  expires_at_unix: Number(expiresAt),
                  signer: account.address,
                  payshell_response: respBody,
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

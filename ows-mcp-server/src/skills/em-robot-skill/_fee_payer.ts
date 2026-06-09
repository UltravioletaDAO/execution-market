/**
 * Phase 3.7 — Fee sponsorship integration boundary.
 *
 * Per `[[SOLANA_MPP_specs_pr201]]` §3.2 "Fee Sponsorship", pay.sh server
 * co-signs the on-chain transactions (`ix open PDA`, voucher refresh, settle,
 * topup) so the worker wallet itself never needs SOL. This is what preserves
 * the cinematic demo claim: "an empty wallet does real work because the
 * protocol sponsors the gas."
 *
 * This module's job is to ASSERT that property at runtime so the demo can
 * never silently drift into "actually the robot wallet had some SOL because
 * we accidentally airdropped it." The assertion is a non-fatal warning by
 * default — operator overrides via `EM_ROBOT_SKILL_ALLOW_SOL=1` skip the
 * check entirely (useful on networks where fee sponsorship is unavailable
 * and the worker has to pay its own gas).
 *
 * What this module does NOT do:
 *   - It does NOT sign anything. The fee-payer signature is added by pay.sh
 *     server-side and never crosses this skill's boundary.
 *   - It does NOT compute fee amounts. pay.sh's facilitator handles that.
 *   - It does NOT proxy SOL transfers — the robot wallet must end the demo
 *     with the same 0 SOL it started with.
 */

import { Connection, PublicKey } from "@solana/web3.js";

import { resolveSolanaAccount, debugLog } from "./_http.js";

const MAINNET_RPC_DEFAULT = "https://api.mainnet-beta.solana.com";

function getRpcUrl(): string {
  return process.env.SOLANA_RPC_URL ?? MAINNET_RPC_DEFAULT;
}

function allowSolBypass(): boolean {
  return (
    process.env.EM_ROBOT_SKILL_ALLOW_SOL === "1" ||
    process.env.EM_ROBOT_SKILL_ALLOW_SOL === "true"
  );
}

export interface ZeroSolAssertionResult {
  pubkey: string;
  lamports: number;
  cinematic: boolean;
  warning?: string;
}

/**
 * Verify the robot wallet has 0 SOL. Returns the actual lamports balance so
 * the caller can include it in tool output (the demo dashboard surfaces
 * "wallet balance: 0 SOL" as part of the cinematic copy).
 *
 * The result includes `cinematic: true` iff lamports === 0 AND fee sponsorship
 * is the expected payment path. When `allow_sol` env override is set, we
 * still report the balance but skip the strict cinematic claim.
 */
export async function assertZeroSolBalance(
  walletName: string,
): Promise<ZeroSolAssertionResult> {
  const account = resolveSolanaAccount(walletName);
  const conn = new Connection(getRpcUrl(), "confirmed");
  const pk = new PublicKey(account.address);
  const lamports = await conn.getBalance(pk, "confirmed");
  debugLog("fee_payer.balance_check", {
    pubkey: account.address,
    lamports,
  });

  if (lamports === 0) {
    return {
      pubkey: account.address,
      lamports: 0,
      cinematic: true,
    };
  }

  if (allowSolBypass()) {
    return {
      pubkey: account.address,
      lamports,
      cinematic: false,
      warning:
        "robot wallet holds SOL — EM_ROBOT_SKILL_ALLOW_SOL is set, bypassing strict assertion",
    };
  }

  return {
    pubkey: account.address,
    lamports,
    cinematic: false,
    warning:
      `robot wallet holds ${lamports} lamports — demo expects 0 for the cinematic "fee sponsorship" claim. ` +
      `Set EM_ROBOT_SKILL_ALLOW_SOL=1 to bypass, or empty the wallet before running.`,
  };
}

/**
 * Strict variant — throws if the wallet is non-zero AND no bypass flag is
 * set. Used by `robot_open_payshell_session` before initiating the 402
 * challenge so the demo can't accidentally proceed in a non-cinematic state.
 */
export async function requireCinematicZeroSol(walletName: string): Promise<void> {
  const result = await assertZeroSolBalance(walletName);
  if (!result.cinematic && !allowSolBypass()) {
    throw new Error(result.warning ?? "fee sponsorship precondition failed");
  }
}

/**
 * OWS Spending Policy Engine (L-82)
 *
 * The OWS server advertises "policy-gated spending" (server.ts header #5) but
 * historically signed any EIP-3009 USDC authorization for any amount to any
 * recipient. That makes a compromised/confused agent able to drain the wallet
 * with a single over-limit authorization.
 *
 * This module enforces a per-signature spending policy on the EIP-3009 / USDC
 * transfer-authorization signing paths:
 *   - a hard per-transaction USDC cap,
 *   - an optional recipient allowlist,
 *   - an optional rolling 24h cumulative cap (best-effort, in-process).
 *
 * Secure-by-default: the policy is ENABLED unless explicitly disabled, and the
 * per-tx cap has a finite default. Limits are read from environment variables —
 * no secrets are read or logged here.
 */

/** Parse a decimal-USDC env var, returning `fallback` when unset/invalid. */
function envNumber(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === null || raw.trim() === "") return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n) || n < 0) return fallback;
  return n;
}

/** Parse a comma-separated lowercase address allowlist (empty = allow any). */
function envAddressList(name: string): Set<string> {
  const raw = process.env[name];
  const set = new Set<string>();
  if (!raw) return set;
  for (const part of raw.split(",")) {
    const a = part.trim().toLowerCase();
    if (a) set.add(a);
  }
  return set;
}

export interface SpendingPolicy {
  enabled: boolean;
  /** Hard per-signature cap in USDC. */
  maxPerTxUsdc: number;
  /** Optional recipient allowlist (lowercased). Empty = any recipient. */
  allowedRecipients: Set<string>;
  /** Optional rolling-24h cumulative cap in USDC. 0 = no cumulative cap. */
  dailyLimitUsdc: number;
}

/**
 * Load the active policy from the environment.
 *
 * Env vars:
 *   OWS_SPENDING_POLICY_ENABLED   default "true"  (set "false" to disable)
 *   OWS_MAX_AMOUNT_USDC_PER_TX    default 100
 *   OWS_ALLOWED_RECIPIENTS        default "" (any)
 *   OWS_DAILY_LIMIT_USDC          default 0 (no cumulative cap)
 *
 * Read fresh on each call so tests and operators can change limits without a
 * process restart.
 */
export function loadSpendingPolicy(): SpendingPolicy {
  const enabledRaw = (process.env.OWS_SPENDING_POLICY_ENABLED ?? "true")
    .trim()
    .toLowerCase();
  // Secure default: anything other than an explicit "false"/"0"/"no" is enabled.
  const enabled = !["false", "0", "no", "off"].includes(enabledRaw);
  return {
    enabled,
    maxPerTxUsdc: envNumber("OWS_MAX_AMOUNT_USDC_PER_TX", 100),
    allowedRecipients: envAddressList("OWS_ALLOWED_RECIPIENTS"),
    dailyLimitUsdc: envNumber("OWS_DAILY_LIMIT_USDC", 0),
  };
}

export interface PolicyDecision {
  allowed: boolean;
  /** Human-readable reason when `allowed === false`. */
  reason?: string;
}

// ---------------------------------------------------------------------------
// Rolling 24h spend tracker (best-effort, in-process). Persists only for the
// lifetime of the server process — a hard per-tx cap is the primary control;
// the daily cap is defense-in-depth against many small authorizations.
// ---------------------------------------------------------------------------

interface SpendRecord {
  amount: number;
  at: number; // epoch ms
}
const DAY_MS = 24 * 60 * 60 * 1000;
const spendLog: SpendRecord[] = [];

function rollingSpend(now: number): number {
  const cutoff = now - DAY_MS;
  // Drop expired records.
  while (spendLog.length > 0 && spendLog[0].at < cutoff) {
    spendLog.shift();
  }
  return spendLog.reduce((acc, r) => acc + r.amount, 0);
}

/** Record a committed spend so it counts against the rolling daily cap. */
export function recordSpend(amountUsdc: number, now: number = Date.now()): void {
  if (amountUsdc > 0) spendLog.push({ amount: amountUsdc, at: now });
}

/** TEST-ONLY: reset the in-process rolling-spend log. */
export function _resetSpendLog(): void {
  spendLog.length = 0;
}

/**
 * Evaluate a proposed USDC transfer authorization against the policy.
 *
 * Does NOT record the spend — call `recordSpend()` only after the signature is
 * actually produced, so rejected attempts never consume the daily budget.
 *
 * @param amountUsdc  Transfer amount in decimal USDC.
 * @param toAddress   Recipient (EVM address; case-insensitive).
 * @param policy      Active policy (defaults to `loadSpendingPolicy()`).
 */
export function evaluateSpend(
  amountUsdc: number,
  toAddress: string,
  policy: SpendingPolicy = loadSpendingPolicy(),
  now: number = Date.now()
): PolicyDecision {
  if (!policy.enabled) {
    return { allowed: true };
  }

  // Reject non-finite / non-positive amounts outright — a 0 or NaN auth is
  // never legitimate and could be a probe.
  if (!Number.isFinite(amountUsdc) || amountUsdc <= 0) {
    return {
      allowed: false,
      reason: `Invalid amount ${String(amountUsdc)} — must be a positive USDC value.`,
    };
  }

  // Per-transaction hard cap.
  if (amountUsdc > policy.maxPerTxUsdc) {
    return {
      allowed: false,
      reason:
        `Amount ${amountUsdc} USDC exceeds the per-transaction limit of ` +
        `${policy.maxPerTxUsdc} USDC (OWS_MAX_AMOUNT_USDC_PER_TX). ` +
        `Raise the limit deliberately or split the payment.`,
    };
  }

  // Recipient allowlist (when configured).
  if (policy.allowedRecipients.size > 0) {
    const to = (toAddress ?? "").trim().toLowerCase();
    if (!policy.allowedRecipients.has(to)) {
      return {
        allowed: false,
        reason:
          `Recipient ${toAddress} is not in the allowlist ` +
          `(OWS_ALLOWED_RECIPIENTS).`,
      };
    }
  }

  // Rolling 24h cumulative cap (when configured).
  if (policy.dailyLimitUsdc > 0) {
    const spent = rollingSpend(now);
    if (spent + amountUsdc > policy.dailyLimitUsdc) {
      return {
        allowed: false,
        reason:
          `This ${amountUsdc} USDC authorization would push the rolling 24h ` +
          `spend (${spent} USDC already) past the daily limit of ` +
          `${policy.dailyLimitUsdc} USDC (OWS_DAILY_LIMIT_USDC).`,
      };
    }
  }

  return { allowed: true };
}

/**
 * Best-effort extraction of (amountUsdc, to) from EIP-712 typed data so the
 * `ows_sign_typed_data` path cannot be used to bypass the policy by signing a
 * raw TransferWithAuthorization / ReceiveWithAuthorization.
 *
 * Returns null when the typed data is not a USDC transfer authorization (other
 * EIP-712 messages — permits, ERC-8128 auth, etc. — are out of scope here).
 *
 * USDC uses 6 decimals; `value` in the message is the integer base-unit amount.
 */
export function extractUsdcTransferFromTypedData(
  typedData: unknown
): { amountUsdc: number; to: string } | null {
  if (!typedData || typeof typedData !== "object") return null;
  const td = typedData as Record<string, unknown>;
  const primaryType = String(td.primaryType ?? "");
  if (
    primaryType !== "TransferWithAuthorization" &&
    primaryType !== "ReceiveWithAuthorization"
  ) {
    return null;
  }
  const message = td.message;
  if (!message || typeof message !== "object") return null;
  const m = message as Record<string, unknown>;
  const rawValue = m.value;
  const to = typeof m.to === "string" ? m.to : "";
  if (rawValue === undefined || rawValue === null) return null;

  // value is a uint256 base-unit string/number; USDC has 6 decimals.
  let baseUnits: bigint;
  try {
    baseUnits = BigInt(typeof rawValue === "number" ? Math.trunc(rawValue) : String(rawValue));
  } catch {
    return null;
  }
  const amountUsdc = Number(baseUnits) / 1e6;
  return { amountUsdc, to };
}

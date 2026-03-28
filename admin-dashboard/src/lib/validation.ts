// ---------------------------------------------------------------------------
// Config value validation — pure utility, no React dependencies.
// Consumed by Settings.tsx and integration panels.
// ---------------------------------------------------------------------------

/** Returns null if valid, or an error message string if invalid. */
export type Validator = (value: unknown) => string | null

// ---------------------------------------------------------------------------
// Individual validators
// ---------------------------------------------------------------------------

/** Fee percentage stored as 0-1 decimal (e.g. 0.13 = 13%). */
export function validateFeePercent(value: number): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'Must be a number'
  if (value < 0 || value > 1) return 'Must be between 0% and 100% (0-1)'
  return null
}

/** Bounty amount in USD. */
export function validateBountyAmount(value: number, min = 0.01): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'Must be a number'
  if (value < min) return `Must be at least $${min}`
  return null
}

/** Integer within optional bounds. */
export function validateInteger(value: number, min?: number, max?: number): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'Must be a number'
  if (!Number.isInteger(value)) return 'Must be a whole number'
  if (min !== undefined && value < min) return `Must be at least ${min}`
  if (max !== undefined && value > max) return `Must be at most ${max}`
  return null
}

/** Hours — positive integer, 1-720 (30 days). */
export function validateHours(value: number): string | null {
  return validateInteger(value, 1, 720)
}

/** EVM wallet address: 0x-prefixed, 42 hex chars. */
export function validateWalletAddress(value: string): string | null {
  if (typeof value !== 'string') return 'Must be a string'
  if (!value.startsWith('0x')) return 'Must start with 0x'
  if (value.length !== 42) return 'Must be 42 characters (0x + 40 hex digits)'
  if (!/^0x[0-9a-fA-F]{40}$/.test(value)) return 'Contains invalid hex characters'
  return null
}

/** URL — must start with https://. */
export function validateUrl(value: string): string | null {
  if (typeof value !== 'string') return 'Must be a string'
  if (!value.startsWith('https://')) return 'Must start with https://'
  try {
    new URL(value)
  } catch {
    return 'Invalid URL format'
  }
  return null
}

/** Positive number (> 0). */
export function validatePositiveNumber(value: number): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'Must be a number'
  if (value <= 0) return 'Must be greater than 0'
  return null
}

// ---------------------------------------------------------------------------
// Config key -> validator map
// ---------------------------------------------------------------------------

const CONFIG_VALIDATORS: Record<string, Validator> = {
  // Fees (stored as 0-1 decimals)
  'fees.platform_fee_pct': (v) => validateFeePercent(v as number),
  'fees.partial_release_pct': (v) => validateFeePercent(v as number),
  'fees.protection_fund_pct': (v) => {
    const n = v as number
    if (typeof n !== 'number' || Number.isNaN(n)) return 'Must be a number'
    if (n < 0 || n > 0.05) return 'Must be between 0% and 5% (0-0.05)'
    return null
  },
  'fees.min_fee_usd': (v) => validateBountyAmount(v as number, 0.01),

  // Bounty limits
  'bounty.min_usd': (v) => validateBountyAmount(v as number),
  'bounty.max_usd': (v) => validateBountyAmount(v as number),

  // Limits (all integers 1-10000)
  'limits.max_resubmissions': (v) => validateInteger(v as number, 1, 10000),
  'limits.max_active_tasks_per_agent': (v) => validateInteger(v as number, 1, 10000),
  'limits.max_applications_per_task': (v) => validateInteger(v as number, 1, 10000),
  'limits.max_active_tasks_per_worker': (v) => validateInteger(v as number, 1, 10000),

  // Timeouts (hours)
  'timeout.approval_hours': (v) => validateHours(v as number),
  'timeout.task_default_hours': (v) => validateHours(v as number),

  // Chat / IRC
  'chat.retention_days': (v) => validateInteger(v as number, 1, 365),
  'chat.irc_port': (v) => validateInteger(v as number, 1, 65535),
  'chat.max_message_length': (v) => validateInteger(v as number, 100, 10000),
  'chat.history_limit': (v) => validateInteger(v as number, 10, 1000),

  // Treasury (wallet addresses)
  'treasury.wallet_address': (v) => validateWalletAddress(v as string),
  'treasury.protection_fund_address': (v) => validateWalletAddress(v as string),

  // URLs
  'meshrelay.api_url': (v) => validateUrl(v as string),
  'meshrelay.webhook_url': (v) => {
    // Webhook URL can be empty (disabled)
    if (typeof v === 'string' && v === '') return null
    return validateUrl(v as string)
  },
  'x402.facilitator_url': (v) => validateUrl(v as string),

  // MeshRelay numeric settings
  'meshrelay.anti_snipe_cooldown_sec': (v) => validateInteger(v as number, 0, 10000),
  'meshrelay.claim_priority_window_sec': (v) => validateInteger(v as number, 0, 10000),
  'meshrelay.channel_auto_expire_minutes': (v) => validateInteger(v as number, 1, 10000),
  'meshrelay.max_bids_per_auction': (v) => validateInteger(v as number, 1, 10000),
  'meshrelay.identity_sync_interval_sec': (v) => validateInteger(v as number, 10, 10000),
}

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------

/**
 * Validate a config value for a given key.
 * Returns null if valid (or no validator registered), error message otherwise.
 */
export function validateConfigValue(key: string, value: unknown): string | null {
  const validator = CONFIG_VALIDATORS[key]
  if (!validator) return null
  return validator(value)
}

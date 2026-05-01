/**
 * ClawKey KYA (Know Your Agent) Badge
 *
 * Mirrors the VeryAiBadge / WorldHumanBadge shape and styling. Renders a
 * small key icon — outlined for the unverified / unknown state, solid for
 * the verified state. Color stays in the project black/white/gray canon —
 * never blue, emerald, or any tier-specific accent.
 *
 * KYA is a public trust signal by design (see ClawKey docs). The tooltip
 * surfaces the truncated humanId when provided so a viewer can copy the
 * binding for an off-chain lookup, but the full human_id is intentionally
 * abbreviated in the UI to keep the badge unobtrusive.
 */

interface ClawKeyBadgeProps {
  /** Whether the executor's ClawKey binding has been confirmed upstream. */
  verified: boolean | null | undefined
  /** Optional ClawKey humanId — surfaced (truncated) in the tooltip. */
  humanId?: string | null
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_CLASSES: Record<NonNullable<ClawKeyBadgeProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}

// Heroicons "key" — outlined variant for the not-yet-verified state.
const KEY_OUTLINED_PATH =
  'M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z'

// Heroicons "key" — solid variant for the verified state.
const KEY_SOLID_PATH =
  'M15.75 1.5a6.75 6.75 0 0 0-6.651 7.906c.067.39-.032.717-.221.906l-6.5 6.499a3 3 0 0 0-.878 2.121v2.818c0 .414.336.75.75.75H6a.75.75 0 0 0 .75-.75v-1.5h1.5A.75.75 0 0 0 9 19.5V18h1.5a.75.75 0 0 0 .53-.22l2.658-2.658c.19-.189.517-.288.906-.22A6.75 6.75 0 1 0 15.75 1.5Zm0 3a.75.75 0 0 0 0 1.5A2.25 2.25 0 0 1 18 8.25a.75.75 0 0 0 1.5 0a3.75 3.75 0 0 0-3.75-3.75Z'

function _shortHumanId(humanId: string | null | undefined): string | null {
  if (!humanId) return null
  // Show first 10 chars to keep tooltips short while still distinguishable.
  // ClawKey humanIds look like "hum-abc123...", so 10 chars is enough
  // signal to copy/recognize without exposing a full value.
  return humanId.length > 12 ? `${humanId.slice(0, 10)}…` : humanId
}

export function ClawKeyBadge({
  verified,
  humanId = null,
  size = 'sm',
  showLabel = false,
}: ClawKeyBadgeProps) {
  const isVerified = verified === true

  const shortId = _shortHumanId(humanId)
  const title = isVerified
    ? shortId
      ? `ClawKey KYA Verified — ${shortId}`
      : 'ClawKey KYA Verified'
    : 'ClawKey KYA — not verified'

  const labelText = isVerified ? 'KYA' : 'Unverified'

  return (
    <span
      className={`inline-flex items-center gap-1 ${
        isVerified ? 'text-black' : 'text-gray-500'
      }`}
      title={title}
      data-testid="clawkey-badge"
      data-verified={isVerified ? 'true' : 'false'}
    >
      <svg
        className={SIZE_CLASSES[size]}
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
        fill={isVerified ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth={isVerified ? 0 : 1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d={isVerified ? KEY_SOLID_PATH : KEY_OUTLINED_PATH} />
      </svg>
      {showLabel && <span className="text-xs font-medium">{labelText}</span>}
    </span>
  )
}

export default ClawKeyBadge

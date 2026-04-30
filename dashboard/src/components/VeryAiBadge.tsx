/**
 * VeryAI Palm Verification Badge
 *
 * Mirrors the WorldIdBadge component shape and styling. Renders a small
 * palm icon — outlined for `palm_single`, filled for `palm_dual` (the
 * higher-trust dual-palm verification). Unknown / null levels render as
 * a muted gray outline.
 *
 * Sizes follow the WorldIdBadge canon (sm/md/lg). Color stays in the
 * project black/white/gray canon — never blue or emerald.
 */

interface VeryAiBadgeProps {
  level: string | null | undefined
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

const SIZE_CLASSES: Record<NonNullable<VeryAiBadgeProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}

const HAND_RAISED_PATH =
  'M10.05 4.575a1.575 1.575 0 1 0-3.15 0v3m3.15-3v-1.5a1.575 1.575 0 0 1 3.15 0v1.5m-3.15 0 .075 5.925m3.075.75V4.575m0 0a1.575 1.575 0 0 1 3.15 0V15M6.9 7.575a1.575 1.575 0 1 0-3.15 0v8.175a6.75 6.75 0 0 0 6.75 6.75h2.018a5.25 5.25 0 0 0 3.712-1.538l1.732-1.732a5.25 5.25 0 0 0 1.538-3.712l.003-2.024a.668.668 0 0 1 .198-.471 1.575 1.575 0 1 0-2.228-2.228 3.818 3.818 0 0 0-1.12 2.687M6.9 7.575V12m6.27 4.318A4.49 4.49 0 0 1 16.35 15'

const SOLID_HAND_PATH =
  'M11.45 1.5a3.075 3.075 0 0 0-3 2.4 3.075 3.075 0 0 0-4.275 4.4l.275.4v6.45a8.25 8.25 0 0 0 8.25 8.25h2.018a6.75 6.75 0 0 0 4.773-1.977l1.732-1.732a6.75 6.75 0 0 0 1.977-4.773l.003-2.024c0-.067.03-.13.075-.176a3.075 3.075 0 1 0-4.348-4.348 5.32 5.32 0 0 0-1.563 3.748l-.001.39V4.575a3.075 3.075 0 0 0-3.075-3.075h-1.84Z'

export function VeryAiBadge({
  level,
  size = 'sm',
  showLabel = false,
}: VeryAiBadgeProps) {
  const isVerified = level === 'palm_single' || level === 'palm_dual'
  const isDual = level === 'palm_dual'

  const title = isDual
    ? 'VeryAI Palm Dual Verified'
    : level === 'palm_single'
      ? 'VeryAI Palm Verified'
      : 'VeryAI Unverified'

  const labelText = isDual ? 'Palm 2×' : level === 'palm_single' ? 'Palm' : 'Unverified'

  return (
    <span
      className={`inline-flex items-center gap-1 ${
        isVerified ? 'text-black' : 'text-gray-500'
      }`}
      title={title}
      data-testid="veryai-badge"
      data-level={level ?? 'none'}
    >
      <svg
        className={SIZE_CLASSES[size]}
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
        fill={isDual ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth={isDual ? 0 : 1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d={isDual ? SOLID_HAND_PATH : HAND_RAISED_PATH} />
      </svg>
      {showLabel && <span className="text-xs font-medium">{labelText}</span>}
    </span>
  )
}

export default VeryAiBadge

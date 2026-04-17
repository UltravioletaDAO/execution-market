/**
 * VerificationBadges — row of 3-char monospace tokens that only render when
 * verification passed. We never show "failed" badges greyed out: absence is
 * the signal. Order is fixed so the visual rhythm stays consistent across
 * slides.
 */

import { memo } from 'react'
import type { VerificationBadges as VerificationBadgesData } from '../../../services/showcase'

interface VerificationBadgesProps {
  verification: VerificationBadgesData
}

const BADGES: ReadonlyArray<{
  key: keyof VerificationBadgesData
  label: string
  title: string
}> = [
  { key: 'gpsVerified', label: 'GPS', title: 'GPS location verified' },
  { key: 'exifVerified', label: 'EXIF', title: 'EXIF metadata verified' },
  { key: 'timestampVerified', label: 'TIME', title: 'Capture timestamp verified' },
  { key: 'worldIdVerified', label: 'ID', title: 'Human proof via World ID' },
]

export const VerificationBadges = memo(function VerificationBadges({
  verification,
}: VerificationBadgesProps) {
  const active = BADGES.filter((b) => verification[b.key])
  if (active.length === 0) return null

  return (
    <ul
      className="flex flex-wrap items-center gap-1.5"
      aria-label="Verification checks passed"
    >
      {active.map((b) => (
        <li
          key={b.key}
          title={b.title}
          className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
        >
          {b.label}
        </li>
      ))}
    </ul>
  )
})

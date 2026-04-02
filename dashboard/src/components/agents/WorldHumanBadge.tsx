/**
 * WorldHumanBadge - World AgentKit verified human badge
 *
 * Shows a green "Verified Human" badge when the executor has been
 * verified through World ID (AgentKit Track 1).
 */

import { memo } from 'react'
import { cn } from '../../lib/utils'

interface WorldHumanBadgeProps {
  /** World ID human verification token ID */
  worldHumanId: number | null | undefined
  className?: string
}

export const WorldHumanBadge = memo(function WorldHumanBadge({
  worldHumanId,
  className,
}: WorldHumanBadgeProps) {
  if (!worldHumanId || worldHumanId <= 0) return null

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-2xs font-medium',
        'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
        className
      )}
      title={`World ID Verified Human #${worldHumanId}`}
    >
      <svg
        className="w-3 h-3 text-green-600 dark:text-green-400"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>
      <span>Verified Human</span>
    </span>
  )
})

export default WorldHumanBadge

/**
 * ENSBadge - ENS name badge for agents and workers (execution-market.eth)
 *
 * Shows an indigo ENS badge when the executor has a resolved ENS name
 * (e.g., "vitalik.eth") or a claimed subname (e.g., "alice.execution-market.eth").
 * Links to the ENS app page for the name.
 */

import { memo } from 'react'
import { cn } from '../../lib/utils'

interface ENSBadgeProps {
  /** Resolved ENS name or claimed subname */
  ensName: string | null | undefined
  /** Optional: show compact or full badge */
  size?: 'sm' | 'md'
  className?: string
}

export const ENSBadge = memo(function ENSBadge({
  ensName,
  size = 'sm',
  className,
}: ENSBadgeProps) {
  if (!ensName) return null

  const href = `https://app.ens.domains/${ensName}`

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full font-medium no-underline',
        'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
        'hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors',
        size === 'sm' ? 'px-1.5 py-0.5 text-2xs' : 'px-2 py-0.5 text-xs',
        className
      )}
      title={`ENS: ${ensName}`}
    >
      {/* ENS diamond icon */}
      <svg
        className={cn(
          'text-indigo-600 dark:text-indigo-400',
          size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'
        )}
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M12 2L4 12l8 10 8-10L12 2zm0 3.5L17.5 12 12 18.5 6.5 12 12 5.5z" />
      </svg>
      <span>{ensName}</span>
    </a>
  )
})

export default ENSBadge

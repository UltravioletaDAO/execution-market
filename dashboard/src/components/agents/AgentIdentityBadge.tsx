/**
 * AgentIdentityBadge - ERC-8004 on-chain identity badge
 *
 * Shows a verified badge with the agent's on-chain ID when registered
 * in the ERC-8004 Identity Registry.
 */

import { memo } from 'react'
import { cn } from '../../lib/utils'

interface AgentIdentityBadgeProps {
  /** ERC-8004 agent token ID (e.g., 2106) */
  agentId: number
  /** Compact mode — just the ID number, no "Agent" prefix */
  compact?: boolean
  className?: string
}

/** Verified checkmark icon (inline SVG) */
function VerifiedIcon({ className }: { className?: string }) {
  return (
    <svg
      className={cn('w-3 h-3', className)}
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
  )
}

export const AgentIdentityBadge = memo(function AgentIdentityBadge({
  agentId,
  compact = false,
  className,
}: AgentIdentityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-2xs font-medium',
        'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
        className
      )}
      title={`ERC-8004 Agent #${agentId}`}
    >
      <VerifiedIcon className="text-blue-600 dark:text-blue-400" />
      <span>{compact ? `#${agentId}` : `Agent #${agentId}`}</span>
    </span>
  )
})

export default AgentIdentityBadge

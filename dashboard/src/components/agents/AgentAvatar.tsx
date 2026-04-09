/**
 * AgentAvatar - Reusable avatar component for agents
 *
 * Shows avatar_url if available, falls back to gradient identicon
 * generated from wallet address. Includes agent type indicator dot.
 */

import { memo, useMemo } from 'react'
import { cn } from '../../lib/utils'
import { safeSrc } from '../../lib/safeHref'
import type { AgentType } from '../../types/database'

interface AgentAvatarProps {
  /** Wallet address (used for identicon generation) */
  walletAddress: string
  /** Avatar image URL */
  avatarUrl?: string | null
  /** Display name (used for alt text and initial fallback) */
  displayName?: string | null
  /** Agent type for indicator dot */
  agentType?: AgentType
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Additional CSS classes */
  className?: string
  /** Show agent type indicator dot */
  showIndicator?: boolean
}

const SIZE_MAP = {
  sm: { container: 'w-8 h-8', text: 'text-xs', dot: 'w-2.5 h-2.5 -bottom-0.5 -right-0.5 border', ring: 'ring-1' },
  md: { container: 'w-12 h-12', text: 'text-sm', dot: 'w-3 h-3 -bottom-0.5 -right-0.5 border-2', ring: 'ring-2' },
  lg: { container: 'w-20 h-20', text: 'text-xl', dot: 'w-4 h-4 -bottom-0.5 -right-0.5 border-2', ring: 'ring-2' },
}

const AGENT_TYPE_COLORS: Record<AgentType, string> = {
  human: 'bg-green-500',
  ai: 'bg-blue-500',
  organization: 'bg-purple-500',
}

/**
 * Generate a deterministic gradient from a wallet address
 */
function walletToGradient(wallet: string): string {
  // Use wallet chars to derive hue values
  const chars = wallet.replace('0x', '').toLowerCase()
  const h1 = (parseInt(chars.slice(0, 4), 16) % 360)
  const h2 = (h1 + 40 + (parseInt(chars.slice(4, 8), 16) % 80)) % 360
  return `linear-gradient(135deg, hsl(${h1}, 70%, 55%), hsl(${h2}, 70%, 45%))`
}

/**
 * Get initial letter(s) for the avatar
 */
function getInitials(displayName: string | null | undefined, wallet: string): string {
  if (displayName) {
    const parts = displayName.trim().split(/\s+/)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return parts[0][0].toUpperCase()
  }
  // Use first 2 chars after 0x
  return wallet.slice(2, 4).toUpperCase()
}

export const AgentAvatar = memo(function AgentAvatar({
  walletAddress,
  avatarUrl,
  displayName,
  agentType = 'human',
  size = 'md',
  className,
  showIndicator = true,
}: AgentAvatarProps) {
  const sizeConfig = SIZE_MAP[size]
  const gradient = useMemo(() => walletToGradient(walletAddress), [walletAddress])
  const initials = useMemo(() => getInitials(displayName, walletAddress), [displayName, walletAddress])

  return (
    <div className={cn('relative inline-flex flex-shrink-0', className)}>
      {avatarUrl ? (
        <img
          src={safeSrc(avatarUrl)}
          alt={displayName || `Agent ${walletAddress.slice(0, 8)}`}
          className={cn(
            sizeConfig.container,
            'rounded-full object-cover',
            sizeConfig.ring,
            'ring-white dark:ring-gray-800'
          )}
          loading="lazy"
        />
      ) : (
        <div
          className={cn(
            sizeConfig.container,
            'rounded-full flex items-center justify-center text-white font-semibold',
            sizeConfig.text,
            sizeConfig.ring,
            'ring-white dark:ring-gray-800'
          )}
          style={{ background: gradient }}
          role="img"
          aria-label={displayName || `Agent ${walletAddress.slice(0, 8)}`}
        >
          {initials}
        </div>
      )}

      {/* Agent type indicator dot */}
      {showIndicator && (
        <span
          className={cn(
            'absolute rounded-full border-white dark:border-gray-800',
            sizeConfig.dot,
            AGENT_TYPE_COLORS[agentType]
          )}
          aria-hidden="true"
        />
      )}
    </div>
  )
})

export default AgentAvatar

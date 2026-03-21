/**
 * NetworkBadge Component
 * 
 * Displays a chain logo + name with optional token name.
 * Used across TaskFeedCard, TaskCard, and TaskDetail for consistent network branding.
 */

import { memo } from 'react'
import { cn } from '../../lib/utils'
import { NETWORK_BY_KEY, getNetworkLogo } from '../../config/networks'

export interface NetworkBadgeProps {
  /** Network key (e.g., 'base', 'ethereum') */
  network: string
  /** Optional token name to display after network (e.g., 'USDC') */
  token?: string
  /** Size variant */
  size?: 'sm' | 'md'
  /** Additional CSS classes */
  className?: string
}

export const NetworkBadge = memo(function NetworkBadge({
  network,
  token,
  size = 'md',
  className,
}: NetworkBadgeProps) {
  const networkInfo = NETWORK_BY_KEY[network] || NETWORK_BY_KEY[network.toLowerCase()]
  const networkName = networkInfo?.name || network
  const logoPath = getNetworkLogo(network)
  
  // Size variants
  const sizeClasses = {
    sm: {
      container: 'px-2 py-0.5 gap-1',
      logo: 'w-3 h-3',
      text: 'text-xs',
    },
    md: {
      container: 'px-2.5 py-1 gap-1.5',
      logo: 'w-4 h-4',
      text: 'text-sm',
    },
  }

  const variant = sizeClasses[size]

  return (
    <span
      className={cn(
        'inline-flex items-center whitespace-nowrap flex-shrink-0 rounded-full font-medium',
        'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
        'uppercase tracking-wide',
        variant.container,
        className
      )}
    >
      {/* Chain logo */}
      <img
        src={logoPath}
        alt={`${networkName} logo`}
        className={cn(variant.logo, 'rounded-full flex-shrink-0')}
        onError={(e) => {
          // Fallback: show first letter of network name
          const target = e.target as HTMLImageElement
          target.style.display = 'none'
          const fallback = target.nextElementSibling as HTMLSpanElement
          if (fallback) {
            fallback.style.display = 'inline-flex'
          }
        }}
      />
      
      {/* Fallback: first letter */}
      <span
        className={cn(
          'hidden items-center justify-center rounded-full bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 font-bold',
          variant.logo,
          size === 'sm' ? 'text-[8px]' : 'text-[10px]'
        )}
      >
        {networkName.charAt(0).toUpperCase()}
      </span>
      
      {/* Network name */}
      <span className={variant.text}>
        {networkName}
      </span>
      
      {/* Optional token */}
      {token && (
        <>
          <span className={cn('text-slate-400 dark:text-slate-500', variant.text)}>
            ·
          </span>
          <span className={variant.text}>
            {token}
          </span>
        </>
      )}
    </span>
  )
})

export default NetworkBadge
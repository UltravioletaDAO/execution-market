/**
 * XBadge - Social identity badge for X (Twitter)
 */

import { memo } from 'react'
import { cn } from '../../lib/utils'

interface XBadgeProps {
  handle: string
  verified?: boolean
  size?: 'sm' | 'md'
  className?: string
}

function XLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

function VerifiedCheck({ className }: { className?: string }) {
  return (
    <svg className={cn('flex-shrink-0', className)} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  )
}

export const XBadge = memo(function XBadge({
  handle,
  verified = false,
  size = 'md',
  className,
}: XBadgeProps) {
  const cleanHandle = handle.replace(/^@/, '')
  const displayHandle = handle.startsWith('@') ? handle : `@${handle}`
  const profileUrl = `https://x.com/${cleanHandle}`
  const isSmall = size === 'sm'

  return (
    <a
      href={profileUrl}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      className={cn(
        'inline-flex items-center gap-1 rounded-full transition-colors',
        'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100',
        isSmall ? 'px-1.5 py-0.5 text-2xs' : 'px-2 py-0.5 text-xs',
        'hover:bg-gray-100 dark:hover:bg-gray-700',
        className
      )}
      title={`${displayHandle} on X`}
    >
      <XLogo className={isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      <span className="truncate max-w-[120px]">{displayHandle}</span>
      {verified && (
        <VerifiedCheck
          className={cn(
            'text-blue-500 dark:text-blue-400',
            isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'
          )}
        />
      )}
    </a>
  )
})

export default XBadge

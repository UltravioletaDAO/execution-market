/**
 * Format a date string as a compact relative time.
 *
 * Returns: "<1m ago" / "Xm ago" / "Xh ago" / "Yesterday" / "X days ago" / actual date if >7d
 */
export function formatRelativeTime(date: string | Date): string {
  const target = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffMs = now.getTime() - target.getTime()

  if (diffMs < 0) return 'just now'

  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (minutes < 1) return '<1m ago'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days === 1) return 'Yesterday'
  if (days <= 7) return `${days}d ago`

  // >7 days — show actual date
  return target.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: target.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

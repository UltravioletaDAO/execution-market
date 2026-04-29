/**
 * WorkerReputationBadge: Inline badge showing a worker's reputation score.
 *
 * Displays as a compact pill with a star icon and numeric score.
 * Color-coded by tier: expert (emerald), trusted (blue), reliable (amber),
 * standard (gray), new (slate).
 */

import { useTranslation } from 'react-i18next'

interface WorkerReputationBadgeProps {
  score: number
  size?: 'sm' | 'md'
  showLabel?: boolean
}

function getTier(score: number): {
  key: string
  className: string
  starColor: string
} {
  if (score >= 90) {
    return {
      key: 'expert',
      className: 'bg-sky-50 text-sky-800 border border-sky-300',
      starColor: 'text-yellow-500',
    }
  }
  if (score >= 75) {
    return {
      key: 'trusted',
      className: 'bg-yellow-50 text-yellow-800 border border-yellow-400',
      starColor: 'text-yellow-500',
    }
  }
  if (score >= 50) {
    return {
      key: 'reliable',
      className: 'bg-slate-100 text-slate-700 border border-slate-300',
      starColor: 'text-yellow-500',
    }
  }
  if (score >= 25) {
    return {
      key: 'standard',
      className: 'bg-orange-50 text-orange-800 border border-orange-300',
      starColor: 'text-yellow-500',
    }
  }
  return {
    key: 'new',
    className: 'bg-zinc-100 text-zinc-600 border border-zinc-300',
    starColor: 'text-zinc-400',
  }
}

export function WorkerReputationBadge({
  score,
  size = 'sm',
  showLabel = false,
}: WorkerReputationBadgeProps) {
  const { t } = useTranslation()
  const tier = getTier(score)

  const sizeClasses =
    size === 'md'
      ? 'px-2.5 py-1 text-sm gap-1.5'
      : 'px-2 py-0.5 text-xs gap-1'

  const iconSize = size === 'md' ? 'w-4 h-4' : 'w-3 h-3'

  const tierLabel = `reputation.tiers.${tier.key}` as const
  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${tier.className} ${sizeClasses}`}
      title={t(tierLabel, tier.key)}
    >
      <svg
        className={`${iconSize} ${tier.starColor}`}
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
      </svg>
      {score}
      {showLabel && (
        <span className="opacity-75">
          {t(tierLabel, tier.key)}
        </span>
      )}
    </span>
  )
}

export default WorkerReputationBadge

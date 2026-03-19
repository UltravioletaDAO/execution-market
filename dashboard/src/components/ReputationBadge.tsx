/**
 * ReputationBadge: Tier-based reputation badge for workers/agents.
 *
 * Ported from em-mobile/components/ReputationBadge.tsx to React + Tailwind.
 * Tiers: Newcomer (0-19), Bronze (20-39), Silver (40-59), Gold (60-79), Legendary (80-100)
 */

import { useTranslation } from 'react-i18next'

interface ReputationBadgeProps {
  score: number
  size?: 'sm' | 'lg'
}

interface TierInfo {
  labelKey: string
  bgClass: string
  textClass: string
  borderClass: string
}

function getTier(score: number): TierInfo {
  if (score >= 80) {
    return {
      labelKey: 'reputation.tiers.legendary',
      bgClass: 'bg-purple-100',
      textClass: 'text-purple-700',
      borderClass: 'border-purple-300',
    }
  }
  if (score >= 60) {
    return {
      labelKey: 'reputation.tiers.gold',
      bgClass: 'bg-yellow-50',
      textClass: 'text-yellow-700',
      borderClass: 'border-yellow-300',
    }
  }
  if (score >= 40) {
    return {
      labelKey: 'reputation.tiers.silver',
      bgClass: 'bg-gray-100',
      textClass: 'text-gray-600',
      borderClass: 'border-gray-300',
    }
  }
  if (score >= 20) {
    return {
      labelKey: 'reputation.tiers.bronze',
      bgClass: 'bg-amber-50',
      textClass: 'text-amber-700',
      borderClass: 'border-amber-300',
    }
  }
  return {
    labelKey: 'reputation.tiers.newcomer',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-500',
    borderClass: 'border-slate-300',
  }
}

export function ReputationBadge({ score, size = 'sm' }: ReputationBadgeProps) {
  const { t } = useTranslation()
  const tier = getTier(score)

  const sizeClasses =
    size === 'lg'
      ? 'px-3 py-1.5 text-sm gap-2'
      : 'px-2 py-0.5 text-xs gap-1'

  const scoreSize = size === 'lg' ? 'text-lg font-bold' : 'text-xs font-semibold'

  return (
    <span
      className={`inline-flex items-center rounded-full border ${tier.bgClass} ${tier.textClass} ${tier.borderClass} ${sizeClasses}`}
      title={t(tier.labelKey, 'Reputation')}
    >
      <span className={scoreSize}>{Math.round(score)}</span>
      <span className="opacity-75">
        {t(tier.labelKey, 'Newcomer')}
      </span>
    </span>
  )
}

export default ReputationBadge

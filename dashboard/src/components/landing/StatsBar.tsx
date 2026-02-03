import { useTranslation } from 'react-i18next'

export function StatsBar() {
  const { t } = useTranslation()

  const stats = [
    { value: '17', label: t('landing.stats.mainnets') },
    { value: '$0.50', label: t('landing.stats.minBounty') },
    { value: t('landing.stats.instantValue'), label: t('landing.stats.payments') },
  ]

  return (
    <div className="flex items-center justify-center gap-8 md:gap-12 py-4">
      {stats.map((stat, i) => (
        <div key={i} className="text-center">
          <div className="text-xl md:text-2xl font-bold text-amber-500">{stat.value}</div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</div>
        </div>
      ))}
    </div>
  )
}

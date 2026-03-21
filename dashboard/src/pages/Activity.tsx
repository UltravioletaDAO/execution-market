/**
 * Activity Page (Protected)
 *
 * Full activity feed page — requires authentication.
 * Uses mode="authenticated" for realtime, filters, richer actor data.
 */

import { useTranslation } from 'react-i18next'
import { ActivityFeed } from '../components/feed'

export function Activity() {
  const { t } = useTranslation()

  return (
    <div className="max-w-3xl mx-auto px-4 w-full py-4">
        {/* Title */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {t('feed.pageTitle', 'Platform Activity')}
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {t('feed.pageSubtitle', 'Real-time activity across the Execution Market.')}
          </p>
        </div>

        {/* Feed — authenticated mode: realtime, filters, richer data */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4">
          <ActivityFeed mode="authenticated" />
        </div>
    </div>
  )
}

export default Activity

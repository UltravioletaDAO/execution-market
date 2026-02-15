/**
 * Activity Page (Protected)
 *
 * Full activity feed page — requires authentication.
 * Uses mode="authenticated" for realtime, filters, richer actor data.
 */

import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AppHeader } from '../components/layout/AppHeader'
import { AppFooter } from '../components/layout/AppFooter'
import { ActivityFeed } from '../components/feed'
import { useAuth } from '../context/AuthContext'
import { useCallback } from 'react'

export function Activity() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { openAuthModal } = useAuth()

  const handleConnectWallet = useCallback(() => {
    openAuthModal()
  }, [openAuthModal])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex flex-col">
      <AppHeader onConnectWallet={handleConnectWallet} />

      <main className="flex-1 max-w-3xl mx-auto px-4 w-full py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-6">
          <button
            onClick={() => navigate('/')}
            className="hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          >
            {t('nav.home', 'Home')}
          </button>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-slate-900 dark:text-slate-100 font-medium">
            {t('feed.pageTitle', 'Platform Activity')}
          </span>
        </nav>

        {/* Title */}
        <div className="mb-6">
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
      </main>

      <AppFooter />
    </div>
  )
}

export default Activity

// Execution Market: Profile Page Component
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { EarningsCard } from './EarningsCard'
import { ReputationCard } from './ReputationCard'
import { TaskHistory } from './TaskHistory'
import { WithdrawalForm } from './WithdrawalForm'
import { WorldIdVerification } from '../WorldIdVerification'
import { ENSLinkSection } from '../ENSLinkSection'
import { useEarnings, useReputation, useTaskHistory } from '../../hooks/useProfile'
import type { Executor } from '../../types/database'
import { safeSrc } from '../../lib/safeHref'

interface ProfilePageProps {
  executor: Executor
  onBack: () => void
  onEditProfile: () => void
  onLogout: () => void
}

export function ProfilePage({ executor, onBack, onEditProfile, onLogout }: ProfilePageProps) {
  const { t } = useTranslation()
  const [showWithdrawal, setShowWithdrawal] = useState(false)

  const { earnings, loading: earningsLoading, refetch: refetchEarnings } = useEarnings(executor.id)
  const { reputation, loading: reputationLoading } = useReputation(executor.id)
  const { history, loading: historyLoading, hasMore, loadMore } = useTaskHistory(executor.id)

  const handleWithdrawalSuccess = () => {
    setShowWithdrawal(false)
    refetchEarnings()
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          aria-label="Volver atras"
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-sm font-medium">{t('common.back', 'Back')}</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={onEditProfile}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            {t('profile.editProfile', 'Edit Profile')}
          </button>

          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {t('profile.logout', 'Cerrar Sesion')}
          </button>
        </div>
      </div>

      {/* Profile header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-center gap-4">
          {/* Avatar */}
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white text-xl font-bold shadow-lg flex-shrink-0">
            {executor.avatar_url ? (
              <img
                src={safeSrc(executor.avatar_url)}
                alt={executor.display_name || 'User'}
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              (executor.display_name || 'U')[0].toUpperCase()
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-gray-900 truncate">
              {executor.display_name || t('profile.anonymous', 'Anonymous User')}
            </h1>

            {executor.bio && (
              <p className="text-gray-600 text-sm mt-1 line-clamp-2">
                {executor.bio}
              </p>
            )}

            <div className="flex items-center gap-4 mt-2">
              {/* Location */}
              {(executor.location_city || executor.location_country) && (
                <div className="flex items-center gap-1 text-gray-500 text-sm">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>
                    {[executor.location_city, executor.location_country].filter(Boolean).join(', ')}
                  </span>
                </div>
              )}

              {/* Member since */}
              <div className="flex items-center gap-1 text-gray-500 text-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>
                  {t('profile.memberSince', 'Member since')} {new Date(executor.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Contact & wallet */}
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
          {/* Wallet */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              {t('profile.walletAddress', 'Wallet Address')}
            </div>
            <div className="flex items-center gap-2">
              <code className="text-sm font-mono text-gray-700 bg-gray-50 px-3 py-1 rounded">
                {executor.wallet_address.slice(0, 6)}...{executor.wallet_address.slice(-4)}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(executor.wallet_address)}
                className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                title={t('common.copy', 'Copy')}
                aria-label={t('common.copy', 'Copy wallet address')}
              >
                <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
              </button>
            </div>
          </div>

          {/* Email */}
          {executor.email && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span>{executor.email}</span>
            </div>
          )}

          {/* Phone */}
          {executor.phone && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <span>{executor.phone}</span>
            </div>
          )}
        </div>

        {/* Skills */}
        {executor.skills && executor.skills.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-sm text-gray-500 mb-2">
              {t('profile.skills', 'Skills')}
            </div>
            <div className="flex flex-wrap gap-2">
              {executor.skills.map(skill => (
                <span
                  key={skill}
                  className="px-3 py-1 bg-blue-100 text-blue-800 border border-blue-200 rounded-full text-sm"
                >
                  {skill.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Languages */}
        {executor.languages && executor.languages.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-sm text-gray-500 mb-2">
              {t('profile.languages', 'Languages')}
            </div>
            <div className="flex flex-wrap gap-2">
              {executor.languages.map(lang => (
                <span
                  key={lang}
                  className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-50 text-gray-700 border border-gray-200 rounded-full text-sm"
                >
                  <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                  {lang}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Identity: World ID + ENS side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-gray-900 font-semibold mb-3">
            {t('profile.humanVerification', 'Human Verification')}
          </h3>
          <WorldIdVerification />
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="text-gray-900 font-semibold mb-3">
            {t('profile.ensIdentity', 'ENS Identity')}
          </h3>
          <ENSLinkSection />
        </div>
      </div>

      {/* Earnings + Reputation side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <EarningsCard
          earnings={earnings}
          loading={earningsLoading}
          onWithdraw={() => setShowWithdrawal(true)}
        />

        <ReputationCard
          reputation={reputation}
          loading={reputationLoading}
        />
      </div>

      {/* Task history */}
      <TaskHistory
        history={history}
        loading={historyLoading}
        hasMore={hasMore}
        onLoadMore={loadMore}
      />

      {/* Withdrawal modal */}
      {showWithdrawal && (
        <WithdrawalForm
          executorId={executor.id}
          earnings={earnings}
          walletAddress={executor.wallet_address}
          onSuccess={handleWithdrawalSuccess}
          onCancel={() => setShowWithdrawal(false)}
        />
      )}
    </div>
  )
}

// Execution Market: Profile Page Component
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { EarningsCard } from './EarningsCard'
import { ReputationCard } from './ReputationCard'
import { TaskHistory } from './TaskHistory'
import { WithdrawalForm } from './WithdrawalForm'
import { useEarnings, useReputation, useTaskHistory } from '../../hooks/useProfile'
import type { Executor } from '../../types/database'

interface ProfilePageProps {
  executor: Executor
  onBack: () => void
  onEditProfile: () => void
}

export function ProfilePage({ executor, onBack, onEditProfile }: ProfilePageProps) {
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-sm font-medium">{t('common.back', 'Back')}</span>
        </button>

        <button
          onClick={onEditProfile}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          {t('profile.editProfile', 'Edit Profile')}
        </button>
      </div>

      {/* Profile header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-4">
          {/* Avatar */}
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white text-2xl font-bold shadow-lg">
            {executor.avatar_url ? (
              <img
                src={executor.avatar_url}
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

        {/* Wallet address */}
        <div className="mt-4 pt-4 border-t border-gray-100">
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
              >
                <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Roles/skills badges */}
        {executor.roles && executor.roles.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-sm text-gray-500 mb-2">
              {t('profile.skills', 'Skills & Roles')}
            </div>
            <div className="flex flex-wrap gap-2">
              {executor.roles.map(role => (
                <span
                  key={role}
                  className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm"
                >
                  {role}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Earnings card */}
      <EarningsCard
        earnings={earnings}
        loading={earningsLoading}
        onWithdraw={() => setShowWithdrawal(true)}
      />

      {/* Reputation card */}
      <ReputationCard
        reputation={reputation}
        loading={reputationLoading}
      />

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

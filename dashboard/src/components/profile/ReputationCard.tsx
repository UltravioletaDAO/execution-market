// Execution Market: Reputation Card Component
import { useTranslation } from 'react-i18next'
import type { ReputationData } from '../../hooks/useProfile'

interface ReputationCardProps {
  reputation: ReputationData | null
  loading: boolean
}

// Reputation tier based on score
function getReputationTier(score: number): { name: string; color: string; bgColor: string } {
  if (score >= 90) return { name: 'Expert', color: 'text-purple-600', bgColor: 'bg-purple-100' }
  if (score >= 75) return { name: 'Trusted', color: 'text-blue-600', bgColor: 'bg-blue-100' }
  if (score >= 60) return { name: 'Reliable', color: 'text-green-600', bgColor: 'bg-green-100' }
  if (score >= 40) return { name: 'Standard', color: 'text-gray-600', bgColor: 'bg-gray-100' }
  return { name: 'New', color: 'text-amber-600', bgColor: 'bg-amber-100' }
}

export function ReputationCard({ reputation, loading }: ReputationCardProps) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-20 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
        </div>
      </div>
    )
  }

  const totalTasks = reputation?.total_tasks || 0
  // Show 0 for new profiles with no tasks (Bayesian prior of 50 only meaningful after tasks)
  // Clamp to 0-100 range — scores above 100 are a backend bug, never display them
  const rawScore = totalTasks === 0 ? 0 : (reputation?.current_score ?? 0)
  const score = Math.min(Math.max(rawScore, 0), 100)
  const tier = getReputationTier(score)
  const approvalRate = reputation?.approval_rate || 0

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-gray-900 font-semibold">
          {t('profile.reputation', 'Reputation')}
        </h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${tier.bgColor} ${tier.color}`}>
          {tier.name}
        </span>
      </div>

      {/* Score display */}
      <div className="flex items-center justify-center mb-6">
        <div className="relative w-32 h-32">
          {/* Background circle */}
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="12"
              fill="none"
              className="text-gray-100"
            />
            {/* Progress circle */}
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="12"
              fill="none"
              strokeDasharray={`${(score / 100) * 352} 352`}
              strokeLinecap="round"
              className={
                score >= 75 ? 'text-green-500' :
                score >= 50 ? 'text-blue-500' :
                score >= 25 ? 'text-amber-500' :
                'text-red-500'
              }
            />
          </svg>
          {/* Score text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-gray-900">{score}</span>
            <span className="text-xs text-gray-500">/ 100</span>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center">
          <div className="text-2xl font-semibold text-gray-900">
            {reputation?.total_tasks || 0}
          </div>
          <div className="text-xs text-gray-500">
            {t('profile.totalTasks', 'Total')}
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-semibold text-green-600">
            {reputation?.approved_tasks || 0}
          </div>
          <div className="text-xs text-gray-500">
            {t('profile.approved', 'Approved')}
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-semibold text-red-600">
            {reputation?.rejected_tasks || 0}
          </div>
          <div className="text-xs text-gray-500">
            {t('profile.rejected', 'Rejected')}
          </div>
        </div>
      </div>

      {/* Approval rate bar */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-gray-600">
            {t('profile.approvalRate', 'Approval Rate')}
          </span>
          <span className="font-medium text-gray-900">
            {approvalRate.toFixed(1)}%
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              approvalRate >= 80 ? 'bg-green-500' :
              approvalRate >= 60 ? 'bg-blue-500' :
              approvalRate >= 40 ? 'bg-amber-500' :
              'bg-red-500'
            }`}
            style={{ width: `${approvalRate}%` }}
          />
        </div>
      </div>

      {/* Disputes warning */}
      {(reputation?.disputed_tasks || 0) > 0 && (
        <div className="mt-4 p-3 bg-amber-50 rounded-lg flex items-start gap-2">
          <svg className="w-5 h-5 text-amber-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div className="text-sm">
            <span className="font-medium text-amber-800">
              {reputation?.disputed_tasks} {t('profile.disputedTasks', 'disputed task(s)')}
            </span>
            <p className="text-amber-700 text-xs mt-0.5">
              {t('profile.disputeWarning', 'Disputes may affect your reputation score')}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

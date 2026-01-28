/**
 * DisputesPage - Page for viewing and managing disputes
 *
 * Features:
 * - List of disputes (as executor)
 * - Dispute detail view with timeline
 * - Evidence viewer
 * - Submit counter-evidence
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useDisputes, useDispute, type Dispute } from '../hooks/useDisputes'
import type { Executor } from '../types/database'

interface DisputesPageProps {
  executor: Executor
  onBack: () => void
}

// Format date for display
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Status badge component
function StatusBadge({ status }: { status: Dispute['status'] }) {
  const colors = {
    open: 'bg-yellow-100 text-yellow-800',
    under_review: 'bg-blue-100 text-blue-800',
    resolved: 'bg-green-100 text-green-800',
    escalated: 'bg-red-100 text-red-800',
  }

  const labels = {
    open: 'Abierto',
    under_review: 'En Revision',
    resolved: 'Resuelto',
    escalated: 'Escalado',
  }

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status]}`}>
      {labels[status]}
    </span>
  )
}

// Dispute list item
function DisputeListItem({
  dispute,
  onClick,
}: {
  dispute: Dispute
  onClick: () => void
}) {
  const { t } = useTranslation()

  return (
    <div
      onClick={onClick}
      className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 cursor-pointer transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-medium text-gray-900">
            {dispute.task?.title || t('disputes.unknownTask')}
          </h3>
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
            {dispute.reason}
          </p>
        </div>
        <StatusBadge status={dispute.status} />
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          ${dispute.task?.bounty_usd.toFixed(2)}
        </span>
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {formatDate(dispute.created_at)}
        </span>
      </div>
    </div>
  )
}

// Dispute detail view
function DisputeDetail({
  disputeId,
  onBack,
}: {
  disputeId: string
  onBack: () => void
}) {
  const { t } = useTranslation()
  const { dispute, loading, error, submitExecutorEvidence } = useDispute(disputeId)
  const [showEvidenceForm, setShowEvidenceForm] = useState(false)
  const [evidenceDescription, setEvidenceDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmitEvidence = async () => {
    if (!evidenceDescription.trim()) return

    setSubmitting(true)
    const result = await submitExecutorEvidence({
      description: evidenceDescription,
    })
    setSubmitting(false)

    if (result.success) {
      setShowEvidenceForm(false)
      setEvidenceDescription('')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !dispute) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error || t('disputes.notFound')}</p>
        <button onClick={onBack} className="mt-4 text-blue-600 hover:text-blue-700">
          {t('common.back')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-semibold text-gray-900">
            {t('disputes.detail')}
          </h1>
          <p className="text-sm text-gray-500">
            {dispute.task?.title}
          </p>
        </div>
        <StatusBadge status={dispute.status} />
      </div>

      {/* Task info card */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="font-medium text-gray-900 mb-2">
          {t('disputes.taskInfo')}
        </h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">{t('tasks.bounty')}:</span>
            <span className="ml-2 font-medium">${dispute.task?.bounty_usd.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-500">{t('tasks.category')}:</span>
            <span className="ml-2 font-medium">{dispute.task?.category}</span>
          </div>
        </div>
      </div>

      {/* Dispute reason */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="font-medium text-gray-900 mb-2">
          {t('disputes.reason')}
        </h2>
        <p className="text-gray-700">{dispute.reason}</p>
      </div>

      {/* Timeline */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="font-medium text-gray-900 mb-4">
          {t('disputes.timeline')}
        </h2>
        <div className="space-y-4">
          {/* Dispute created */}
          <div className="flex gap-3">
            <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">{t('disputes.opened')}</p>
              <p className="text-sm text-gray-500">{formatDate(dispute.created_at)}</p>
            </div>
          </div>

          {/* Agent evidence */}
          {dispute.agent_evidence && (
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{t('disputes.agentEvidence')}</p>
                <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm">
                  <pre className="whitespace-pre-wrap text-gray-700">
                    {JSON.stringify(dispute.agent_evidence, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Executor evidence */}
          {dispute.executor_evidence && (
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{t('disputes.yourEvidence')}</p>
                <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm">
                  <pre className="whitespace-pre-wrap text-gray-700">
                    {JSON.stringify(dispute.executor_evidence, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Resolution */}
          {dispute.resolution && (
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{t('disputes.resolved')}</p>
                <p className="text-sm text-gray-500">{formatDate(dispute.resolved_at!)}</p>
                <div className="mt-2 p-3 bg-green-50 rounded-lg text-sm text-green-800">
                  {dispute.resolution}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Submit evidence form */}
      {dispute.status === 'open' && !dispute.executor_evidence && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          {!showEvidenceForm ? (
            <button
              onClick={() => setShowEvidenceForm(true)}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('disputes.submitEvidence')}
            </button>
          ) : (
            <div className="space-y-4">
              <h2 className="font-medium text-gray-900">
                {t('disputes.submitEvidence')}
              </h2>
              <textarea
                value={evidenceDescription}
                onChange={(e) => setEvidenceDescription(e.target.value)}
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                placeholder={t('disputes.evidencePlaceholder')}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => setShowEvidenceForm(false)}
                  className="flex-1 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={handleSubmitEvidence}
                  disabled={submitting || !evidenceDescription.trim()}
                  className="flex-1 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {submitting ? t('common.submitting') : t('common.submit')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Original submission evidence */}
      {dispute.submission?.evidence && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h2 className="font-medium text-gray-900 mb-2">
            {t('disputes.originalSubmission')}
          </h2>
          <p className="text-sm text-gray-500 mb-3">
            {t('disputes.submittedOn')} {formatDate(dispute.submission.submitted_at)}
          </p>
          <div className="p-3 bg-gray-50 rounded-lg text-sm">
            <pre className="whitespace-pre-wrap text-gray-700">
              {JSON.stringify(dispute.submission.evidence, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

// Main disputes page
export function DisputesPage({ executor, onBack }: DisputesPageProps) {
  const { t } = useTranslation()
  const [selectedDispute, setSelectedDispute] = useState<string | null>(null)

  const { disputes, loading, error, refetch } = useDisputes({
    executorId: executor.id,
  })

  const handleDisputeClick = useCallback((dispute: Dispute) => {
    setSelectedDispute(dispute.id)
  }, [])

  const handleBackFromDetail = useCallback(() => {
    setSelectedDispute(null)
    refetch()
  }, [refetch])

  // Show detail view if dispute selected
  if (selectedDispute) {
    return (
      <DisputeDetail
        disputeId={selectedDispute}
        onBack={handleBackFromDetail}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-xl font-semibold text-gray-900">
          {t('disputes.title', 'Mis Disputas')}
        </h1>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-center py-12">
          <p className="text-red-600">{error}</p>
          <button onClick={refetch} className="mt-4 text-blue-600 hover:text-blue-700">
            {t('common.retry')}
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && disputes.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="font-medium text-gray-900">
            {t('disputes.empty', 'Sin Disputas')}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {t('disputes.emptyDescription', 'No tienes disputas activas')}
          </p>
        </div>
      )}

      {/* Disputes list */}
      {!loading && !error && disputes.length > 0 && (
        <div className="space-y-3">
          {disputes.map((dispute) => (
            <DisputeListItem
              key={dispute.id}
              dispute={dispute}
              onClick={() => handleDisputeClick(dispute)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default DisputesPage

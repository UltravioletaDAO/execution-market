// Execution Market: Task Detail Component
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import { useTaskPayment } from '../hooks/useTaskPayment'
import type { Task, TaskCategory, Executor, Submission } from '../types/database'
import { CATEGORY_ICONS } from '../constants/categories'
import { getNetworkDisplayName } from '../utils/blockchain'
import { NetworkBadge } from './ui/NetworkBadge'
import { useAgentReputation, getReputationTier, getTierColor } from '../hooks/useAgentReputation'
import { AgentStandardCard } from './agents/AgentStandardCard'
import { EvidenceVerificationPanel } from './EvidenceVerificationPanel'
import { TaskLifecycleTimeline } from './TaskLifecycleTimeline'
import { TaskRatings } from './TaskRatings'
import { EvidenceModal } from './EvidenceModal'
import { getStatusBadgeClass } from '../styles/theme'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

interface TaskDetailProps {
  task: Task
  currentExecutor: Executor | null
  onBack: () => void
  onAccept?: () => void
}

// Category labels resolved via i18n (see tasks.categories in locale files)
const CATEGORY_KEYS: Record<TaskCategory, string> = {
  physical_presence: 'physical_presence',
  knowledge_access: 'knowledge_access',
  human_authority: 'human_authority',
  simple_action: 'simple_action',
  digital_physical: 'digital_physical',
  data_processing: 'data_processing',
  research: 'research',
  content_generation: 'content_generation',
  code_execution: 'code_execution',
  api_integration: 'api_integration',
  multi_step_workflow: 'multi_step_workflow',
}

// Evidence type labels resolved via i18n (see tasks.evidenceTypes in locale files)
const EVIDENCE_TYPE_KEYS: Record<string, string> = {
  photo: 'photo',
  photo_geo: 'photo_geo',
  video: 'video',
  document: 'document',
  receipt: 'receipt',
  signature: 'signature',
  notarized: 'notarized',
  timestamp_proof: 'timestamp_proof',
  text_response: 'text_response',
  measurement: 'measurement',
  screenshot: 'screenshot',
}

/** Map task status (snake_case) to i18n key under agentDashboard.status */
const STATUS_I18N_KEY: Record<string, string> = {
  published: 'agentDashboard.status.published',
  accepted: 'agentDashboard.status.accepted',
  in_progress: 'agentDashboard.status.inProgress',
  submitted: 'agentDashboard.status.submitted',
  verifying: 'agentDashboard.status.verifying',
  completed: 'agentDashboard.status.completed',
  disputed: 'agentDashboard.status.disputed',
  expired: 'agentDashboard.status.expired',
  cancelled: 'agentDashboard.status.cancelled',
}

/** English fallback labels for task statuses */
const STATUS_FALLBACK: Record<string, string> = {
  published: 'Published',
  accepted: 'Accepted',
  in_progress: 'In Progress',
  submitted: 'Submitted',
  verifying: 'Verifying',
  completed: 'Completed',
  disputed: 'Disputed',
  expired: 'Expired',
  cancelled: 'Cancelled',
}

function formatDeadline(deadline: string, lang = 'en'): string {
  const localeMap: Record<string, string> = { en: 'en-US', es: 'es-MX', pt: 'pt-BR' }
  const date = new Date(deadline)
  return date.toLocaleDateString(localeMap[lang] || lang, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatBounty(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}

/** Resolve evidence file URL — handles Supabase storage paths and full URLs */
function resolveEvidenceUrl(fileUrl: string): string {
  if (!fileUrl) return ''
  // Already a full URL (S3/CloudFront or Supabase public URL)
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) {
    return fileUrl
  }
  // Relative path — Supabase storage bucket
  return `${SUPABASE_URL}/storage/v1/object/public/evidence/${fileUrl}`
}

export function TaskDetail({
  task,
  currentExecutor,
  onBack,
  onAccept,
}: TaskDetailProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [accepting, setAccepting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [zoomImage, setZoomImage] = useState<{ url: string; alt: string } | null>(null)

  const hasEscrowContext = Boolean(task.escrow_tx || task.escrow_id)
  const showPayment =
    hasEscrowContext ||
    task.status === 'completed' ||
    task.status === 'submitted' ||
    task.status === 'expired' ||
    task.status === 'cancelled'
  const { payment, loading: paymentLoading } = useTaskPayment(showPayment ? task.id : null)
  const { data: agentReputation } = useAgentReputation()

  // Fetch submissions for this task
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [submissionsLoading, setSubmissionsLoading] = useState(false)

  const fetchSubmissions = useCallback(async () => {
    if (!task.id) return
    // Only fetch when task has been assigned or beyond
    if (!['accepted', 'in_progress', 'submitted', 'verifying', 'completed', 'disputed'].includes(task.status)) return

    setSubmissionsLoading(true)
    try {
      const { data, error: fetchErr } = await supabase
        .from('submissions')
        .select('*')
        .eq('task_id', task.id)
        .order('submitted_at', { ascending: false })

      if (!fetchErr && data) {
        setSubmissions(data)
      }
    } catch {
      // Silently fail — submissions display is supplementary
    } finally {
      setSubmissionsLoading(false)
    }
  }, [task.id, task.status])

  useEffect(() => {
    fetchSubmissions()
  }, [fetchSubmissions])

  const canAccept =
    task.status === 'published' &&
    currentExecutor &&
    currentExecutor.reputation_score >= task.min_reputation

  const handleAccept = async () => {
    if (!currentExecutor) return

    setAccepting(true)
    setError(null)

    try {
      // Get fresh session to avoid stale token / RLS mismatch
      const { data: { session: currentSession } } = await supabase.auth.getSession()

      const headers: Record<string, string> = {
        apikey: SUPABASE_KEY,
        'Content-Type': 'application/json',
      }

      if (currentSession?.access_token) {
        headers['Authorization'] = `Bearer ${currentSession.access_token}`
      }

      // Use the apply_to_task RPC for atomic acceptance
      const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/apply_to_task`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          p_task_id: task.id,
          p_executor_id: currentExecutor.id,
          p_message: null,
        }),
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `Failed: ${response.status}`)
      }

      const result = await response.json()
      if (result && result.success === false) {
        throw new Error(result.error || t('taskDetail.taskUnavailable', 'Task is no longer available'))
      }

      onAccept?.()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t('taskDetail.acceptError', 'Could not accept the task. Try again.')
      )
    } finally {
      setAccepting(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onBack}
          aria-label={t('taskDetail.backToList', 'Back to task list')}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          {t('taskDetail.backToList', 'Back to list')}
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{CATEGORY_ICONS[task.category]}</span>
              <span className="text-sm text-gray-500 uppercase tracking-wide">
                {t(`tasks.categories.${CATEGORY_KEYS[task.category]}`, task.category)}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-gray-900">{task.title}</h1>
              <span
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                style={task.status === 'completed'
                  ? { backgroundColor: '#16a34a', color: '#ffffff' }
                  : task.status === 'cancelled' || task.status === 'expired'
                  ? { backgroundColor: '#e5e7eb', color: '#6b7280' }
                  : task.status === 'disputed'
                  ? { backgroundColor: '#fecaca', color: '#991b1b' }
                  : { backgroundColor: '#e0e7ff', color: '#3730a3' }}
              >
                {t(STATUS_I18N_KEY[task.status] || `agentDashboard.status.${task.status}`, STATUS_FALLBACK[task.status] || task.status)}
              </span>
            </div>
          </div>

          <div className="text-right">
            <div className="text-2xl font-bold text-green-600">
              {formatBounty(task.bounty_usd)}
            </div>
            <div className="flex items-center justify-end gap-1 mt-1">
              {task.payment_token && task.payment_network ? (
                <NetworkBadge
                  network={task.payment_network}
                  token={task.payment_token}
                  size="sm"
                />
              ) : (
                <div className="text-xs text-gray-400">
                  {task.payment_token}{task.payment_network ? ` on ${getNetworkDisplayName(task.payment_network)}` : ''}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Instructions */}
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            {t('tasks.instructions')}
          </h2>
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-gray-700 bg-gray-50 p-4 rounded-lg">
              {task.instructions}
            </pre>
          </div>
        </section>

        {/* Evidence requirements */}
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            {t('tasks.requirements', 'Required Evidence')}
          </h2>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {task.evidence_schema.required.map((type) => (
                <span
                  key={type}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-700 text-sm rounded-full"
                >
                  <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                  {t(`tasks.evidenceTypes.${EVIDENCE_TYPE_KEYS[type] || type}`, type)}
                </span>
              ))}
            </div>
            {task.evidence_schema.optional && task.evidence_schema.optional.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {task.evidence_schema.optional.map((type) => (
                  <span
                    key={type}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 text-gray-600 text-sm rounded-full"
                  >
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full" />
                    {t(`tasks.evidenceTypes.${EVIDENCE_TYPE_KEYS[type] || type}`, type)} ({t('common.optional', 'optional')})
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Location */}
        {task.location_hint && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('tasks.location')}
            </h2>
            <div className="flex items-center gap-2 text-gray-700">
              <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                  clipRule="evenodd"
                />
              </svg>
              <span>{task.location_hint}</span>
              {task.location_radius_km && (
                <span className="text-sm text-gray-500">
                  ({t('taskDetail.radius', 'radius')}: {task.location_radius_km} km)
                </span>
              )}
            </div>
          </section>
        )}

        {/* Deadline */}
        <section>
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            {t('tasks.deadline')}
          </h2>
          <div className="flex items-center gap-2 text-gray-700">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{formatDeadline(task.deadline)}</span>
          </div>
        </section>

        {/* Requirements */}
        {(task.min_reputation > 0 || task.required_roles.length > 0) && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('tasks.requirements')}
            </h2>
            <ul className="space-y-2">
              {task.min_reputation > 0 && (
                <li className="flex items-center gap-2 text-gray-700">
                  <svg className="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span>{t('tasks.minReputation')}: {task.min_reputation}</span>
                  {currentExecutor && (
                    <span
                      className={`text-sm ${
                        currentExecutor.reputation_score >= task.min_reputation
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      ({t('taskDetail.yours', 'yours')}: {currentExecutor.reputation_score})
                    </span>
                  )}
                </li>
              )}
              {task.required_roles.map((role) => (
                <li key={role} className="flex items-center gap-2 text-gray-700">
                  <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>{t('taskDetail.requiredRole', 'Required role')}: {role}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Posted by - Agent Card */}
        <section>
          <AgentStandardCard
            walletAddress={task.agent_id}
            label={t('tasks.postedBy', 'Posted by')}
          />
        </section>

        {/* Accepted by - Worker Card (if assigned) */}
        {task.executor_id && (
          <section>
            <AgentStandardCard
              walletAddress={task.executor_id}
              label={t('tasks.acceptedBy', 'Accepted by')}
            />
          </section>
        )}

        {/* Task Lifecycle Timeline — unified section with inline payment info */}
        {(task.executor_id || task.escrow_tx || ['accepted', 'in_progress', 'submitted', 'verifying', 'completed', 'expired', 'cancelled', 'disputed'].includes(task.status)) && (
          <TaskLifecycleTimeline
            task={task}
            submissions={submissions}
            payment={payment}
            paymentLoading={paymentLoading}
          />
        )}

        {/* Submissions / Evidence — after escrow timeline */}
        {submissions.length > 0 && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('tasks.submissions', 'Evidence Submitted')}
            </h2>
            <div className="space-y-3">
              {submissions.map((sub) => (
                <div key={sub.id} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  {/* Status badge */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-500">
                      {new Date(sub.submitted_at).toLocaleString()}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      sub.agent_verdict === 'approved'
                        ? 'bg-green-100 text-green-700'
                        : sub.agent_verdict === 'rejected'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {sub.agent_verdict === 'approved'
                        ? t('submission.approved', 'Approved')
                        : sub.agent_verdict === 'rejected'
                        ? t('submission.rejected', 'Rejected')
                        : t('submission.pending', 'Pending review')}
                    </span>
                  </div>

                  {/* Evidence content — smart rendering */}
                  {sub.evidence && typeof sub.evidence === 'object' && (
                    <div className="space-y-4">
                      {Object.entries(sub.evidence).map(([key, value]) => {
                        const ev = value as Record<string, unknown> | string | null
                        // Evidence object with fileUrl (e.g. {type, fileUrl, filename, metadata})
                        if (ev && typeof ev === 'object' && 'fileUrl' in ev) {
                          const fileUrl = resolveEvidenceUrl(String(ev.fileUrl || ''))
                          const filename = String(ev.filename || '')
                          const evType = String(ev.type || key)
                          const metadata = ev.metadata as Record<string, unknown> | undefined
                          const isImage = fileUrl.match(/\.(jpg|jpeg|png|gif|webp)$/i) || evType === 'screenshot' || evType === 'photo' || evType === 'photo_geo'

                          return (
                            <div key={key}>
                              <span className="text-xs font-semibold text-gray-600 uppercase">{evType.replace(/_/g, ' ')}</span>
                              {/* Show the image */}
                              {isImage && fileUrl && (
                                <button
                                  type="button"
                                  onClick={() => setZoomImage({ url: fileUrl, alt: filename || evType })}
                                  className="block mt-2 cursor-zoom-in w-full"
                                >
                                  <img
                                    src={fileUrl}
                                    alt={filename || evType}
                                    className="rounded-lg max-h-72 w-full object-contain border border-gray-200 bg-white"
                                  />
                                </button>
                              )}
                              {/* Non-image file link */}
                              {!isImage && fileUrl && (
                                <a href={fileUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm block mt-1">
                                  {filename || 'View file'}
                                </a>
                              )}
                              {/* Metadata as clean key-value pairs */}
                              {metadata && Object.keys(metadata).length > 0 && (
                                <div className="mt-2 space-y-2">
                                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                                    {filename && (
                                      <>
                                        <span className="text-gray-400">{t('submission.filename', 'File')}</span>
                                        <span className="text-gray-600 truncate">{filename}</span>
                                      </>
                                    )}
                                    {Object.entries(metadata).map(([mk, mv]) => {
                                      // Hide internal fields
                                      if (['backend', 'storagePath', 'nonce', 'storage_path'].includes(mk)) return null
                                      // Nested objects rendered separately below
                                      if (typeof mv === 'object' && mv !== null) return null
                                      return (
                                        <span key={mk} className="contents">
                                          <span className="text-gray-400">
                                            {mk === 'size' ? t('submission.fileSize', 'Size')
                                              : mk === 'checksum' ? 'Hash'
                                              : mk.replace(/_/g, ' ')}
                                          </span>
                                          <span className="text-gray-600 truncate flex items-center gap-1">
                                            {mk === 'size' && typeof mv === 'number'
                                              ? mv > 1048576 ? `${(mv / 1048576).toFixed(1)} MB` : `${(mv / 1024).toFixed(0)} KB`
                                              : mk === 'checksum' && typeof mv === 'string' && mv.length > 16
                                              ? <>{mv.slice(0, 16)}...<button type="button" title="Copy hash" className="ml-1 text-gray-400 hover:text-gray-600" onClick={() => navigator.clipboard.writeText(String(mv))}><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button></>
                                              : String(mv)}
                                          </span>
                                        </span>
                                      )
                                    })}
                                  </div>
                                  {/* Nested objects: forensic, etc. (ai_verification hidden — shown via EvidenceVerificationPanel) */}
                                  {Object.entries(metadata).map(([mk, mv]) => {
                                    if (typeof mv !== 'object' || mv === null) return null
                                    if (mk === 'ai_verification') return null
                                    const obj = mv as Record<string, unknown>

                                    if (mk === 'forensic') {
                                      const device = obj.device as Record<string, string> | string | undefined
                                      const parsedDevice = typeof device === 'string'
                                        ? (() => { try { return JSON.parse(device) as Record<string, string> } catch { return null } })()
                                        : device && typeof device === 'object' ? device : null
                                      const platform = parsedDevice?.platform || ''
                                      const rawSource = String(obj.source ?? 'unknown')
                                      const derivedSource = rawSource !== 'unknown' ? rawSource
                                        : /iphone|ipad/i.test(platform) ? 'iOS'
                                        : /android/i.test(platform) ? 'Android'
                                        : /win/i.test(platform) ? 'Windows'
                                        : /mac/i.test(platform) ? 'macOS'
                                        : /linux/i.test(platform) ? 'Linux'
                                        : 'unknown'

                                      return (
                                        <div key={mk} className="bg-white rounded p-2 border border-gray-100">
                                          <span className="text-xs font-medium text-gray-500 uppercase">{mk}</span>
                                          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1 text-xs">
                                            {parsedDevice && Object.entries(parsedDevice).map(([dk, dv]) => (
                                              <span key={dk} className="contents">
                                                <span className="text-gray-400">{dk === 'userAgent' ? 'User Agent' : dk.replace(/_/g, ' ')}</span>
                                                <span className="text-gray-600 break-all">{String(dv)}</span>
                                              </span>
                                            ))}
                                            <span className="contents">
                                              <span className="text-gray-400">source</span>
                                              <span className="text-gray-600">{derivedSource}</span>
                                            </span>
                                            {Object.entries(obj).map(([nk, nv]) => {
                                              if (nk === 'device' || nk === 'source') return null
                                              if (typeof nv === 'object' && nv !== null) {
                                                return Object.entries(nv as Record<string, unknown>).map(([gk, gv]) => (
                                                  <span key={`${nk}.${gk}`} className="contents">
                                                    <span className="text-gray-400">{gk.replace(/_/g, ' ')}</span>
                                                    <span className="text-gray-600 truncate">
                                                      {typeof gv === 'number' ? (gk === 'timestamp' ? new Date(gv).toLocaleString() : String(Math.round(gv * 1000) / 1000)) : String(gv ?? '')}
                                                    </span>
                                                  </span>
                                                ))
                                              }
                                              return (
                                                <span key={nk} className="contents">
                                                  <span className="text-gray-400">{nk.replace(/_/g, ' ')}</span>
                                                  <span className="text-gray-600 truncate">{String(nv ?? '')}</span>
                                                </span>
                                              )
                                            })}
                                          </div>
                                        </div>
                                      )
                                    }

                                    return (
                                      <div key={mk} className="bg-white rounded p-2 border border-gray-100">
                                        <span className="text-xs font-medium text-gray-500 uppercase">{mk.replace(/_/g, ' ')}</span>
                                        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1 text-xs">
                                          {Object.entries(obj).map(([nk, nv]) => (
                                            <span key={nk} className="contents">
                                              <span className="text-gray-400">{nk.replace(/_/g, ' ')}</span>
                                              <span className="text-gray-600 truncate">
                                                {typeof nv === 'boolean' ? (nv ? t('common.yes', 'Yes') : t('common.no', 'No'))
                                                  : typeof nv === 'number' ? (nk.includes('score') ? `${Math.round(nv * 100)}%` : String(nv))
                                                  : typeof nv === 'string' && nv.length > 32 ? `${nv.slice(0, 32)}...`
                                                  : typeof nv === 'object' && nv !== null ? JSON.stringify(nv)
                                                  : String(nv ?? '')}
                                              </span>
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              )}
                            </div>
                          )
                        }

                        // Plain URL string
                        if (typeof ev === 'string' && (ev.startsWith('http://') || ev.startsWith('https://'))) {
                          const isImg = ev.match(/\.(jpg|jpeg|png|gif|webp)$/i)
                          return (
                            <div key={key}>
                              <span className="text-xs font-semibold text-gray-600 uppercase">{key.replace(/_/g, ' ')}</span>
                              {isImg ? (
                                <button
                                  type="button"
                                  onClick={() => setZoomImage({ url: ev, alt: key })}
                                  className="block mt-2 cursor-zoom-in w-full"
                                >
                                  <img src={ev} alt={key} className="rounded-lg max-h-72 w-full object-contain border border-gray-200 bg-white" />
                                </button>
                              ) : (
                                <a href={ev} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm block mt-1">{ev}</a>
                              )}
                            </div>
                          )
                        }

                        // Plain text or other value
                        if (ev !== null && ev !== undefined) {
                          return (
                            <div key={key}>
                              <span className="text-xs font-semibold text-gray-600 uppercase">{key.replace(/_/g, ' ')}</span>
                              <p className="text-sm text-gray-700 mt-1">{typeof ev === 'object' ? JSON.stringify(ev) : String(ev)}</p>
                            </div>
                          )
                        }

                        return null
                      })}
                    </div>
                  )}

                  {/* Evidence files (S3/CDN direct links) */}
                  {sub.evidence_files && sub.evidence_files.length > 0 && (
                    <div className="mt-3">
                      <div className="grid grid-cols-2 gap-2">
                        {sub.evidence_files.map((url, i) => (
                          url.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                            <button
                              key={i}
                              type="button"
                              onClick={() => setZoomImage({ url, alt: `Evidence ${i + 1}` })}
                              className="cursor-zoom-in"
                            >
                              <img src={url} alt={`Evidence ${i + 1}`} className="rounded-lg max-h-48 object-contain border border-gray-200 bg-white" />
                            </button>
                          ) : (
                            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm">
                              {t('submission.file', 'File')} {i + 1}
                            </a>
                          )
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Auto-check verification results */}
                  {sub.auto_check_details && (
                    <div className="mt-3">
                      <EvidenceVerificationPanel details={sub.auto_check_details} />
                    </div>
                  )}

                  {/* Agent notes — italic quote block */}
                  {sub.agent_notes && (
                    <div className="mt-3 border-l-4 border-blue-300 bg-blue-50 rounded-r-lg px-4 py-3">
                      <span className="text-xs font-medium text-blue-600 block mb-1">{t('submission.agentNotes', 'Agent notes')}</span>
                      <p className="text-sm text-blue-800 italic">{sub.agent_notes}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Ratings — completed tasks only */}
        {task.status === 'completed' && (
          <TaskRatings
            taskId={task.id}
            executorId={currentExecutor?.id === task.executor_id ? currentExecutor.id : undefined}
            paymentNetwork={task.payment_network}
            taskTitle={task.title}
            agentId={task.erc8004_agent_id ? Number(task.erc8004_agent_id) : 2106}
            agentName={task.agent_name ?? undefined}
          />
        )}

        {/* Submissions loading state */}
        {submissionsLoading && ['accepted', 'in_progress', 'submitted', 'verifying', 'completed'].includes(task.status) && (
          <section>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
              {t('tasks.submissions', 'Evidence Submitted')}
            </h2>
            <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
              <div className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
              {t('common.loading', 'Loading...')}
            </div>
          </section>
        )}
      </div>

      {/* Evidence Zoom Modal */}
      {zoomImage && (
        <EvidenceModal
          imageUrl={zoomImage.url}
          alt={zoomImage.alt}
          onClose={() => setZoomImage(null)}
        />
      )}


      {/* Actions */}
      {task.status === 'published' && (
        <div className="p-4 bg-gray-50 border-t border-gray-200">
          {error && (
            <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm text-red-700">{error}</p>
                  <button
                    onClick={() => setError(null)}
                    className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                  >
                    {t('common.dismiss')}
                  </button>
                </div>
              </div>
            </div>
          )}

          {!currentExecutor ? (
            <div className="text-center">
              <p className="text-gray-600 mb-2">{t('taskDetail.loginToAccept', 'Sign in to accept this task')}</p>
              <button
                onClick={() => navigate('/')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('auth.signIn')}
              </button>
            </div>
          ) : !canAccept ? (
            <div className="text-center">
              <p className="text-amber-600">
                {t('taskDetail.requirementsNotMet', 'You do not meet the requirements for this task')}
              </p>
            </div>
          ) : (
            <button
              onClick={handleAccept}
              disabled={accepting}
              className="w-full py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {accepting ? t('taskDetail.accepting', 'Accepting...') : `${t('tasks.acceptTask')} - ${formatBounty(task.bounty_usd)}`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

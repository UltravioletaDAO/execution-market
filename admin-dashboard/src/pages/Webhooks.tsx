/**
 * Webhooks Management Page
 *
 * Lists all registered webhooks, allows registration, editing, pausing,
 * deleting, secret rotation, and test delivery.
 *
 * NOTE: The backend webhook endpoints (/api/v1/webhooks/) use agent API key
 * auth (verify_api_key). The admin dashboard sends X-Admin-Key. If the backend
 * does not yet have an admin-level webhook listing route, requests may 401.
 * An admin webhook proxy or dedicated /api/v1/admin/webhooks endpoint will be
 * needed on the backend side to bridge this gap.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { adminGet, adminPost, adminPut, adminFetch } from '../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WebhookResponse {
  webhook_id: string
  owner_id: string
  url: string
  events: string[]
  description: string
  status: string
  created_at: string
  updated_at: string
  last_triggered_at: string | null
  failure_count: number
  total_deliveries: number
  successful_deliveries: number
}

interface WebhookCreateResponse extends WebhookResponse {
  secret: string
}

interface RotateSecretResponse {
  webhook_id: string
  secret: string
}

interface TestResult {
  webhook_id: string
  test_event_id?: string
  delivered: boolean
  error?: string
}

interface WebhooksProps {
  adminKey: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_PREFIX = '/api/v1/webhooks'

/** All event types from the backend WebhookEventType enum. */
const ALL_EVENT_TYPES = [
  'task.created',
  'task.updated',
  'task.assigned',
  'task.started',
  'task.submitted',
  'task.completed',
  'task.expired',
  'task.cancelled',
  'submission.received',
  'submission.approved',
  'submission.rejected',
  'submission.revision_requested',
  'payment.escrowed',
  'payment.released',
  'payment.partial_released',
  'payment.refunded',
  'payment.failed',
  'dispute.opened',
  'dispute.evidence_submitted',
  'dispute.resolved',
  'dispute.escalated',
  'worker.applied',
  'worker.accepted',
  'worker.rejected',
  'reputation.updated',
  'webhook.test',
] as const

type EventType = (typeof ALL_EVENT_TYPES)[number]

/** Color map for event category badges. */
function eventColor(event: string): string {
  if (event.startsWith('task.')) return 'bg-blue-600/20 text-blue-400 border-blue-500/30'
  if (event.startsWith('submission.')) return 'bg-purple-600/20 text-purple-400 border-purple-500/30'
  if (event.startsWith('payment.')) return 'bg-emerald-600/20 text-emerald-400 border-emerald-500/30'
  if (event.startsWith('dispute.')) return 'bg-orange-600/20 text-orange-400 border-orange-500/30'
  if (event.startsWith('worker.')) return 'bg-cyan-600/20 text-cyan-400 border-cyan-500/30'
  if (event.startsWith('reputation.')) return 'bg-yellow-600/20 text-yellow-400 border-yellow-500/30'
  return 'bg-gray-600/20 text-gray-400 border-gray-500/30'
}

function statusBadge(status: string): { bg: string; label: string } {
  switch (status) {
    case 'active':
      return { bg: 'bg-green-600/20 text-green-400 border border-green-500/30', label: 'Active' }
    case 'paused':
      return { bg: 'bg-yellow-600/20 text-yellow-400 border border-yellow-500/30', label: 'Paused' }
    case 'disabled':
      return { bg: 'bg-red-600/20 text-red-400 border border-red-500/30', label: 'Disabled' }
    default:
      return { bg: 'bg-gray-600/20 text-gray-400 border border-gray-500/30', label: status }
  }
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s
}

function formatDate(iso: string | null): string {
  if (!iso) return '--'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Modal overlay */
function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-gray-800 rounded-lg shadow-2xl border border-gray-700 w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">
            x
          </button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  )
}

/** Secret display with copy-to-clipboard */
function SecretDisplay({ secret, onDismiss }: { secret: string; onDismiss: () => void }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(secret)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback: select the text
    }
  }, [secret])

  return (
    <div className="bg-yellow-900/30 border border-yellow-600/40 rounded-lg p-4 mb-4">
      <p className="text-yellow-400 text-sm font-medium mb-2">
        Save this HMAC secret now -- it will not be shown again.
      </p>
      <div className="flex items-center gap-2">
        <code className="flex-1 bg-gray-900 text-green-400 px-3 py-2 rounded font-mono text-sm break-all select-all">
          {secret}
        </code>
        <button
          onClick={handleCopy}
          className="shrink-0 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <button
        onClick={onDismiss}
        className="mt-3 text-gray-400 hover:text-white text-xs underline"
      >
        I have saved the secret
      </button>
    </div>
  )
}

/** Event multi-select with checkboxes */
function EventSelector({
  selected,
  onChange,
}: {
  selected: Set<EventType>
  onChange: (next: Set<EventType>) => void
}) {
  const toggleEvent = (e: EventType) => {
    const next = new Set(selected)
    if (next.has(e)) next.delete(e)
    else next.add(e)
    onChange(next)
  }

  const selectAll = () => onChange(new Set(ALL_EVENT_TYPES))
  const deselectAll = () => onChange(new Set())

  // Group events by prefix
  const groups: Record<string, EventType[]> = {}
  for (const evt of ALL_EVENT_TYPES) {
    const prefix = evt.split('.')[0]
    ;(groups[prefix] ??= []).push(evt)
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <button
          type="button"
          onClick={selectAll}
          className="text-xs text-em-400 hover:text-em-300 underline"
        >
          Select All
        </button>
        <span className="text-gray-600">|</span>
        <button
          type="button"
          onClick={deselectAll}
          className="text-xs text-gray-400 hover:text-gray-300 underline"
        >
          Deselect All
        </button>
        <span className="ml-auto text-xs text-gray-500">{selected.size} selected</span>
      </div>
      <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
        {Object.entries(groups).map(([prefix, events]) => (
          <div key={prefix}>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{prefix}</p>
            <div className="grid grid-cols-2 gap-1">
              {events.map((evt) => (
                <label
                  key={evt}
                  className="flex items-center gap-2 text-sm text-gray-300 hover:text-white cursor-pointer py-0.5"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(evt)}
                    onChange={() => toggleEvent(evt)}
                    className="accent-em-500 rounded"
                  />
                  <span className="truncate">{evt}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Confirmation modal for destructive actions */
function ConfirmModal({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  loading,
}: {
  open: boolean
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div
        className="bg-gray-800 rounded-lg shadow-2xl border border-gray-700 w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-gray-700">
          <h3 className="text-white font-semibold">{title}</h3>
        </div>
        <div className="px-6 py-4 text-gray-300 text-sm">{message}</div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-700">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors disabled:opacity-50"
          >
            {loading ? 'Working...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Register Webhook Form (inside modal)
// ---------------------------------------------------------------------------

function RegisterWebhookForm({
  adminKey,
  onSuccess,
  onCancel,
}: {
  adminKey: string
  onSuccess: (data: WebhookCreateResponse) => void
  onCancel: () => void
}) {
  const [url, setUrl] = useState('')
  const [description, setDescription] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<Set<EventType>>(new Set())
  const [urlError, setUrlError] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      adminPost<WebhookCreateResponse>(API_PREFIX + '/', adminKey, {
        url,
        events: Array.from(selectedEvents),
        description,
      }),
    onSuccess: (data) => onSuccess(data),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setUrlError('')
    if (!url.startsWith('https://')) {
      setUrlError('URL must start with https://')
      return
    }
    if (selectedEvents.size === 0) {
      setUrlError('Select at least one event type')
      return
    }
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-1">Webhook URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/webhook"
          className="w-full bg-gray-900 text-white px-3 py-2 rounded border border-gray-600 focus:border-em-500 focus:outline-none focus:ring-1 focus:ring-em-500 text-sm"
          required
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-1">Description (optional)</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Production notifications"
          className="w-full bg-gray-900 text-white px-3 py-2 rounded border border-gray-600 focus:border-em-500 focus:outline-none focus:ring-1 focus:ring-em-500 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-2">Event Types</label>
        <EventSelector selected={selectedEvents} onChange={setSelectedEvents} />
      </div>

      {(urlError || mutation.error) && (
        <p className="text-red-400 text-sm">
          {urlError || (mutation.error as Error).message}
        </p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 text-sm bg-em-600 hover:bg-em-700 text-white rounded transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? 'Registering...' : 'Register Webhook'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Edit Webhook Form (inside modal)
// ---------------------------------------------------------------------------

function EditWebhookForm({
  adminKey,
  webhook,
  onSuccess,
  onCancel,
}: {
  adminKey: string
  webhook: WebhookResponse
  onSuccess: () => void
  onCancel: () => void
}) {
  const [url, setUrl] = useState(webhook.url)
  const [description, setDescription] = useState(webhook.description)
  const [selectedEvents, setSelectedEvents] = useState<Set<EventType>>(
    new Set(webhook.events as EventType[])
  )

  const mutation = useMutation({
    mutationFn: () =>
      adminPut<WebhookResponse>(`${API_PREFIX}/${webhook.webhook_id}`, adminKey, {
        url,
        events: Array.from(selectedEvents),
        description,
      }),
    onSuccess,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.startsWith('https://')) return
    if (selectedEvents.size === 0) return
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-1">Webhook URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full bg-gray-900 text-white px-3 py-2 rounded border border-gray-600 focus:border-em-500 focus:outline-none focus:ring-1 focus:ring-em-500 text-sm"
          required
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-1">Description</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full bg-gray-900 text-white px-3 py-2 rounded border border-gray-600 focus:border-em-500 focus:outline-none focus:ring-1 focus:ring-em-500 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-400 mb-2">Event Types</label>
        <EventSelector selected={selectedEvents} onChange={setSelectedEvents} />
      </div>

      {mutation.error && (
        <p className="text-red-400 text-sm">{(mutation.error as Error).message}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-4 py-2 text-sm bg-em-600 hover:bg-em-700 text-white rounded transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Expanded Row Detail
// ---------------------------------------------------------------------------

function WebhookDetail({
  adminKey,
  webhook,
  onRefresh,
}: {
  adminKey: string
  webhook: WebhookResponse
  onRefresh: () => void
}) {
  const queryClient = useQueryClient()
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showRotateConfirm, setShowRotateConfirm] = useState(false)
  const [rotatedSecret, setRotatedSecret] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  const toggleStatus = useMutation({
    mutationFn: () =>
      adminPut<WebhookResponse>(`${API_PREFIX}/${webhook.webhook_id}`, adminKey, {
        status: webhook.status === 'active' ? 'paused' : 'active',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      onRefresh()
    },
  })

  const deleteWebhook = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`${API_PREFIX}/${webhook.webhook_id}`, adminKey, {
        method: 'DELETE',
      })
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Delete failed: ${res.status}`)
      }
    },
    onSuccess: () => {
      setShowDeleteConfirm(false)
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      onRefresh()
    },
  })

  const rotateSecret = useMutation({
    mutationFn: () =>
      adminPost<RotateSecretResponse>(
        `${API_PREFIX}/${webhook.webhook_id}/rotate-secret`,
        adminKey,
        {}
      ),
    onSuccess: (data) => {
      setRotatedSecret(data.secret)
      setShowRotateConfirm(false)
    },
  })

  const testWebhook = useMutation({
    mutationFn: () =>
      adminPost<TestResult>(`${API_PREFIX}/${webhook.webhook_id}/test`, adminKey, {}),
    onSuccess: (data) => setTestResult(data),
    onError: (err) =>
      setTestResult({ webhook_id: webhook.webhook_id, delivered: false, error: (err as Error).message }),
  })

  const badge = statusBadge(webhook.status)

  return (
    <div className="bg-gray-800/50 border-t border-gray-700 px-6 py-4">
      {/* Secret display after rotation */}
      {rotatedSecret && (
        <SecretDisplay secret={rotatedSecret} onDismiss={() => setRotatedSecret(null)} />
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 uppercase">Status</p>
          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badge.bg}`}>
            {badge.label}
          </span>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Total Deliveries</p>
          <p className="text-white text-sm">{webhook.total_deliveries}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Successful</p>
          <p className="text-green-400 text-sm">{webhook.successful_deliveries}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Failures</p>
          <p className={`text-sm ${webhook.failure_count > 0 ? 'text-red-400' : 'text-gray-400'}`}>
            {webhook.failure_count}
          </p>
        </div>
      </div>

      {/* Full URL */}
      <div className="mb-3">
        <p className="text-xs text-gray-500 uppercase mb-1">URL</p>
        <code className="text-sm text-gray-300 bg-gray-900 px-2 py-1 rounded break-all block">
          {webhook.url}
        </code>
      </div>

      {/* Description */}
      {webhook.description && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 uppercase mb-1">Description</p>
          <p className="text-sm text-gray-300">{webhook.description}</p>
        </div>
      )}

      {/* Events */}
      <div className="mb-4">
        <p className="text-xs text-gray-500 uppercase mb-1">Subscribed Events</p>
        <div className="flex flex-wrap gap-1">
          {webhook.events.map((evt) => (
            <span
              key={evt}
              className={`text-xs px-2 py-0.5 rounded border ${eventColor(evt)}`}
            >
              {evt}
            </span>
          ))}
        </div>
      </div>

      {/* Timestamps */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4 text-xs text-gray-500">
        <div>
          <p className="uppercase">Created</p>
          <p className="text-gray-300">{formatDate(webhook.created_at)}</p>
        </div>
        <div>
          <p className="uppercase">Updated</p>
          <p className="text-gray-300">{formatDate(webhook.updated_at)}</p>
        </div>
        <div>
          <p className="uppercase">Last Triggered</p>
          <p className="text-gray-300">{formatDate(webhook.last_triggered_at)}</p>
        </div>
      </div>

      {/* Test result */}
      {testResult && (
        <div
          className={`mb-4 px-3 py-2 rounded text-sm ${
            testResult.delivered
              ? 'bg-green-900/30 border border-green-600/40 text-green-400'
              : 'bg-red-900/30 border border-red-600/40 text-red-400'
          }`}
        >
          {testResult.delivered
            ? `Test delivered successfully (event: ${testResult.test_event_id ?? 'n/a'})`
            : `Test delivery failed: ${testResult.error ?? 'Unknown error'}`}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setShowEditModal(true)}
          className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
        >
          Edit
        </button>
        <button
          onClick={() => toggleStatus.mutate()}
          disabled={toggleStatus.isPending}
          className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors disabled:opacity-50"
        >
          {toggleStatus.isPending
            ? 'Working...'
            : webhook.status === 'active'
              ? 'Pause'
              : 'Resume'}
        </button>
        <button
          onClick={() => testWebhook.mutate()}
          disabled={testWebhook.isPending}
          className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors disabled:opacity-50"
        >
          {testWebhook.isPending ? 'Sending...' : 'Send Test'}
        </button>
        <button
          onClick={() => setShowRotateConfirm(true)}
          className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-yellow-400 rounded transition-colors"
        >
          Rotate Secret
        </button>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-red-400 rounded transition-colors"
        >
          Delete
        </button>
      </div>

      {/* Edit modal */}
      <Modal open={showEditModal} onClose={() => setShowEditModal(false)} title="Edit Webhook">
        <EditWebhookForm
          adminKey={adminKey}
          webhook={webhook}
          onSuccess={() => {
            setShowEditModal(false)
            queryClient.invalidateQueries({ queryKey: ['webhooks'] })
            onRefresh()
          }}
          onCancel={() => setShowEditModal(false)}
        />
      </Modal>

      {/* Delete confirmation */}
      <ConfirmModal
        open={showDeleteConfirm}
        title="Delete Webhook"
        message={`Permanently delete webhook ${truncate(webhook.webhook_id, 12)}? This action cannot be undone. All delivery history will be lost.`}
        confirmLabel="Delete"
        loading={deleteWebhook.isPending}
        onConfirm={() => deleteWebhook.mutate()}
        onCancel={() => setShowDeleteConfirm(false)}
      />

      {/* Rotate secret confirmation */}
      <ConfirmModal
        open={showRotateConfirm}
        title="Rotate HMAC Secret"
        message="Generate a new signing secret? The current secret will stop working immediately. Make sure to update your endpoint before rotating."
        confirmLabel="Rotate"
        loading={rotateSecret.isPending}
        onConfirm={() => rotateSecret.mutate()}
        onCancel={() => setShowRotateConfirm(false)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function Webhooks({ adminKey }: WebhooksProps) {
  const queryClient = useQueryClient()
  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [createdSecret, setCreatedSecret] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const {
    data: webhooks,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['webhooks', adminKey],
    queryFn: () => adminGet<WebhookResponse[]>(API_PREFIX + '/', adminKey),
    enabled: !!adminKey,
  })

  const handleRegisterSuccess = (data: WebhookCreateResponse) => {
    setCreatedSecret(data.secret)
    setShowRegisterModal(false)
    queryClient.invalidateQueries({ queryKey: ['webhooks'] })
  }

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Webhooks</h1>
          <p className="text-gray-400 text-sm mt-1">
            Manage webhook endpoints for real-time event notifications
          </p>
        </div>
        <button
          onClick={() => setShowRegisterModal(true)}
          className="px-4 py-2 bg-em-600 hover:bg-em-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Register Webhook
        </button>
      </div>

      {/* Secret from just-created webhook */}
      {createdSecret && (
        <SecretDisplay secret={createdSecret} onDismiss={() => setCreatedSecret(null)} />
      )}

      {/* Loading state */}
      {isLoading && <div className="text-gray-400">Loading webhooks...</div>}

      {/* Error state */}
      {error && (
        <div className="bg-red-900/20 border border-red-600/40 rounded-lg p-4 text-red-400 text-sm">
          <p className="font-medium mb-1">Failed to load webhooks</p>
          <p>{(error as Error).message}</p>
          <p className="text-xs text-red-500 mt-2">
            Note: Webhook endpoints require agent API key auth. Admin-level webhook listing
            may need a dedicated /api/v1/admin/webhooks endpoint on the backend.
          </p>
        </div>
      )}

      {/* Empty state */}
      {webhooks && webhooks.length === 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">No webhooks registered</p>
          <p className="text-gray-500 text-sm mb-4">
            Register a webhook endpoint to receive real-time notifications about tasks,
            payments, and other platform events.
          </p>
          <button
            onClick={() => setShowRegisterModal(true)}
            className="px-4 py-2 bg-em-600 hover:bg-em-700 text-white rounded text-sm transition-colors"
          >
            Register Your First Webhook
          </button>
        </div>
      )}

      {/* Webhook table */}
      {webhooks && webhooks.length > 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
          {/* Header row */}
          <div className="grid grid-cols-12 gap-2 px-4 py-3 bg-gray-800/80 border-b border-gray-700 text-xs text-gray-500 uppercase tracking-wider">
            <div className="col-span-2">ID</div>
            <div className="col-span-2">Owner</div>
            <div className="col-span-3">URL</div>
            <div className="col-span-2">Events</div>
            <div className="col-span-1">Status</div>
            <div className="col-span-2">Created</div>
          </div>

          {/* Data rows */}
          {webhooks.map((wh) => {
            const isExpanded = expandedId === wh.webhook_id
            const badge = statusBadge(wh.status)

            return (
              <div key={wh.webhook_id}>
                <div
                  className={`grid grid-cols-12 gap-2 px-4 py-3 items-center cursor-pointer hover:bg-gray-700/50 transition-colors ${
                    isExpanded ? 'bg-gray-700/30' : ''
                  }`}
                  onClick={() => toggleExpand(wh.webhook_id)}
                >
                  <div className="col-span-2 text-sm text-gray-300 font-mono">
                    {truncate(wh.webhook_id, 10)}
                  </div>
                  <div className="col-span-2 text-sm text-gray-300">
                    {truncate(wh.owner_id, 12)}
                  </div>
                  <div className="col-span-3 text-sm text-gray-400 truncate" title={wh.url}>
                    {truncate(wh.url, 36)}
                  </div>
                  <div className="col-span-2 flex flex-wrap gap-1">
                    {wh.events.slice(0, 2).map((evt) => (
                      <span
                        key={evt}
                        className={`text-xs px-1.5 py-0.5 rounded border ${eventColor(evt)}`}
                      >
                        {evt.split('.')[1]}
                      </span>
                    ))}
                    {wh.events.length > 2 && (
                      <span className="text-xs text-gray-500">+{wh.events.length - 2}</span>
                    )}
                  </div>
                  <div className="col-span-1">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badge.bg}`}>
                      {badge.label}
                    </span>
                  </div>
                  <div className="col-span-2 text-xs text-gray-500">
                    {formatDate(wh.created_at)}
                  </div>
                </div>

                {/* Expanded detail panel */}
                {isExpanded && (
                  <WebhookDetail adminKey={adminKey} webhook={wh} onRefresh={() => refetch()} />
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Register modal */}
      <Modal
        open={showRegisterModal}
        onClose={() => setShowRegisterModal(false)}
        title="Register Webhook"
      >
        <RegisterWebhookForm
          adminKey={adminKey}
          onSuccess={handleRegisterSuccess}
          onCancel={() => setShowRegisterModal(false)}
        />
      </Modal>
    </div>
  )
}

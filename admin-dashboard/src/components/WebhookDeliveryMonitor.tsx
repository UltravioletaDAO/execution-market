import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet, adminPost, AdminApiError } from '../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface WebhookDetail {
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

interface DeliveryAttempt {
  attempt: number
  timestamp: string
  status_code: number | null
  error: string | null
  latency_ms: number | null
}

interface DeliveryRecord {
  delivery_id: string
  webhook_id: string
  endpoint_url: string
  event_type: string
  status: 'pending' | 'delivered' | 'failed' | 'retrying' | 'dead_letter'
  attempts: DeliveryAttempt[]
  created_at: string
  completed_at: string | null
}

interface TestEventResult {
  webhook_id: string
  test_event_id?: string
  delivered: boolean
  error?: string
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WebhookDeliveryMonitorProps {
  adminKey: string
  webhookId: string
  webhookUrl: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(dateStr: string | null): string {
  if (!dateStr) return '--'
  const d = new Date(dateStr)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function timeSince(dateStr: string | null): string {
  if (!dateStr) return 'Never'
  const then = new Date(dateStr).getTime()
  const now = Date.now()
  const diffMs = now - then
  if (diffMs < 0) return 'just now'

  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m ago`

  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h ago`
}

function computeSuccessRate(total: number, successful: number): string {
  if (total === 0) return '100'
  return ((successful / total) * 100).toFixed(1)
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  active: { bg: 'bg-green-900/40', text: 'text-green-400', label: 'Active' },
  paused: { bg: 'bg-yellow-900/40', text: 'text-yellow-400', label: 'Paused' },
  disabled: { bg: 'bg-gray-700/40', text: 'text-gray-400', label: 'Disabled' },
  failed: { bg: 'bg-red-900/40', text: 'text-red-400', label: 'Failed' },
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] ?? STATUS_BADGE.disabled
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.text}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          status === 'active' ? 'bg-green-400 animate-pulse' : status === 'failed' ? 'bg-red-400' : 'bg-gray-500'
        }`}
      />
      {cfg.label}
    </span>
  )
}

const EVENT_COLORS: Record<string, string> = {
  task: 'bg-blue-900/40 text-blue-300 border-blue-700/50',
  submission: 'bg-purple-900/40 text-purple-300 border-purple-700/50',
  payment: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50',
  dispute: 'bg-orange-900/40 text-orange-300 border-orange-700/50',
  ping: 'bg-gray-700/40 text-gray-300 border-gray-600/50',
}

function EventBadge({ eventType }: { eventType: string }) {
  const prefix = eventType.split('.')[0] ?? 'ping'
  const colors = EVENT_COLORS[prefix] ?? EVENT_COLORS.ping
  return (
    <span className={`inline-block rounded border px-1.5 py-0.5 text-[11px] font-mono ${colors}`}>
      {eventType}
    </span>
  )
}

function HttpStatusBadge({ code }: { code: number | null }) {
  if (code === null) {
    return <span className="text-xs text-gray-500 font-mono">--</span>
  }
  const color =
    code >= 200 && code < 300
      ? 'text-green-400'
      : code >= 400 && code < 500
        ? 'text-yellow-400'
        : code >= 500
          ? 'text-red-400'
          : 'text-gray-400'
  return <span className={`text-xs font-mono font-semibold ${color}`}>{code}</span>
}

function DeliveryStatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    delivered: { color: 'text-green-400', label: 'Delivered' },
    failed: { color: 'text-red-400', label: 'Failed' },
    dead_letter: { color: 'text-red-500', label: 'Dead Letter' },
    retrying: { color: 'text-yellow-400', label: 'Retrying' },
    pending: { color: 'text-gray-400', label: 'Pending' },
  }
  const cfg = map[status] ?? { color: 'text-gray-400', label: status }
  return <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WebhookDeliveryMonitor({
  adminKey,
  webhookId,
  webhookUrl: _webhookUrl,
}: WebhookDeliveryMonitorProps) {
  const queryClient = useQueryClient()
  const [deliveryHistoryAvailable, setDeliveryHistoryAvailable] = useState<boolean | null>(null)

  // Fetch webhook detail (aggregate stats)
  const {
    data: webhook,
    isLoading: loadingDetail,
    error: detailError,
  } = useQuery<WebhookDetail>({
    queryKey: ['webhook-detail', webhookId],
    queryFn: () => adminGet<WebhookDetail>(`/api/v1/webhooks/${webhookId}`, adminKey),
    refetchInterval: 30_000,
  })

  // Attempt to fetch delivery history (may 404 if endpoint not implemented)
  const {
    data: deliveries,
    isLoading: loadingDeliveries,
  } = useQuery<DeliveryRecord[]>({
    queryKey: ['webhook-deliveries', webhookId],
    queryFn: async () => {
      try {
        const result = await adminGet<DeliveryRecord[]>(
          `/api/v1/webhooks/${webhookId}/deliveries`,
          adminKey,
        )
        setDeliveryHistoryAvailable(true)
        return result
      } catch (err) {
        if (err instanceof AdminApiError && (err.status === 404 || err.status === 405)) {
          setDeliveryHistoryAvailable(false)
          return []
        }
        throw err
      }
    },
    refetchInterval: 30_000,
    retry: false,
  })

  // Send test event
  const testMutation = useMutation<TestEventResult, Error>({
    mutationFn: () =>
      adminPost<TestEventResult>(`/api/v1/webhooks/${webhookId}/test`, adminKey, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhook-detail', webhookId] })
      queryClient.invalidateQueries({ queryKey: ['webhook-deliveries', webhookId] })
    },
  })

  // Redeliver a failed delivery
  const redeliverMutation = useMutation<TestEventResult, Error, string>({
    mutationFn: (deliveryId: string) =>
      adminPost<TestEventResult>(
        `/api/v1/webhooks/${webhookId}/deliveries/${deliveryId}/redeliver`,
        adminKey,
        {},
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhook-deliveries', webhookId] })
      queryClient.invalidateQueries({ queryKey: ['webhook-detail', webhookId] })
    },
  })

  // -------------------------------------------------------------------------
  // Loading / Error states
  // -------------------------------------------------------------------------

  if (loadingDetail) {
    return (
      <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-6">
        <div className="flex items-center gap-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-em-400 border-t-transparent" />
          <span className="text-sm text-gray-400">Loading webhook details...</span>
        </div>
      </div>
    )
  }

  if (detailError || !webhook) {
    return (
      <div className="rounded-lg border border-red-700/40 bg-red-900/20 p-6">
        <p className="text-sm text-red-400">
          Failed to load webhook details.{' '}
          {detailError instanceof Error ? detailError.message : ''}
        </p>
      </div>
    )
  }

  const successRate = computeSuccessRate(webhook.total_deliveries, webhook.successful_deliveries)
  const failedDeliveries = webhook.total_deliveries - webhook.successful_deliveries

  return (
    <div className="space-y-4">
      {/* Header: URL + Status */}
      <div className="flex items-center justify-between rounded-lg border border-gray-700/50 bg-gray-800/60 px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0">
            <StatusBadge status={webhook.status} />
          </div>
          <code className="truncate text-sm text-gray-200" title={webhook.url}>
            {webhook.url}
          </code>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-4">
          <span className="text-xs text-gray-500">
            Created {formatTimestamp(webhook.created_at)}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total Deliveries" value={String(webhook.total_deliveries)} />
        <StatCard
          label="Success Rate"
          value={`${successRate}%`}
          valueColor={
            Number(successRate) >= 95
              ? 'text-green-400'
              : Number(successRate) >= 80
                ? 'text-yellow-400'
                : 'text-red-400'
          }
        />
        <StatCard
          label="Failed"
          value={String(failedDeliveries)}
          valueColor={failedDeliveries > 0 ? 'text-red-400' : 'text-gray-300'}
        />
        <StatCard label="Last Delivery" value={timeSince(webhook.last_triggered_at)} />
      </div>

      {/* Subscribed events */}
      <div className="rounded-lg border border-gray-700/50 bg-gray-800/40 px-4 py-3">
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
          Subscribed Events
        </p>
        <div className="flex flex-wrap gap-1.5">
          {webhook.events.map((evt) => (
            <EventBadge key={evt} eventType={evt} />
          ))}
        </div>
      </div>

      {/* Delivery history or placeholder */}
      {deliveryHistoryAvailable === false ? (
        <DeliveryHistoryPlaceholder
          webhook={webhook}
          testMutation={testMutation}
        />
      ) : (
        <DeliveryHistoryTable
          deliveries={deliveries ?? []}
          loading={loadingDeliveries}
          testMutation={testMutation}
          redeliverMutation={redeliverMutation}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  valueColor = 'text-gray-100',
}: {
  label: string
  value: string
  valueColor?: string
}) {
  return (
    <div className="rounded-lg border border-gray-700/50 bg-gray-800/40 px-3 py-2.5">
      <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500">{label}</p>
      <p className={`mt-0.5 text-lg font-semibold tabular-nums ${valueColor}`}>{value}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Delivery history placeholder (endpoint not implemented)
// ---------------------------------------------------------------------------

function DeliveryHistoryPlaceholder({
  webhook,
  testMutation,
}: {
  webhook: WebhookDetail
  testMutation: ReturnType<typeof useMutation<TestEventResult, Error>>
}) {
  return (
    <div className="rounded-lg border border-gray-700/50 bg-gray-800/40 p-6">
      <div className="flex flex-col items-center gap-4 py-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-gray-600/50 bg-gray-700/40">
          <svg className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-medium text-gray-300">
            Delivery history will be available when the webhook delivery log endpoint is implemented
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Aggregate stats above are updated from the webhook registry in real time.
          </p>
        </div>

        {/* Webhook info summary */}
        <div className="mt-2 w-full max-w-md rounded border border-gray-700/50 bg-gray-900/50 p-3 text-left">
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-gray-500">URL</dt>
              <dd className="font-mono text-gray-300 truncate ml-4 max-w-[250px]" title={webhook.url}>
                {webhook.url}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Events</dt>
              <dd className="text-gray-300">{webhook.events.length} subscribed</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Created</dt>
              <dd className="text-gray-300">{formatTimestamp(webhook.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Status</dt>
              <dd>
                <StatusBadge status={webhook.status} />
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Consecutive Failures</dt>
              <dd className={webhook.failure_count > 0 ? 'text-red-400' : 'text-gray-300'}>
                {webhook.failure_count}
              </dd>
            </div>
          </dl>
        </div>

        {/* Send test event */}
        <button
          onClick={() => testMutation.mutate()}
          disabled={testMutation.isPending}
          className="mt-2 inline-flex items-center gap-2 rounded-lg border border-em-500/40 bg-em-600/20 px-4 py-2 text-sm font-medium text-em-300 transition hover:bg-em-600/30 hover:border-em-500/60 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {testMutation.isPending ? (
            <>
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-em-400 border-t-transparent" />
              Sending...
            </>
          ) : (
            'Send Test Event'
          )}
        </button>

        {testMutation.isSuccess && (
          <p className={`text-xs ${testMutation.data?.delivered ? 'text-green-400' : 'text-red-400'}`}>
            {testMutation.data?.delivered
              ? `Test event delivered (${testMutation.data.test_event_id ?? 'OK'})`
              : `Delivery failed: ${testMutation.data?.error ?? 'Unknown error'}`}
          </p>
        )}

        {testMutation.isError && (
          <p className="text-xs text-red-400">
            Error: {testMutation.error?.message ?? 'Failed to send test event'}
          </p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Delivery history table (endpoint exists)
// ---------------------------------------------------------------------------

function DeliveryHistoryTable({
  deliveries,
  loading,
  testMutation,
  redeliverMutation,
}: {
  deliveries: DeliveryRecord[]
  loading: boolean
  testMutation: ReturnType<typeof useMutation<TestEventResult, Error>>
  redeliverMutation: ReturnType<typeof useMutation<TestEventResult, Error, string>>
}) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  return (
    <div className="rounded-lg border border-gray-700/50 bg-gray-800/40">
      {/* Table header bar */}
      <div className="flex items-center justify-between border-b border-gray-700/50 px-4 py-2.5">
        <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
          Delivery History
        </p>
        <button
          onClick={() => testMutation.mutate()}
          disabled={testMutation.isPending}
          className="inline-flex items-center gap-1.5 rounded border border-em-500/40 bg-em-600/20 px-2.5 py-1 text-xs font-medium text-em-300 transition hover:bg-em-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {testMutation.isPending ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-em-400 border-t-transparent" />
              Sending...
            </>
          ) : (
            'Send Test Event'
          )}
        </button>
      </div>

      {/* Test result feedback */}
      {testMutation.isSuccess && (
        <div
          className={`mx-4 mt-2 rounded px-3 py-1.5 text-xs ${
            testMutation.data?.delivered
              ? 'bg-green-900/30 text-green-400'
              : 'bg-red-900/30 text-red-400'
          }`}
        >
          {testMutation.data?.delivered
            ? `Test event delivered (${testMutation.data.test_event_id ?? 'OK'})`
            : `Delivery failed: ${testMutation.data?.error ?? 'Unknown error'}`}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-em-400 border-t-transparent" />
          <span className="ml-2 text-sm text-gray-400">Loading deliveries...</span>
        </div>
      ) : deliveries.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500">
          No delivery records yet. Send a test event to verify connectivity.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-700/30 text-xs uppercase tracking-wider text-gray-500">
                <th className="px-4 py-2 font-medium">Timestamp</th>
                <th className="px-4 py-2 font-medium">Event Type</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium text-right">HTTP</th>
                <th className="px-4 py-2 font-medium text-right">Latency</th>
                <th className="px-4 py-2 font-medium text-right">Retries</th>
                <th className="px-4 py-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/20">
              {deliveries.map((d) => {
                const lastAttempt = d.attempts[d.attempts.length - 1] ?? null
                const isFailed = d.status === 'failed' || d.status === 'dead_letter'
                const isExpanded = expandedRow === d.delivery_id

                return (
                  <tr key={d.delivery_id} className="group">
                    <td className="px-4 py-2">
                      <button
                        onClick={() => setExpandedRow(isExpanded ? null : d.delivery_id)}
                        className="text-xs text-gray-300 hover:text-em-300 transition"
                        title="Toggle attempt details"
                      >
                        {formatTimestamp(d.created_at)}
                      </button>
                      {/* Expanded attempt details */}
                      {isExpanded && d.attempts.length > 1 && (
                        <div className="mt-2 space-y-1 pl-2 border-l-2 border-gray-700/50">
                          {d.attempts.map((a) => (
                            <div key={a.attempt} className="text-[11px] text-gray-500">
                              <span className="text-gray-600">#{a.attempt}</span>{' '}
                              {formatTimestamp(a.timestamp)}{' '}
                              <HttpStatusBadge code={a.status_code} />{' '}
                              {a.latency_ms != null && (
                                <span className="text-gray-600">{a.latency_ms}ms</span>
                              )}
                              {a.error && (
                                <span className="block text-red-500/80 truncate max-w-[200px]" title={a.error}>
                                  {a.error}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <EventBadge eventType={d.event_type} />
                    </td>
                    <td className="px-4 py-2">
                      <DeliveryStatusBadge status={d.status} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <HttpStatusBadge code={lastAttempt?.status_code ?? null} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      {lastAttempt?.latency_ms != null ? (
                        <span
                          className={`text-xs tabular-nums ${
                            lastAttempt.latency_ms > 5000
                              ? 'text-red-400'
                              : lastAttempt.latency_ms > 1000
                                ? 'text-yellow-400'
                                : 'text-gray-300'
                          }`}
                        >
                          {lastAttempt.latency_ms}ms
                        </span>
                      ) : (
                        <span className="text-xs text-gray-600">--</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <span className="text-xs tabular-nums text-gray-400">
                        {d.attempts.length > 1 ? d.attempts.length - 1 : 0}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {isFailed && (
                        <button
                          onClick={() => redeliverMutation.mutate(d.delivery_id)}
                          disabled={redeliverMutation.isPending}
                          className="text-xs text-em-400 hover:text-em-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {redeliverMutation.isPending ? 'Sending...' : 'Redeliver'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

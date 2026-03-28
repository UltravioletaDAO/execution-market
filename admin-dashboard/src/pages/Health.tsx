import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useCallback } from 'react'
import clsx from 'clsx'
import { API_BASE } from '../lib/api'
import PhantomTasks from '../components/PhantomTasks'
import OrphanedPayments from '../components/OrphanedPayments'
import FinancialAudit from '../components/FinancialAudit'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HealthProps {
  adminKey: string
}

interface ComponentDetail {
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency_ms?: number
  message?: string
  last_check?: string
  details?: Record<string, unknown>
}

interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  uptime_seconds: number
  timestamp: string
  components: Record<string, ComponentDetail>
}

interface VersionResponse {
  name: string
  version: string
  environment: string
  build_date: string
  git_commit: string
  uptime_seconds: number
}

interface DetailedHealthResponse {
  status: string
  version: string
  environment: string
  uptime_seconds: number
  timestamp: string
  components: Record<string, ComponentDetail>
  summary: {
    total_components: number
    healthy: number
    degraded: number
    unhealthy: number
  }
  critical_components: string[]
}

interface SanityWarning {
  check: string
  message: string
  task_ids?: string[]
  submission_ids?: string[]
}

interface SanityResponse {
  status: 'ok' | 'warnings'
  checks_passed: number
  checks_total: number
  warnings: SanityWarning[]
  summary: {
    task_status_distribution: Record<string, number>
    total_tasks: number
    total_bounty_usd: number
  }
  timestamp: string
}

interface RouteInfo {
  path: string
  methods: string[]
  name: string
  tags: string[]
}

interface RoutesResponse {
  total: number
  by_group: Record<string, { count: number; routes: RouteInfo[] }>
  timestamp: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const AUTO_REFRESH_INTERVAL = 30_000

/** Health endpoints live at /health/*, no admin auth required. */
async function healthFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`Health fetch failed: ${res.status}`)
  }
  return res.json()
}

async function healthFetchText(path: string): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`Health fetch failed: ${res.status}`)
  }
  return res.text()
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h < 24) return `${h}h ${m}m`
  const d = Math.floor(h / 24)
  return `${d}d ${h % 24}h ${m}m`
}

function statusColor(status: string): string {
  switch (status) {
    case 'healthy':
    case 'ok':
    case 'pass':
      return 'text-green-400'
    case 'degraded':
    case 'warn':
      return 'text-yellow-400'
    default:
      return 'text-red-400'
  }
}

function statusBgColor(status: string): string {
  switch (status) {
    case 'healthy':
    case 'ok':
    case 'pass':
      return 'bg-green-900/30 border-green-700'
    case 'degraded':
    case 'warn':
      return 'bg-yellow-900/30 border-yellow-700'
    default:
      return 'bg-red-900/30 border-red-700'
  }
}

function statusBorderColor(status: string): string {
  switch (status) {
    case 'healthy':
    case 'ok':
      return 'border-green-600'
    case 'degraded':
    case 'warn':
      return 'border-yellow-600'
    default:
      return 'border-red-600'
  }
}

function statusDot(status: string) {
  const color =
    status === 'healthy' || status === 'ok'
      ? 'bg-green-400'
      : status === 'degraded' || status === 'warn'
        ? 'bg-yellow-400'
        : 'bg-red-400'
  return (
    <span className={clsx('inline-block w-2.5 h-2.5 rounded-full', color)} />
  )
}

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-green-700/60 text-green-300',
  POST: 'bg-blue-700/60 text-blue-300',
  PUT: 'bg-yellow-700/60 text-yellow-300',
  PATCH: 'bg-orange-700/60 text-orange-300',
  DELETE: 'bg-red-700/60 text-red-300',
  MOUNT: 'bg-purple-700/60 text-purple-300',
}

const CRITICAL_COMPONENTS = new Set(['database', 'blockchain'])

const COMPONENT_LABELS: Record<string, { label: string; description: string }> = {
  database: { label: 'Database', description: 'Supabase PostgreSQL' },
  redis: { label: 'Redis', description: 'Cache layer (optional)' },
  x402: { label: 'x402 SDK', description: 'Facilitator + payment config' },
  storage: { label: 'Storage / S3', description: 'Evidence bucket' },
  blockchain: { label: 'Blockchain RPC', description: 'Base L2 on-chain ops' },
}

// ---------------------------------------------------------------------------
// Parse Prometheus text into key/value pairs
// ---------------------------------------------------------------------------

interface ParsedMetric {
  name: string
  help: string
  values: { labels: string; value: string }[]
}

function parsePrometheus(text: string): ParsedMetric[] {
  const metrics: ParsedMetric[] = []
  const lines = text.split('\n')
  let current: ParsedMetric | null = null

  for (const line of lines) {
    if (line.startsWith('# HELP ')) {
      const rest = line.slice(7)
      const sp = rest.indexOf(' ')
      const name = sp > 0 ? rest.slice(0, sp) : rest
      const help = sp > 0 ? rest.slice(sp + 1) : ''
      current = { name, help, values: [] }
      metrics.push(current)
    } else if (line.startsWith('# TYPE ')) {
      // skip type declarations
    } else if (line.trim() && !line.startsWith('#') && current) {
      const match = line.match(/^([^{}\s]+)(?:\{([^}]*)\})?\s+(.+)$/)
      if (match) {
        current.values.push({ labels: match[2] || '', value: match[3] })
      }
    } else if (line.trim() && !line.startsWith('#')) {
      // Metric line without a preceding HELP
      const match = line.match(/^([^{}\s]+)(?:\{([^}]*)\})?\s+(.+)$/)
      if (match) {
        const existing = metrics.find((m) => m.name === match[1])
        if (existing) {
          existing.values.push({ labels: match[2] || '', value: match[3] })
        } else {
          const m: ParsedMetric = {
            name: match[1],
            help: '',
            values: [{ labels: match[2] || '', value: match[3] }],
          }
          metrics.push(m)
          current = m
        }
      }
    }
  }
  return metrics
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CountdownBar({
  secondsLeft,
  total,
}: {
  secondsLeft: number
  total: number
}) {
  const pct = Math.max(0, Math.min(100, (secondsLeft / total) * 100))
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <span>Refresh in {secondsLeft}s</span>
      <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden max-w-[120px]">
        <div
          className="h-full bg-em-600 rounded-full transition-all duration-1000"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function StatusBanner({
  health,
  version,
  countdown,
}: {
  health: HealthResponse | undefined
  version: VersionResponse | undefined
  countdown: number
}) {
  const overall = health?.status || 'unknown'
  return (
    <div className={clsx('rounded-lg border p-5', statusBgColor(overall))}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          {statusDot(overall)}
          <div>
            <h2 className="text-lg font-semibold text-white">
              System{' '}
              {overall === 'healthy'
                ? 'Operational'
                : overall === 'degraded'
                  ? 'Degraded'
                  : overall === 'unhealthy'
                    ? 'Down'
                    : 'Unknown'}
            </h2>
            <p className="text-sm text-gray-400 mt-0.5">
              {health?.timestamp
                ? `Last check: ${new Date(health.timestamp).toLocaleTimeString()}`
                : 'Checking...'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-gray-400">
          {version && (
            <>
              <span>
                <span className="text-gray-500">Version</span>{' '}
                <span className="text-gray-300 font-mono">{version.version}</span>
              </span>
              <span>
                <span className="text-gray-500">Build</span>{' '}
                <span className="text-gray-300 font-mono">{version.git_commit}</span>
              </span>
              <span>
                <span className="text-gray-500">Uptime</span>{' '}
                <span className="text-gray-300">
                  {formatUptime(version.uptime_seconds)}
                </span>
              </span>
              <span>
                <span className="text-gray-500">Env</span>{' '}
                <span className="text-gray-300">{version.environment}</span>
              </span>
            </>
          )}
          <CountdownBar
            secondsLeft={countdown}
            total={AUTO_REFRESH_INTERVAL / 1000}
          />
        </div>
      </div>
    </div>
  )
}

function ComponentCard({
  name,
  comp,
}: {
  name: string
  comp: ComponentDetail
}) {
  const [expanded, setExpanded] = useState(false)
  const info = COMPONENT_LABELS[name] || { label: name, description: '' }
  const isCritical = CRITICAL_COMPONENTS.has(name)

  return (
    <div
      className={clsx(
        'rounded-lg border bg-gray-800 p-4 cursor-pointer transition-colors hover:bg-gray-800/80',
        statusBorderColor(comp.status),
      )}
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          {statusDot(comp.status)}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-medium">{info.label}</span>
              {isCritical && (
                <span className="text-[10px] uppercase tracking-wide font-semibold px-1.5 py-0.5 rounded bg-red-900/40 text-red-400 border border-red-800">
                  Critical
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{info.description}</p>
          </div>
        </div>
        <span
          className={clsx(
            'text-xs font-medium capitalize',
            statusColor(comp.status),
          )}
        >
          {comp.status}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
        {comp.latency_ms !== undefined && (
          <span>
            <span className="text-gray-500">Latency</span>{' '}
            <span
              className={clsx(
                comp.latency_ms > 1000 ? 'text-yellow-400' : 'text-gray-300',
              )}
            >
              {comp.latency_ms.toFixed(0)}ms
            </span>
          </span>
        )}
        {comp.last_check && (
          <span>
            <span className="text-gray-500">Checked</span>{' '}
            <span className="text-gray-300">
              {new Date(comp.last_check).toLocaleTimeString()}
            </span>
          </span>
        )}
      </div>

      {comp.message && (
        <p className="mt-2 text-xs text-gray-400 truncate">{comp.message}</p>
      )}

      {expanded && comp.details && Object.keys(comp.details).length > 0 && (
        <div className="mt-3 border-t border-gray-700 pt-3">
          <pre className="text-xs text-gray-400 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
            {JSON.stringify(comp.details, null, 2)}
          </pre>
        </div>
      )}

      <div className="mt-2 text-center">
        <span className="text-[10px] text-gray-600">
          {expanded ? 'Click to collapse' : 'Click to expand details'}
        </span>
      </div>
    </div>
  )
}

function SanitySection() {
  const {
    data: sanity,
    isLoading,
    isFetching,
    refetch,
    error,
  } = useQuery<SanityResponse>({
    queryKey: ['health', 'sanity'],
    queryFn: () => healthFetch('/health/sanity'),
    staleTime: 60_000,
  })

  const passed = sanity?.checks_passed ?? 0
  const total = sanity?.checks_total ?? 0
  const hasIssues = sanity && sanity.warnings.length > 0

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-white font-semibold">Data Sanity Checks</h3>
          {sanity && (
            <span
              className={clsx(
                'text-xs font-medium px-2 py-0.5 rounded-full',
                hasIssues
                  ? 'bg-yellow-900/40 text-yellow-400 border border-yellow-800'
                  : 'bg-green-900/40 text-green-400 border border-green-800',
              )}
            >
              {hasIssues
                ? `${total - passed} issue${total - passed !== 1 ? 's' : ''} found`
                : `${passed}/${total} passed`}
            </span>
          )}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className={clsx(
            'text-sm px-3 py-1.5 rounded border transition-colors',
            isFetching
              ? 'border-gray-600 text-gray-500 cursor-not-allowed'
              : 'border-em-600 text-em-400 hover:bg-em-900/30',
          )}
        >
          {isFetching ? 'Running...' : 'Run Full Check'}
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
          <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-em-500" />
          Running sanity checks...
        </div>
      )}

      {error && (
        <p className="text-red-400 text-sm">
          Failed to load sanity checks: {String(error)}
        </p>
      )}

      {sanity && (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-gray-900 rounded p-3 text-center">
              <div className="text-2xl font-bold text-white">
                {sanity.summary.total_tasks}
              </div>
              <div className="text-xs text-gray-500">Total Tasks</div>
            </div>
            <div className="bg-gray-900 rounded p-3 text-center">
              <div className="text-2xl font-bold text-white">
                ${sanity.summary.total_bounty_usd.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500">Total Bounties</div>
            </div>
            <div className="bg-gray-900 rounded p-3 text-center">
              <div className="text-2xl font-bold text-white">
                {Object.entries(sanity.summary.task_status_distribution)
                  .filter(([s]) =>
                    ['published', 'accepted', 'in_progress', 'submitted'].includes(
                      s,
                    ),
                  )
                  .reduce((sum, [, c]) => sum + c, 0)}
              </div>
              <div className="text-xs text-gray-500">Active Tasks</div>
            </div>
          </div>

          {/* Check rows */}
          <div className="space-y-1">
            {sanity.warnings.length === 0 && (
              <div className="flex items-center gap-3 p-2 text-sm">
                <span className="text-green-400">&#10003;</span>
                <span className="text-gray-300">
                  All {total} consistency checks passed. No issues detected.
                </span>
              </div>
            )}
            {sanity.warnings.map((w, i) => (
              <div
                key={i}
                className={clsx(
                  'flex items-start gap-3 p-2 rounded text-sm',
                  w.check.includes('fail')
                    ? 'bg-red-900/20'
                    : 'bg-yellow-900/20',
                )}
              >
                <span
                  className={
                    w.check.includes('fail')
                      ? 'text-red-400'
                      : 'text-yellow-400'
                  }
                >
                  {w.check.includes('fail') ? '!!' : '!'}
                </span>
                <div>
                  <span className="text-gray-300 font-mono text-xs">
                    {w.check}
                  </span>
                  <p className="text-gray-400 mt-0.5">{w.message}</p>
                  {w.task_ids && w.task_ids.length > 0 && (
                    <p className="text-gray-500 text-xs mt-1 font-mono truncate">
                      IDs: {w.task_ids.slice(0, 5).join(', ')}
                      {w.task_ids.length > 5 &&
                        ` (+${w.task_ids.length - 5} more)`}
                    </p>
                  )}
                  {w.submission_ids && w.submission_ids.length > 0 && (
                    <p className="text-gray-500 text-xs mt-1 font-mono truncate">
                      Submissions: {w.submission_ids.slice(0, 5).join(', ')}
                      {w.submission_ids.length > 5 &&
                        ` (+${w.submission_ids.length - 5} more)`}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Status distribution */}
          {Object.keys(sanity.summary.task_status_distribution).length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-700">
              <p className="text-xs text-gray-500 mb-2">
                Task Status Distribution
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(sanity.summary.task_status_distribution)
                  .sort(([, a], [, b]) => b - a)
                  .map(([st, count]) => (
                    <span
                      key={st}
                      className="text-xs px-2 py-1 rounded bg-gray-900 text-gray-400"
                    >
                      {st}:{' '}
                      <span className="text-gray-200 font-medium">
                        {count}
                      </span>
                    </span>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function MetricsSection() {
  const [expanded, setExpanded] = useState(false)
  const {
    data: rawMetrics,
    isLoading,
    error,
  } = useQuery<string>({
    queryKey: ['health', 'metrics'],
    queryFn: () => healthFetchText('/health/metrics'),
    staleTime: 30_000,
    enabled: expanded,
  })

  const parsed = rawMetrics ? parsePrometheus(rawMetrics) : []

  const findMetric = (name: string) => parsed.find((m) => m.name === name)

  const requestsTotal = findMetric('em_requests_total')
  const activeTasks = findMetric('em_active_tasks')
  const escrowBalance = findMetric('em_escrow_balance_usd')
  const componentHealth = findMetric('em_component_health')

  const totalRequests = requestsTotal
    ? requestsTotal.values.reduce(
        (sum, v) => sum + parseFloat(v.value || '0'),
        0,
      )
    : null

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <h3 className="text-white font-semibold">API Metrics (Prometheus)</h3>
        <span className="text-gray-500 text-sm">
          {expanded ? '[-]' : '[+]'}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-5">
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
              <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-em-500" />
              Loading metrics...
            </div>
          )}

          {error && (
            <p className="text-red-400 text-sm">
              Failed to load metrics: {String(error)}
            </p>
          )}

          {rawMetrics && (
            <>
              {/* Key metrics summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                {totalRequests !== null && (
                  <div className="bg-gray-900 rounded p-3">
                    <div className="text-lg font-bold text-white">
                      {totalRequests.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Total Requests</div>
                  </div>
                )}
                {activeTasks && activeTasks.values.length > 0 && (
                  <div className="bg-gray-900 rounded p-3">
                    <div className="text-lg font-bold text-white">
                      {activeTasks.values
                        .reduce(
                          (sum, v) => sum + parseFloat(v.value || '0'),
                          0,
                        )
                        .toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">
                      Active Tasks (gauge)
                    </div>
                  </div>
                )}
                {escrowBalance && escrowBalance.values.length > 0 && (
                  <div className="bg-gray-900 rounded p-3">
                    <div className="text-lg font-bold text-white">
                      $
                      {escrowBalance.values
                        .reduce(
                          (sum, v) => sum + parseFloat(v.value || '0'),
                          0,
                        )
                        .toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500">Escrow Balance</div>
                  </div>
                )}
                {componentHealth && componentHealth.values.length > 0 && (
                  <div className="bg-gray-900 rounded p-3">
                    <div className="text-lg font-bold text-white">
                      {
                        componentHealth.values.filter(
                          (v) => parseFloat(v.value) === 1,
                        ).length
                      }
                      /{componentHealth.values.length}
                    </div>
                    <div className="text-xs text-gray-500">
                      Components Healthy
                    </div>
                  </div>
                )}
              </div>

              {/* Full metric list */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {parsed.map((metric) => (
                  <div key={metric.name} className="text-xs">
                    <div className="flex items-baseline gap-2">
                      <span className="text-em-400 font-mono font-medium">
                        {metric.name}
                      </span>
                      {metric.help && (
                        <span className="text-gray-600 truncate">
                          {metric.help}
                        </span>
                      )}
                    </div>
                    {metric.values.map((v, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 pl-4 mt-0.5"
                      >
                        {v.labels && (
                          <span className="text-gray-500 font-mono">
                            {'{' + v.labels + '}'}
                          </span>
                        )}
                        <span className="text-gray-300 font-mono">
                          {v.value}
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
                {parsed.length === 0 && (
                  <p className="text-gray-500 text-sm">
                    No metrics available.
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function RoutesSection() {
  const [expanded, setExpanded] = useState(false)
  const {
    data: routes,
    isLoading,
    error,
  } = useQuery<RoutesResponse>({
    queryKey: ['health', 'routes'],
    queryFn: () => healthFetch('/health/routes'),
    staleTime: 120_000,
    enabled: expanded,
  })

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-3">
          <h3 className="text-white font-semibold">Registered Routes</h3>
          {routes && (
            <span className="text-xs text-gray-500">
              {routes.total} routes
            </span>
          )}
        </div>
        <span className="text-gray-500 text-sm">
          {expanded ? '[-]' : '[+]'}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-5">
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
              <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-em-500" />
              Loading routes...
            </div>
          )}

          {error && (
            <p className="text-red-400 text-sm">
              Failed to load routes: {String(error)}
            </p>
          )}

          {routes && (
            <div className="space-y-4">
              {Object.entries(routes.by_group)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([group, { count, routes: groupRoutes }]) => (
                  <div key={group}>
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="text-sm font-medium text-gray-300 uppercase tracking-wide">
                        {group}
                      </h4>
                      <span className="text-xs text-gray-600">({count})</span>
                    </div>
                    <div className="space-y-0.5">
                      {groupRoutes.map((route, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-900/50 text-xs"
                        >
                          <div className="flex gap-1 w-20 shrink-0">
                            {route.methods.map((method) => (
                              <span
                                key={method}
                                className={clsx(
                                  'px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold',
                                  METHOD_COLORS[method] ||
                                    'bg-gray-700 text-gray-400',
                                )}
                              >
                                {method}
                              </span>
                            ))}
                          </div>
                          <span className="text-gray-300 font-mono">
                            {route.path}
                          </span>
                          {route.name && (
                            <span className="text-gray-600 ml-auto truncate max-w-[200px]">
                              {route.name}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Health Page
// ---------------------------------------------------------------------------

export default function Health({ adminKey }: HealthProps) {
  // Countdown timer for auto-refresh indicator
  const [countdown, setCountdown] = useState(AUTO_REFRESH_INTERVAL / 1000)

  const resetCountdown = useCallback(() => {
    setCountdown(AUTO_REFRESH_INTERVAL / 1000)
  }, [])

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) =>
        prev <= 1 ? AUTO_REFRESH_INTERVAL / 1000 : prev - 1,
      )
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // --- Data fetching ---

  const {
    data: health,
    isLoading: healthLoading,
    error: healthError,
  } = useQuery<HealthResponse>({
    queryKey: ['health', 'root'],
    queryFn: async () => {
      const result = await healthFetch<HealthResponse>('/health?force=true')
      resetCountdown()
      return result
    },
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 10_000,
  })

  const { data: version, isLoading: versionLoading } =
    useQuery<VersionResponse>({
      queryKey: ['health', 'version'],
      queryFn: () => healthFetch('/health/version'),
      refetchInterval: AUTO_REFRESH_INTERVAL,
      staleTime: 10_000,
    })

  const { data: detailed } = useQuery<DetailedHealthResponse>({
    queryKey: ['health', 'detailed'],
    queryFn: () => healthFetch('/health/detailed?force=true'),
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 10_000,
  })

  // Merge component data: prefer detailed response (has summary + critical list)
  const components = detailed?.components ?? health?.components ?? {}
  const criticalList =
    detailed?.critical_components ?? Array.from(CRITICAL_COMPONENTS)

  // Order components: critical first, then alphabetical
  const orderedComponents = Object.entries(components).sort(([a], [b]) => {
    const aCrit = criticalList.includes(a) ? 0 : 1
    const bCrit = criticalList.includes(b) ? 0 : 1
    if (aCrit !== bCrit) return aCrit - bCrit
    return a.localeCompare(b)
  })

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (healthLoading && versionLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-em-500 mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Loading health data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          Health &amp; Monitoring
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Real-time system health, data consistency, and API metrics
        </p>
      </div>

      {/* Error banner */}
      {healthError && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
          Failed to reach health endpoint: {String(healthError)}. The API
          server may be down.
        </div>
      )}

      {/* Section A: Status Banner */}
      <StatusBanner health={health} version={version} countdown={countdown} />

      {/* Section B: Component Health Cards */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
          Component Health
          {detailed?.summary && (
            <span className="ml-2 normal-case tracking-normal text-gray-500">
              {detailed.summary.healthy} healthy, {detailed.summary.degraded}{' '}
              degraded, {detailed.summary.unhealthy} unhealthy
            </span>
          )}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {orderedComponents.map(([name, comp]) => (
            <ComponentCard key={name} name={name} comp={comp} />
          ))}
          {orderedComponents.length === 0 && !healthLoading && (
            <p className="text-gray-500 text-sm col-span-full">
              No component data available.
            </p>
          )}
        </div>
      </div>

      {/* Section C: Sanity Checks */}
      <SanitySection />

      {/* Section D: API Metrics (collapsible) */}
      <MetricsSection />

      {/* Section E: Registered Routes (collapsible, collapsed by default) */}
      <RoutesSection />

      {/* Section F: Existing health auditors (phantom tasks, orphaned payments, financial audit) */}
      <div className="border-t border-gray-700 pt-6 space-y-8">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
          Financial Health Auditors
        </h3>
        <PhantomTasks adminKey={adminKey} />
        <OrphanedPayments adminKey={adminKey} />
        <FinancialAudit adminKey={adminKey} />
      </div>
    </div>
  )
}

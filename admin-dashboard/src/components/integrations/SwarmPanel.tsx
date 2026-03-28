import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminPut } from '../../lib/api'

interface SwarmPanelProps {
  adminKey: string
  config: Record<string, any>
  onConfigUpdate: () => void
}

// --- Routing Strategies (from orchestrator.py RoutingStrategy enum) ---

const ROUTING_STRATEGIES = [
  {
    value: 'best_fit',
    label: 'BEST_FIT',
    description:
      'Assign to the highest-scoring available agent. Maximizes task quality by always picking the top candidate.',
  },
  {
    value: 'round_robin',
    label: 'ROUND_ROBIN',
    description:
      'Distribute tasks evenly across agents with tie-breaking by score. Prevents overloading a single agent.',
  },
  {
    value: 'specialist',
    label: 'SPECIALIST',
    description:
      'Only assign to agents with prior experience in the task category. Falls back to BEST_FIT if no specialist is available.',
  },
  {
    value: 'budget_aware',
    label: 'BUDGET_AWARE',
    description:
      'Prefer agents with remaining daily/monthly budget headroom. Avoids burning through a single agent budget.',
  },
] as const

// --- Priority weights (from orchestrator.py PRIORITY_WEIGHTS) ---

const DEFAULT_PRIORITY_WEIGHTS: { key: string; label: string; default: number }[] = [
  { key: 'critical', label: 'CRITICAL', default: 1.0 },
  { key: 'high', label: 'HIGH', default: 0.8 },
  { key: 'normal', label: 'NORMAL', default: 0.5 },
  { key: 'low', label: 'LOW', default: 0.2 },
]

// --- Circuit breaker defaults (from config_manager.py SchedulerConfig) ---

const CIRCUIT_BREAKER_DEFAULTS = {
  failure_threshold: 5,
  reset_timeout_seconds: 60,
}

// --- Config key helpers ---

const CONFIG_KEYS = {
  routingStrategy: 'swarm.routing_strategy',
  priorityWeight: (level: string) => `swarm.priority_weight_${level}`,
  cbThreshold: 'swarm.circuit_breaker_threshold',
  cbResetTimeout: 'swarm.circuit_breaker_reset_seconds',
}

// --- Inline "Coming Soon" badge ---

function ComingSoonBadge() {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-900/40 text-yellow-400 border border-yellow-700/50 ml-2">
      Coming Soon
    </span>
  )
}

// --- Editable config row with reason dialog ---

function EditableRow({
  label,
  configKey,
  currentValue,
  defaultValue,
  adminKey,
  onSuccess,
  type = 'text',
  options,
}: {
  label: string
  configKey: string
  currentValue: any
  defaultValue: any
  adminKey: string
  onSuccess: () => void
  type?: 'text' | 'number' | 'select'
  options?: { value: string; label: string }[]
}) {
  const queryClient = useQueryClient()
  const hasConfigKey = currentValue !== undefined && currentValue !== null
  const displayValue = hasConfigKey ? currentValue : defaultValue

  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(displayValue))
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      adminPut(`/api/v1/admin/config/${configKey}`, adminKey, {
        value: type === 'number' ? Number(draft) : draft,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      setEditing(false)
      setReason('')
      queryClient.invalidateQueries({ queryKey: ['config'] })
      onSuccess()
    },
  })

  if (!editing) {
    return (
      <div className="flex items-center justify-between py-2.5 border-b border-gray-700 last:border-b-0">
        <span className="text-gray-300 text-sm">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-white font-mono text-sm">{displayValue}</span>
          {!hasConfigKey && <ComingSoonBadge />}
          {hasConfigKey && (
            <button
              onClick={() => {
                setDraft(String(displayValue))
                setEditing(true)
              }}
              className="text-em-400 hover:text-em-300 text-xs ml-2"
            >
              Edit
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="py-2.5 border-b border-gray-700 last:border-b-0 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-gray-300 text-sm">{label}</span>
        {type === 'select' && options ? (
          <select
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 text-sm"
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            type={type}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            step={type === 'number' ? '0.1' : undefined}
            min={type === 'number' ? '0' : undefined}
            max={type === 'number' ? (label.includes('Weight') ? '1' : undefined) : undefined}
            className="bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 text-sm w-24 text-right"
          />
        )}
      </div>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for change (optional)"
          className="flex-1 bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 text-sm"
        />
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="bg-em-600 hover:bg-em-700 text-white px-3 py-1.5 rounded text-sm disabled:opacity-50"
        >
          {mutation.isPending ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={() => {
            setEditing(false)
            setReason('')
          }}
          className="text-gray-400 hover:text-white px-2 py-1.5 text-sm"
        >
          Cancel
        </button>
      </div>
      {mutation.isError && (
        <p className="text-red-400 text-xs">
          Failed: {(mutation.error as Error)?.message || 'Unknown error'}
        </p>
      )}
    </div>
  )
}

// --- Read-only row for "Coming Soon" settings ---

function ReadOnlyRow({
  label,
  value,
  unit,
}: {
  label: string
  value: string | number
  unit?: string
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-700 last:border-b-0">
      <span className="text-gray-300 text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-white font-mono text-sm">
          {value}
          {unit && <span className="text-gray-500 ml-1">{unit}</span>}
        </span>
        <ComingSoonBadge />
      </div>
    </div>
  )
}

// =====================================================================
// Main Component
// =====================================================================

export default function SwarmPanel({ adminKey, config, onConfigUpdate }: SwarmPanelProps) {
  // Resolve current values from config (may be undefined if not yet in platform_config)
  const currentStrategy = config[CONFIG_KEYS.routingStrategy]
  const hasStrategy = currentStrategy !== undefined && currentStrategy !== null

  return (
    <div className="space-y-6">
      {/* ---- Status Card ---- */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="text-lg font-semibold text-white">Swarm Orchestrator</h2>
            <p className="text-gray-400 text-sm mt-1">
              Routes tasks to the best available agent in the fleet. Coordinates assignment
              strategies, priority weighting, and circuit breaker protection across all swarm agents.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-900/50 text-blue-400 border border-blue-700">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            Internal Module
          </span>
        </div>
        <p className="text-gray-500 text-xs mt-3">
          The orchestrator is compiled into the swarm binary. Settings below reflect hardcoded
          defaults from <code className="text-gray-400">orchestrator.py</code> and{' '}
          <code className="text-gray-400">config_manager.py</code>. Editable settings will appear
          once their config keys are registered in platform_config.
        </p>
      </div>

      {/* ---- Routing Strategy ---- */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-md font-semibold text-white mb-4">Routing Strategy</h3>

        {hasStrategy ? (
          <EditableRow
            label="Default Strategy"
            configKey={CONFIG_KEYS.routingStrategy}
            currentValue={currentStrategy}
            defaultValue="best_fit"
            adminKey={adminKey}
            onSuccess={onConfigUpdate}
            type="select"
            options={ROUTING_STRATEGIES.map((s) => ({ value: s.value, label: s.label }))}
          />
        ) : (
          <div className="flex items-center justify-between py-2.5 border-b border-gray-700">
            <span className="text-gray-300 text-sm">Default Strategy</span>
            <div className="flex items-center gap-2">
              <span className="text-white font-mono text-sm">BEST_FIT</span>
              <span className="text-gray-500 text-xs">(default)</span>
              <ComingSoonBadge />
            </div>
          </div>
        )}

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {ROUTING_STRATEGIES.map((strategy) => {
            const isActive =
              (hasStrategy && currentStrategy === strategy.value) ||
              (!hasStrategy && strategy.value === 'best_fit')

            return (
              <div
                key={strategy.value}
                className={`rounded-lg p-3 border ${
                  isActive
                    ? 'bg-em-900/30 border-em-600/50'
                    : 'bg-gray-700/50 border-gray-600'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-medium ${
                      isActive ? 'text-em-400' : 'text-white'
                    }`}
                  >
                    {strategy.label}
                  </span>
                  {isActive && (
                    <span className="text-xs text-em-500 font-medium">(active)</span>
                  )}
                </div>
                <p className="text-gray-400 text-xs mt-1">{strategy.description}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* ---- Priority Weights ---- */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-md font-semibold text-white mb-1">Priority Weights</h3>
        <p className="text-gray-500 text-xs mb-4">
          Multiplier applied to task score based on priority level. Higher weight = more likely to be
          routed to top agents.
        </p>

        <div className="space-y-0">
          {DEFAULT_PRIORITY_WEIGHTS.map((pw) => {
            const configKey = CONFIG_KEYS.priorityWeight(pw.key)
            const currentValue = config[configKey]
            const hasValue = currentValue !== undefined && currentValue !== null

            if (hasValue) {
              return (
                <EditableRow
                  key={pw.key}
                  label={`${pw.label} Weight`}
                  configKey={configKey}
                  currentValue={currentValue}
                  defaultValue={pw.default}
                  adminKey={adminKey}
                  onSuccess={onConfigUpdate}
                  type="number"
                />
              )
            }

            return (
              <ReadOnlyRow key={pw.key} label={`${pw.label} Weight`} value={pw.default} />
            )
          })}
        </div>

        {/* Visual weight bar */}
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-gray-500 text-xs mb-3 uppercase tracking-wide">Weight Distribution</p>
          <div className="space-y-2">
            {DEFAULT_PRIORITY_WEIGHTS.map((pw) => {
              const configKey = CONFIG_KEYS.priorityWeight(pw.key)
              const value = config[configKey] ?? pw.default
              const pct = Math.round(value * 100)

              return (
                <div key={pw.key} className="flex items-center gap-3">
                  <span className="text-gray-400 text-xs w-16 text-right">{pw.label}</span>
                  <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-em-500 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-gray-400 text-xs w-8">{value}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* ---- Fleet Overview ---- */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-md font-semibold text-white mb-4">Fleet Overview</h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          {[
            { label: 'Total Agents', value: '--' },
            { label: 'Active', value: '--' },
            { label: 'Idle', value: '--' },
            { label: 'Paused', value: '--' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-gray-700/50 border border-gray-600 rounded-lg p-3 text-center"
            >
              <div className="text-xl font-bold text-gray-500">{stat.value}</div>
              <div className="text-gray-400 text-xs mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        <div className="bg-gray-700/30 rounded p-4 text-center">
          <p className="text-gray-400 text-sm">
            Fleet telemetry will be available when the swarm status endpoints are deployed. Agent
            counts, state distribution, and task throughput will appear here.
          </p>
          <p className="text-gray-500 text-xs mt-2">
            Expected endpoint:{' '}
            <code className="text-gray-400">GET /api/v1/admin/swarm/status</code>
          </p>
        </div>
      </div>

      {/* ---- Circuit Breaker ---- */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-md font-semibold text-white">Circuit Breaker</h3>
          <ComingSoonBadge />
        </div>
        <p className="text-gray-500 text-xs mb-4">
          Protects the swarm from cascading failures. When an external dependency (EM API, autojob
          service) exceeds the failure threshold, the circuit opens and stops sending requests until
          the reset timeout elapses.
        </p>

        <div className="space-y-0">
          {(() => {
            const cbThreshold = config[CONFIG_KEYS.cbThreshold]
            const cbReset = config[CONFIG_KEYS.cbResetTimeout]
            const hasThreshold = cbThreshold !== undefined && cbThreshold !== null
            const hasReset = cbReset !== undefined && cbReset !== null

            return (
              <>
                {hasThreshold ? (
                  <EditableRow
                    label="Failure Threshold"
                    configKey={CONFIG_KEYS.cbThreshold}
                    currentValue={cbThreshold}
                    defaultValue={CIRCUIT_BREAKER_DEFAULTS.failure_threshold}
                    adminKey={adminKey}
                    onSuccess={onConfigUpdate}
                    type="number"
                  />
                ) : (
                  <ReadOnlyRow
                    label="Failure Threshold"
                    value={CIRCUIT_BREAKER_DEFAULTS.failure_threshold}
                    unit="consecutive failures"
                  />
                )}
                {hasReset ? (
                  <EditableRow
                    label="Reset Timeout"
                    configKey={CONFIG_KEYS.cbResetTimeout}
                    currentValue={cbReset}
                    defaultValue={CIRCUIT_BREAKER_DEFAULTS.reset_timeout_seconds}
                    adminKey={adminKey}
                    onSuccess={onConfigUpdate}
                    type="number"
                  />
                ) : (
                  <ReadOnlyRow
                    label="Reset Timeout"
                    value={CIRCUIT_BREAKER_DEFAULTS.reset_timeout_seconds}
                    unit="seconds"
                  />
                )}
              </>
            )
          })()}
        </div>

        {/* Circuit breaker state diagram */}
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-gray-500 text-xs mb-3 uppercase tracking-wide">State Machine</p>
          <div className="flex items-center justify-center gap-4 py-2">
            <div className="bg-green-900/30 border border-green-700/50 rounded-lg px-4 py-2 text-center">
              <div className="text-green-400 text-sm font-medium">CLOSED</div>
              <div className="text-gray-500 text-xs">Normal operation</div>
            </div>
            <div className="text-gray-500 text-xs">
              <span className="block">&rarr; {CIRCUIT_BREAKER_DEFAULTS.failure_threshold} failures &rarr;</span>
              <span className="block">&larr; success &larr;</span>
            </div>
            <div className="bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-2 text-center">
              <div className="text-red-400 text-sm font-medium">OPEN</div>
              <div className="text-gray-500 text-xs">Requests blocked</div>
            </div>
            <div className="text-gray-500 text-xs">
              <span className="block">&rarr; {CIRCUIT_BREAKER_DEFAULTS.reset_timeout_seconds}s &rarr;</span>
              <span className="block">&larr; failure &larr;</span>
            </div>
            <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg px-4 py-2 text-center">
              <div className="text-yellow-400 text-sm font-medium">HALF-OPEN</div>
              <div className="text-gray-500 text-xs">Probe request</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, ReactNode } from 'react'
import { adminGet, adminPut } from '../lib/api'

interface SettingsProps {
  adminKey: string
}

// ---------------------------------------------------------------------------
// ConfigInput — supports number, text, boolean (toggle), password, slider,
// select (dropdown), and multi-select (chips)
// ---------------------------------------------------------------------------

type InputType =
  | 'number'
  | 'text'
  | 'boolean'
  | 'password'
  | 'slider'
  | 'select'
  | 'multi-select'

interface ConfigInputProps {
  label: string
  configKey: string
  value: string | number | boolean | string[]
  type?: InputType
  suffix?: string
  adminKey: string
  onSuccess: () => void
  /** Divide display value before saving (e.g. 100 for pct display) */
  saveDivisor?: number
  /** For number inputs */
  min?: number
  max?: number
  step?: number
  /** For slider: the range */
  sliderMin?: number
  sliderMax?: number
  sliderStep?: number
  /** For select / multi-select */
  options?: string[]
  /** Read-only display (no edit button) */
  readOnly?: boolean
}

function ConfigInput({
  label,
  configKey,
  value,
  type = 'number',
  suffix,
  adminKey,
  onSuccess,
  saveDivisor,
  min,
  max,
  step,
  sliderMin = 0,
  sliderMax = 100,
  sliderStep = 1,
  options = [],
  readOnly = false,
}: ConfigInputProps) {
  const [editing, setEditing] = useState(false)
  const [newValue, setNewValue] = useState(
    Array.isArray(value) ? JSON.stringify(value) : String(value),
  )
  const [reason, setReason] = useState('')
  const [selectedChips, setSelectedChips] = useState<string[]>(
    Array.isArray(value) ? value : [],
  )

  const mutation = useMutation({
    mutationFn: () => {
      let parsedValue: unknown
      if (type === 'number' || type === 'slider') {
        parsedValue = parseFloat(newValue)
        if (saveDivisor) parsedValue = (parsedValue as number) / saveDivisor
      } else if (type === 'boolean') {
        parsedValue = newValue === 'true'
      } else if (type === 'multi-select') {
        parsedValue = selectedChips
      } else {
        parsedValue = newValue
      }
      return adminPut(`/api/v1/admin/config/${configKey}`, adminKey, {
        value: parsedValue,
        reason,
      })
    },
    onSuccess: () => {
      setEditing(false)
      setReason('')
      onSuccess()
    },
  })

  // --- Display (not editing) ---
  if (!editing) {
    const displayValue = (() => {
      if (type === 'boolean') return value ? 'Enabled' : 'Disabled'
      if (type === 'password') return value ? '********' : '(not set)'
      if (type === 'multi-select' && Array.isArray(value))
        return (
          <span className="flex flex-wrap gap-1">
            {value.map((v) => (
              <span
                key={v}
                className="bg-gray-700 text-gray-200 px-2 py-0.5 rounded text-xs"
              >
                {v}
              </span>
            ))}
          </span>
        )
      return (
        <>
          {String(value)}
          {suffix && <span className="text-gray-500 ml-1">{suffix}</span>}
        </>
      )
    })()

    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-700/60 last:border-b-0">
        <span className="text-gray-300 text-sm">{label}</span>
        <div className="flex items-center gap-3">
          {type === 'boolean' ? (
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded ${
                value
                  ? 'bg-emerald-900/40 text-emerald-400'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {value ? 'ON' : 'OFF'}
            </span>
          ) : (
            <span className="text-white font-mono text-sm">{displayValue}</span>
          )}
          {!readOnly && (
            <button
              onClick={() => {
                setNewValue(
                  Array.isArray(value) ? JSON.stringify(value) : String(value),
                )
                if (Array.isArray(value)) setSelectedChips(value)
                setEditing(true)
              }}
              className="text-em-400 hover:text-em-300 text-xs font-medium tracking-wide uppercase"
            >
              Edit
            </button>
          )}
        </div>
      </div>
    )
  }

  // --- Editing ---
  const renderInput = () => {
    if (type === 'boolean') {
      const isOn = newValue === 'true'
      return (
        <button
          type="button"
          onClick={() => setNewValue(isOn ? 'false' : 'true')}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            isOn ? 'bg-em-600' : 'bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              isOn ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      )
    }

    if (type === 'slider') {
      return (
        <div className="flex items-center gap-3 w-64">
          <input
            type="range"
            min={sliderMin}
            max={sliderMax}
            step={sliderStep}
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            className="flex-1 accent-em-500"
          />
          <span className="text-white font-mono text-sm w-16 text-right">
            {newValue}
            {suffix && <span className="text-gray-400 ml-0.5">{suffix}</span>}
          </span>
        </div>
      )
    }

    if (type === 'select') {
      return (
        <select
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          className="bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 text-sm"
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      )
    }

    if (type === 'multi-select') {
      return (
        <div className="flex flex-wrap gap-1.5">
          {options.map((opt) => {
            const selected = selectedChips.includes(opt)
            return (
              <button
                key={opt}
                type="button"
                onClick={() => {
                  setSelectedChips((prev) =>
                    selected ? prev.filter((c) => c !== opt) : [...prev, opt],
                  )
                }}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  selected
                    ? 'bg-em-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:text-gray-200'
                }`}
              >
                {opt}
              </button>
            )
          })}
        </div>
      )
    }

    if (type === 'password') {
      return (
        <input
          type="password"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          placeholder="Enter new value"
          className="bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 w-64 text-sm"
        />
      )
    }

    // number / text
    return (
      <input
        type={type}
        value={newValue}
        onChange={(e) => setNewValue(e.target.value)}
        className="bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 w-40 text-right text-sm font-mono"
        step={step ?? (type === 'number' ? 0.01 : undefined)}
        min={min}
        max={max}
      />
    )
  }

  return (
    <div className="py-3 border-b border-gray-700/60 last:border-b-0 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-gray-300 text-sm">{label}</span>
        {renderInput()}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for change (optional)"
          className="flex-1 bg-gray-700 text-white px-3 py-1.5 rounded border border-gray-600 text-xs"
        />
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="bg-em-600 hover:bg-em-500 text-white px-4 py-1.5 rounded text-xs font-medium disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={() => {
            setEditing(false)
            setNewValue(
              Array.isArray(value) ? JSON.stringify(value) : String(value),
            )
            if (Array.isArray(value)) setSelectedChips(value)
          }}
          className="text-gray-400 hover:text-white px-3 py-1.5 text-xs transition-colors"
        >
          Cancel
        </button>
      </div>
      {mutation.isError && (
        <p className="text-red-400 text-xs">
          Failed to update: {(mutation.error as Error)?.message || 'Unknown error'}
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// CollapsibleSection
// ---------------------------------------------------------------------------

function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="bg-gray-800/80 rounded-lg mb-4 border border-gray-700/40">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left group"
      >
        <div>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="px-6 pb-5">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Settings page
// ---------------------------------------------------------------------------

// All available networks and tokens for multi-select
const ALL_NETWORKS = [
  'base',
  'ethereum',
  'polygon',
  'arbitrum',
  'celo',
  'monad',
  'avalanche',
  'optimism',
  'skale',
  'solana',
]
const ALL_TOKENS = ['USDC', 'EURC', 'USDT', 'PYUSD', 'AUSD']
const NETWORK_OPTIONS = ALL_NETWORKS
const TERMINOLOGY_MODES = ['conservative', 'standard', 'crypto-native']
const AGENT_JOIN_MODES = ['optional', 'required', 'disabled']

export default function Settings({ adminKey }: SettingsProps) {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['config', adminKey],
    queryFn: () => adminGet('/api/v1/admin/config', adminKey),
    enabled: !!adminKey,
  })

  const handleSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['config'] })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-400 text-sm">Loading configuration...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800/40 rounded-lg p-6">
        <p className="text-red-400 text-sm">
          Failed to load configuration. Verify your admin key is correct.
        </p>
      </div>
    )
  }

  // Destructure config categories from API response.
  // The API returns grouped data; keys within each group omit the prefix.
  const {
    fees = {} as Record<string, any>,
    limits = {} as Record<string, any>,
    timing = {} as Record<string, any>,
    features = {} as Record<string, any>,
    payments = {} as Record<string, any>,
    treasury = {} as Record<string, any>,
    meshrelay = {} as Record<string, any>,
    chat = {} as Record<string, any>,
    mobile = {} as Record<string, any>,
    bounty = {} as Record<string, any>,
  } = data || {}

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-white mb-2">Platform Settings</h1>
      <p className="text-gray-500 text-sm mb-8">
        All 71 configuration keys. Changes take effect within 5 minutes (cache TTL).
      </p>

      {/* ---- Section 1: Fees ---- */}
      <CollapsibleSection title="Fees" subtitle="Platform fee, partial release, minimums" defaultOpen>
        <ConfigInput
          label="Platform Fee"
          configKey="fees.platform_fee_pct"
          value={Math.round((fees.platform_fee_pct ?? 0.13) * 100)}
          type="slider"
          sliderMin={0}
          sliderMax={100}
          sliderStep={1}
          saveDivisor={100}
          suffix="%"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Partial Release on Submission"
          configKey="fees.partial_release_pct"
          value={Math.round((fees.partial_release_pct ?? 0.30) * 100)}
          type="slider"
          sliderMin={0}
          sliderMax={100}
          sliderStep={1}
          saveDivisor={100}
          suffix="%"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Minimum Fee"
          configKey="fees.min_fee_usd"
          value={fees.min_fee_usd ?? 0.01}
          type="number"
          min={0.01}
          step={0.01}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Protection Fund"
          configKey="fees.protection_fund_pct"
          value={Math.round((fees.protection_fund_pct ?? 0.005) * 100 * 10) / 10}
          type="slider"
          sliderMin={0}
          sliderMax={5}
          sliderStep={0.1}
          saveDivisor={100}
          suffix="%"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 2: Bounty Limits ---- */}
      <CollapsibleSection title="Bounty Limits" subtitle="Min and max bounty amounts">
        <ConfigInput
          label="Minimum Bounty"
          configKey="bounty.min_usd"
          value={bounty.min_usd ?? limits.min_usd ?? 0.01}
          type="number"
          min={0.01}
          step={0.01}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Maximum Bounty"
          configKey="bounty.max_usd"
          value={bounty.max_usd ?? limits.max_usd ?? 10000}
          type="number"
          min={1}
          step={1}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 3: Limits ---- */}
      <CollapsibleSection title="Limits" subtitle="Task, application, and resubmission caps">
        <ConfigInput
          label="Max Resubmissions"
          configKey="limits.max_resubmissions"
          value={limits.max_resubmissions ?? 3}
          type="number"
          min={1}
          max={10}
          step={1}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Active Tasks per Agent"
          configKey="limits.max_active_tasks_per_agent"
          value={limits.max_active_tasks_per_agent ?? 100}
          type="number"
          min={1}
          max={1000}
          step={1}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Applications per Task"
          configKey="limits.max_applications_per_task"
          value={limits.max_applications_per_task ?? 50}
          type="number"
          min={1}
          max={100}
          step={1}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Active Tasks per Worker"
          configKey="limits.max_active_tasks_per_worker"
          value={limits.max_active_tasks_per_worker ?? 10}
          type="number"
          min={1}
          max={100}
          step={1}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 4: Timing ---- */}
      <CollapsibleSection title="Timing" subtitle="Approval timeouts and deadlines">
        <ConfigInput
          label="Approval Timeout"
          configKey="timeout.approval_hours"
          value={timing.approval_hours ?? 48}
          type="number"
          min={1}
          max={720}
          step={1}
          suffix="hours"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Default Task Deadline"
          configKey="timeout.task_default_hours"
          value={timing.task_default_hours ?? 24}
          type="number"
          min={1}
          max={720}
          step={1}
          suffix="hours"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Auto-release on Timeout"
          configKey="timeout.auto_release_on_timeout"
          value={timing.auto_release_on_timeout ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 5: Feature Flags ---- */}
      <CollapsibleSection title="Feature Flags" subtitle="10 platform-wide toggles" defaultOpen>
        <ConfigInput
          label="Disputes"
          configKey="feature.disputes_enabled"
          value={features.disputes_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Reputation System"
          configKey="feature.reputation_enabled"
          value={features.reputation_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Auto-matching"
          configKey="feature.auto_matching_enabled"
          value={features.auto_matching_enabled ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Partial Release"
          configKey="feature.partial_release_enabled"
          value={features.partial_release_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="WebSocket Notifications"
          configKey="feature.websocket_notifications"
          value={features.websocket_notifications ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="ERC-8004 Auto-register Worker"
          configKey="feature.erc8004_auto_register_worker_enabled"
          value={features.erc8004_auto_register_worker_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="ERC-8004 Auto-rate Agent"
          configKey="feature.erc8004_auto_rate_agent_enabled"
          value={features.erc8004_auto_rate_agent_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="ERC-8004 Dynamic Scoring"
          configKey="feature.erc8004_dynamic_scoring_enabled"
          value={features.erc8004_dynamic_scoring_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="ERC-8004 Rejection Feedback"
          configKey="feature.erc8004_rejection_feedback_enabled"
          value={features.erc8004_rejection_feedback_enabled ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="DescribeNet Integration"
          configKey="feature.describenet_enabled"
          value={features.describenet_enabled ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 6: MeshRelay ---- */}
      <CollapsibleSection title="MeshRelay" subtitle="Cross-platform relay integration">
        <ConfigInput
          label="MeshRelay Enabled"
          configKey="meshrelay.enabled"
          value={meshrelay.enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="API URL"
          configKey="meshrelay.api_url"
          value={meshrelay.api_url ?? 'https://api.meshrelay.xyz'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Webhook URL"
          configKey="meshrelay.webhook_url"
          value={meshrelay.webhook_url ?? ''}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Partner API Key"
          configKey="meshrelay.partner_api_key"
          value={meshrelay.partner_api_key ?? ''}
          type="password"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Bounties Channel"
          configKey="meshrelay.channels.bounties"
          value={meshrelay['channels.bounties'] ?? meshrelay.channels_bounties ?? '#bounties'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Agents Channel"
          configKey="meshrelay.channels.agents"
          value={meshrelay['channels.agents'] ?? meshrelay.channels_agents ?? '#Agents'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Anti-snipe Cooldown"
          configKey="meshrelay.anti_snipe_cooldown_sec"
          value={meshrelay.anti_snipe_cooldown_sec ?? 30}
          type="number"
          min={0}
          step={1}
          suffix="sec"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Claim Priority Window"
          configKey="meshrelay.claim_priority_window_sec"
          value={meshrelay.claim_priority_window_sec ?? 120}
          type="number"
          min={0}
          step={1}
          suffix="sec"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Channel Auto-expire"
          configKey="meshrelay.channel_auto_expire_minutes"
          value={meshrelay.channel_auto_expire_minutes ?? 90}
          type="number"
          min={1}
          step={1}
          suffix="min"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Bids per Auction"
          configKey="meshrelay.max_bids_per_auction"
          value={meshrelay.max_bids_per_auction ?? 20}
          type="number"
          min={1}
          step={1}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Identity Sync Interval"
          configKey="meshrelay.identity_sync_interval_sec"
          value={meshrelay.identity_sync_interval_sec ?? 300}
          type="number"
          min={10}
          step={1}
          suffix="sec"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Dynamic Channels"
          configKey="feature.meshrelay_dynamic_channels"
          value={features.meshrelay_dynamic_channels ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Relay Chains"
          configKey="feature.meshrelay_relay_chains"
          value={features.meshrelay_relay_chains ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Reverse Auctions"
          configKey="feature.meshrelay_reverse_auctions"
          value={features.meshrelay_reverse_auctions ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 7: Task Chat / IRC ---- */}
      <CollapsibleSection title="Task Chat / IRC" subtitle="Per-task IRC relay configuration">
        <ConfigInput
          label="Task Chat Enabled"
          configKey="feature.task_chat_enabled"
          value={features.task_chat_enabled ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="IRC Host"
          configKey="chat.irc_host"
          value={chat.irc_host ?? 'irc.meshrelay.xyz'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="IRC Port"
          configKey="chat.irc_port"
          value={chat.irc_port ?? 6697}
          type="number"
          min={1}
          max={65535}
          step={1}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="IRC TLS"
          configKey="chat.irc_tls"
          value={chat.irc_tls ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="IRC Nick Prefix"
          configKey="chat.irc_nick_prefix"
          value={chat.irc_nick_prefix ?? 'em-relay'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Message Length"
          configKey="chat.max_message_length"
          value={chat.max_message_length ?? 2000}
          type="number"
          min={100}
          max={10000}
          step={100}
          suffix="chars"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="History Limit"
          configKey="chat.history_limit"
          value={chat.history_limit ?? 50}
          type="number"
          min={10}
          max={1000}
          step={10}
          suffix="messages"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Channel Prefix"
          configKey="chat.channel_prefix"
          value={chat.channel_prefix ?? '#task-'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Agent Join Mode"
          configKey="chat.agent_join_mode"
          value={chat.agent_join_mode ?? 'optional'}
          type="select"
          options={AGENT_JOIN_MODES}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Retention"
          configKey="chat.retention_days"
          value={chat.retention_days ?? 90}
          type="number"
          min={1}
          max={365}
          step={1}
          suffix="days"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 8: Mobile / Apple Review ---- */}
      <CollapsibleSection title="Mobile / Apple Review" subtitle="Feature flags for app store compliance">
        <ConfigInput
          label="Terminology Mode"
          configKey="mobile.terminology_mode"
          value={mobile.terminology_mode ?? 'conservative'}
          type="select"
          options={TERMINOLOGY_MODES}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Chain Logos"
          configKey="mobile.show_chain_logos"
          value={mobile.show_chain_logos ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Chain Selector"
          configKey="mobile.show_chain_selector"
          value={mobile.show_chain_selector ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Blockchain Details"
          configKey="mobile.show_blockchain_details"
          value={mobile.show_blockchain_details ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Stablecoin Names"
          configKey="mobile.show_stablecoin_names"
          value={mobile.show_stablecoin_names ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Protocol Details"
          configKey="mobile.show_protocol_details"
          value={mobile.show_protocol_details ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Escrow Details"
          configKey="mobile.show_escrow_details"
          value={mobile.show_escrow_details ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show Onboarding Crypto Slides"
          configKey="mobile.show_onboarding_crypto_slides"
          value={mobile.show_onboarding_crypto_slides ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show FAQ Blockchain"
          configKey="mobile.show_faq_blockchain"
          value={mobile.show_faq_blockchain ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Show AI Agent References"
          configKey="mobile.show_ai_agent_references"
          value={mobile.show_ai_agent_references ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 9: Payment Networks ---- */}
      <CollapsibleSection title="Payment Networks" subtitle="x402 network and token configuration">
        <ConfigInput
          label="Supported Networks"
          configKey="x402.supported_networks"
          value={payments.supported_networks ?? ALL_NETWORKS}
          type="multi-select"
          options={NETWORK_OPTIONS}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Supported Tokens"
          configKey="x402.supported_tokens"
          value={payments.supported_tokens ?? ALL_TOKENS}
          type="multi-select"
          options={ALL_TOKENS}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Preferred Network"
          configKey="x402.preferred_network"
          value={payments.preferred_network ?? 'base'}
          type="select"
          options={ALL_NETWORKS}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Facilitator URL"
          configKey="x402.facilitator_url"
          value={payments.facilitator_url ?? 'https://facilitator.ultravioletadao.xyz'}
          type="text"
          readOnly
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>

      {/* ---- Section 10: Treasury ---- */}
      <CollapsibleSection title="Treasury" subtitle="Wallet addresses for fee collection">
        <ConfigInput
          label="Treasury Wallet"
          configKey="treasury.wallet_address"
          value={treasury.wallet_address ?? '0x0000000000000000000000000000000000000000'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Protection Fund Wallet"
          configKey="treasury.protection_fund_address"
          value={treasury.protection_fund_address ?? '0x0000000000000000000000000000000000000000'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </CollapsibleSection>
    </div>
  )
}

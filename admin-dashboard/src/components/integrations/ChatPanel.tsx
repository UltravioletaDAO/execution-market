import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { adminPut } from '../../lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatPanelProps {
  adminKey: string
  config: Record<string, any>
  onConfigUpdate: () => void
}

interface ConfigItemProps {
  label: string
  description: string
  configKey: string
  value: any
  type: 'text' | 'number' | 'toggle' | 'select'
  options?: { value: string; label: string }[]
  adminKey: string
  onSaved: () => void
}

// ---------------------------------------------------------------------------
// Config keys
// ---------------------------------------------------------------------------

const CHAT_ENABLED_KEY = 'feature.task_chat_enabled'

const IRC_CONNECTION_KEYS = [
  { key: 'chat.irc_host', label: 'IRC Host', description: 'Hostname of the IRC server', type: 'text' as const },
  { key: 'chat.irc_port', label: 'IRC Port', description: 'Port number (typically 6697 for TLS)', type: 'number' as const },
  { key: 'chat.irc_tls', label: 'TLS Enabled', description: 'Use TLS encryption for IRC connection', type: 'toggle' as const },
  { key: 'chat.irc_nick_prefix', label: 'Nick Prefix', description: 'Prefix for the relay bot nickname', type: 'text' as const },
]

const CHANNEL_KEYS = [
  { key: 'chat.channel_prefix', label: 'Channel Prefix', description: 'Prefix for task chat channels (e.g. #task-)', type: 'text' as const },
  {
    key: 'chat.agent_join_mode',
    label: 'Agent Join Mode',
    description: 'Whether agents must join task channels',
    type: 'select' as const,
    options: [
      { value: 'optional', label: 'Optional' },
      { value: 'required', label: 'Required' },
      { value: 'disabled', label: 'Disabled' },
    ],
  },
]

const LIMIT_KEYS = [
  { key: 'chat.max_message_length', label: 'Max Message Length', description: 'Maximum characters per chat message', type: 'number' as const },
  { key: 'chat.history_limit', label: 'History Limit', description: 'Number of messages kept in channel history', type: 'number' as const },
]

const RETENTION_KEYS = [
  { key: 'chat.retention_days', label: 'Retention Days', description: 'Days to retain chat logs before purge', type: 'number' as const },
]

// ---------------------------------------------------------------------------
// Editable config item
// ---------------------------------------------------------------------------

function ConfigItem({ label, description, configKey, value, type, options, adminKey, onSaved }: ConfigItemProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<string>(String(value ?? ''))
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: async () => {
      let parsed: any = draft
      if (type === 'number') parsed = Number(draft)
      if (type === 'toggle') parsed = draft === 'true'
      return adminPut(`/api/v1/admin/config/${encodeURIComponent(configKey)}`, adminKey, {
        value: parsed,
        reason: reason || undefined,
      })
    },
    onSuccess: () => {
      setEditing(false)
      setReason('')
      onSaved()
    },
  })

  const handleCancel = useCallback(() => {
    setEditing(false)
    setDraft(String(value ?? ''))
    setReason('')
    mutation.reset()
  }, [value, mutation])

  const handleEdit = useCallback(() => {
    setDraft(String(value ?? ''))
    setEditing(true)
  }, [value])

  // Display value
  const displayValue = type === 'toggle'
    ? (value ? 'Enabled' : 'Disabled')
    : type === 'select'
      ? (options?.find(o => o.value === value)?.label ?? String(value))
      : String(value ?? '--')

  if (!editing) {
    return (
      <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-gray-900/50 hover:bg-gray-900/80 transition-colors group">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-200">{label}</span>
            <code className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded font-mono">{configKey}</code>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{description}</p>
        </div>
        <div className="flex items-center gap-3 ml-4 shrink-0">
          <span className={`text-sm font-mono ${type === 'toggle' ? (value ? 'text-green-400' : 'text-gray-500') : 'text-em-400'}`}>
            {displayValue}
          </span>
          <button
            onClick={handleEdit}
            className="px-3 py-1 text-xs font-medium text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors opacity-0 group-hover:opacity-100"
          >
            Edit
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="py-3 px-4 rounded-lg bg-gray-900 border border-gray-600 space-y-3">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-gray-200">{label}</span>
          <code className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded font-mono">{configKey}</code>
        </div>
        <p className="text-xs text-gray-500">{description}</p>
      </div>

      {/* Input */}
      {type === 'text' && (
        <input
          type="text"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-em-500 focus:ring-1 focus:ring-em-500"
        />
      )}
      {type === 'number' && (
        <input
          type="number"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          className="w-48 bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-em-500 focus:ring-1 focus:ring-em-500"
        />
      )}
      {type === 'toggle' && (
        <button
          onClick={() => setDraft(draft === 'true' ? 'false' : 'true')}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            draft === 'true' ? 'bg-em-600' : 'bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              draft === 'true' ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      )}
      {type === 'select' && options && (
        <select
          value={draft}
          onChange={e => setDraft(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-em-500 focus:ring-1 focus:ring-em-500"
        >
          {options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      )}

      {/* Reason */}
      <input
        type="text"
        value={reason}
        onChange={e => setReason(e.target.value)}
        placeholder="Reason for change (optional)"
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-gray-500"
      />

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="px-4 py-1.5 text-xs font-medium bg-em-600 hover:bg-em-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
        >
          {mutation.isPending ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={handleCancel}
          disabled={mutation.isPending}
          className="px-4 py-1.5 text-xs font-medium text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors"
        >
          Cancel
        </button>
        {mutation.isError && (
          <span className="text-xs text-red-400 ml-2">
            {mutation.error instanceof Error ? mutation.error.message : 'Save failed'}
          </span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section card
// ---------------------------------------------------------------------------

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">{title}</h3>
      </div>
      <div className="p-4 space-y-2">
        {children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Master toggle
// ---------------------------------------------------------------------------

function MasterToggle({ enabled, adminKey, onSaved }: { enabled: boolean; adminKey: string; onSaved: () => void }) {
  const [reason, setReason] = useState('')
  const [showReason, setShowReason] = useState(false)

  const mutation = useMutation({
    mutationFn: async (newValue: boolean) => {
      return adminPut(`/api/v1/admin/config/${encodeURIComponent(CHAT_ENABLED_KEY)}`, adminKey, {
        value: newValue,
        reason: reason || `Chat ${newValue ? 'enabled' : 'disabled'} via admin panel`,
      })
    },
    onSuccess: () => {
      setShowReason(false)
      setReason('')
      onSaved()
    },
  })

  const handleToggle = useCallback(() => {
    if (!showReason) {
      setShowReason(true)
      return
    }
    mutation.mutate(!enabled)
  }, [showReason, enabled, mutation])

  const handleCancel = useCallback(() => {
    setShowReason(false)
    setReason('')
    mutation.reset()
  }, [mutation])

  return (
    <div className={`rounded-lg border p-5 transition-colors ${
      enabled
        ? 'bg-gray-800 border-green-700/50'
        : 'bg-gray-800 border-gray-700'
    }`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-white">Task Chat / IRC Relay</h2>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
              enabled
                ? 'bg-green-900/50 text-green-400 border border-green-700/50'
                : 'bg-gray-700 text-gray-400 border border-gray-600'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${enabled ? 'bg-green-400' : 'bg-gray-500'}`} />
              {enabled ? 'Active' : 'Disabled'}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            WebSocket-to-IRC bridge for real-time task chat between agents and workers
          </p>
          <code className="text-xs text-gray-600 font-mono">{CHAT_ENABLED_KEY}</code>
        </div>
        <button
          onClick={handleToggle}
          disabled={mutation.isPending}
          className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors shrink-0 ml-4 ${
            enabled ? 'bg-green-600 hover:bg-green-500' : 'bg-gray-600 hover:bg-gray-500'
          } ${mutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
              enabled ? 'translate-x-8' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {showReason && (
        <div className="mt-4 pt-4 border-t border-gray-700 space-y-3">
          <p className="text-sm text-yellow-400">
            {enabled
              ? 'Disabling will close all active chat channels. Existing messages are preserved per retention policy.'
              : 'Enabling will allow agents and workers to use real-time chat on tasks.'}
          </p>
          <input
            type="text"
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="Reason for change (optional)"
            className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-em-500"
          />
          <div className="flex items-center gap-2">
            <button
              onClick={() => mutation.mutate(!enabled)}
              disabled={mutation.isPending}
              className={`px-4 py-1.5 text-sm font-medium rounded transition-colors ${
                enabled
                  ? 'bg-red-700 hover:bg-red-600 text-white'
                  : 'bg-green-700 hover:bg-green-600 text-white'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {mutation.isPending ? 'Saving...' : enabled ? 'Disable Chat' : 'Enable Chat'}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
          </div>
          {mutation.isError && (
            <p className="text-xs text-red-400">
              {mutation.error instanceof Error ? mutation.error.message : 'Failed to update'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ChatPanel (exported)
// ---------------------------------------------------------------------------

export default function ChatPanel({ adminKey, config, onConfigUpdate }: ChatPanelProps) {
  const chatEnabled = config[CHAT_ENABLED_KEY] ?? false

  const renderItems = (items: { key: string; label: string; description: string; type: ConfigItemProps['type']; options?: { value: string; label: string }[] }[]) =>
    items.map(item => (
      <ConfigItem
        key={item.key}
        label={item.label}
        description={item.description}
        configKey={item.key}
        value={config[item.key]}
        type={item.type}
        options={'options' in item ? (item as any).options : undefined}
        adminKey={adminKey}
        onSaved={onConfigUpdate}
      />
    ))

  return (
    <div className="space-y-6">
      {/* Master toggle */}
      <MasterToggle enabled={chatEnabled} adminKey={adminKey} onSaved={onConfigUpdate} />

      {/* IRC Connection */}
      <SectionCard title="IRC Connection">
        {renderItems(IRC_CONNECTION_KEYS)}
      </SectionCard>

      {/* Channel Configuration */}
      <SectionCard title="Channel Configuration">
        {renderItems(CHANNEL_KEYS)}
      </SectionCard>

      {/* Limits */}
      <SectionCard title="Limits">
        {renderItems(LIMIT_KEYS)}
      </SectionCard>

      {/* Retention */}
      <SectionCard title="Retention">
        {renderItems(RETENTION_KEYS)}
      </SectionCard>
    </div>
  )
}

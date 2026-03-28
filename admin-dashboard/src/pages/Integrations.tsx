import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet, adminPut } from '../lib/api'
import ChatPanel from '../components/integrations/ChatPanel'
import SwarmPanel from '../components/integrations/SwarmPanel'
import DescribeNetPanel from '../components/integrations/DescribeNetPanel'

interface IntegrationsProps {
  adminKey: string
}

type TabId = 'meshrelay' | 'chat' | 'swarm' | 'describenet'

interface TabDef {
  id: TabId
  label: string
}

const TABS: TabDef[] = [
  { id: 'meshrelay', label: 'MeshRelay' },
  { id: 'chat', label: 'Chat' },
  { id: 'swarm', label: 'Swarm' },
  { id: 'describenet', label: 'describe.net' },
]

/* ------------------------------------------------------------------ */
/*  Reusable inline-edit input (mirrors Settings.tsx ConfigInput)      */
/* ------------------------------------------------------------------ */

function ConfigInput({
  label,
  configKey,
  value,
  type = 'text',
  suffix,
  adminKey,
  onSuccess,
}: {
  label: string
  configKey: string
  value: string | number | boolean
  type?: 'number' | 'text' | 'boolean' | 'password'
  suffix?: string
  adminKey: string
  onSuccess: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [newValue, setNewValue] = useState(String(value))
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: () => {
      const parsedValue: unknown =
        type === 'number'
          ? parseFloat(newValue)
          : type === 'boolean'
            ? newValue === 'true'
            : newValue
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

  if (!editing) {
    const displayValue =
      type === 'boolean'
        ? value
          ? 'Yes'
          : 'No'
        : type === 'password'
          ? String(value)
            ? '********'
            : '(not set)'
          : String(value)

    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-700">
        <span className="text-gray-300">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-white font-mono">
            {displayValue}
            {suffix && <span className="text-gray-400 ml-1">{suffix}</span>}
          </span>
          <button
            onClick={() => {
              setNewValue(type === 'password' ? '' : String(value))
              setEditing(true)
            }}
            className="text-em-400 hover:text-em-300 text-sm"
          >
            Edit
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="py-3 border-b border-gray-700 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-gray-300">{label}</span>
        {type === 'boolean' ? (
          <select
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            className="bg-gray-700 text-white px-3 py-1 rounded border border-gray-600"
          >
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        ) : (
          <input
            type={type === 'password' ? 'password' : type}
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            className="bg-gray-700 text-white px-3 py-1 rounded border border-gray-600 w-64 text-right"
            step={type === 'number' ? '1' : undefined}
            placeholder={type === 'password' ? 'Enter new value' : undefined}
          />
        )}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for change (optional)"
          className="flex-1 bg-gray-700 text-white px-3 py-1 rounded border border-gray-600 text-sm"
        />
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="bg-em-600 hover:bg-em-700 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
        >
          {mutation.isPending ? '...' : 'Save'}
        </button>
        <button
          onClick={() => {
            setEditing(false)
            setNewValue(String(value))
          }}
          className="text-gray-400 hover:text-white px-3 py-1 text-sm"
        >
          Cancel
        </button>
      </div>
      {mutation.isError && (
        <p className="text-red-400 text-sm">Failed to update</p>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Toggle component for master switch                                 */
/* ------------------------------------------------------------------ */

function MasterToggle({
  configKey,
  enabled,
  adminKey,
  onSuccess,
}: {
  configKey: string
  enabled: boolean
  adminKey: string
  onSuccess: () => void
}) {
  const [reason, setReason] = useState('')
  const [showReason, setShowReason] = useState(false)

  const mutation = useMutation({
    mutationFn: (newVal: boolean) =>
      adminPut(`/api/v1/admin/config/${configKey}`, adminKey, {
        value: newVal,
        reason: reason || (newVal ? 'Enable integration' : 'Disable integration'),
      }),
    onSuccess: () => {
      setShowReason(false)
      setReason('')
      onSuccess()
    },
  })

  const toggle = () => {
    if (showReason) {
      mutation.mutate(!enabled)
    } else {
      setShowReason(true)
    }
  }

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={toggle}
        disabled={mutation.isPending}
        className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none disabled:opacity-50 ${
          enabled ? 'bg-em-600' : 'bg-gray-600'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow transform transition-transform duration-200 ${
            enabled ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
      {showReason && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason (optional)"
            className="bg-gray-700 text-white px-3 py-1 rounded border border-gray-600 text-sm w-48"
            autoFocus
          />
          <button
            onClick={() => mutation.mutate(!enabled)}
            disabled={mutation.isPending}
            className="bg-em-600 hover:bg-em-700 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
          >
            {mutation.isPending ? '...' : 'Confirm'}
          </button>
          <button
            onClick={() => {
              setShowReason(false)
              setReason('')
            }}
            className="text-gray-400 hover:text-white text-sm"
          >
            Cancel
          </button>
        </div>
      )}
      {mutation.isError && (
        <span className="text-red-400 text-sm">Failed</span>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Card wrapper                                                       */
/* ------------------------------------------------------------------ */

function SectionCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      <div>{children}</div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  MeshRelay Tab                                                      */
/* ------------------------------------------------------------------ */

function MeshRelayTab({
  config,
  adminKey,
  onSuccess,
}: {
  config: Record<string, any>
  adminKey: string
  onSuccess: () => void
}) {
  const meshrelay = config.meshrelay || {}
  const features = config.features || {}
  const enabled = meshrelay.enabled ?? false

  return (
    <div>
      {/* Master toggle + status */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-white">MeshRelay Integration</h2>
            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-2.5 h-2.5 rounded-full ${
                  enabled ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span
                className={`text-sm font-medium ${
                  enabled ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {enabled ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
          <MasterToggle
            configKey="meshrelay.enabled"
            enabled={enabled}
            adminKey={adminKey}
            onSuccess={onSuccess}
          />
        </div>
        <p className="text-gray-400 text-sm mt-2">
          Forwards task/submission/payment events to MeshRelay via webhook with HMAC-SHA256 signatures.
        </p>
      </div>

      {/* Connection */}
      <SectionCard title="Connection">
        <ConfigInput
          label="API URL"
          configKey="meshrelay.api_url"
          value={meshrelay.api_url ?? 'https://api.meshrelay.xyz'}
          type="text"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Webhook URL"
          configKey="meshrelay.webhook_url"
          value={meshrelay.webhook_url ?? ''}
          type="text"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Partner API Key"
          configKey="meshrelay.partner_api_key"
          value={meshrelay.partner_api_key ?? ''}
          type="password"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
      </SectionCard>

      {/* Channels */}
      <SectionCard title="Channels">
        <ConfigInput
          label="Bounties Channel"
          configKey="meshrelay.channels.bounties"
          value={meshrelay.channels_bounties ?? meshrelay['channels.bounties'] ?? '#bounties'}
          type="text"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Agents Channel"
          configKey="meshrelay.channels.agents"
          value={meshrelay.channels_agents ?? meshrelay['channels.agents'] ?? '#Agents'}
          type="text"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
      </SectionCard>

      {/* Auction Parameters */}
      <SectionCard title="Auction Parameters">
        <ConfigInput
          label="Anti-Snipe Cooldown"
          configKey="meshrelay.anti_snipe_cooldown_sec"
          value={meshrelay.anti_snipe_cooldown_sec ?? 30}
          type="number"
          suffix="sec"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Claim Priority Window"
          configKey="meshrelay.claim_priority_window_sec"
          value={meshrelay.claim_priority_window_sec ?? 120}
          type="number"
          suffix="sec"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Channel Auto-Expire"
          configKey="meshrelay.channel_auto_expire_minutes"
          value={meshrelay.channel_auto_expire_minutes ?? 90}
          type="number"
          suffix="min"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Max Bids per Auction"
          configKey="meshrelay.max_bids_per_auction"
          value={meshrelay.max_bids_per_auction ?? 20}
          type="number"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Identity Sync Interval"
          configKey="meshrelay.identity_sync_interval_sec"
          value={meshrelay.identity_sync_interval_sec ?? 300}
          type="number"
          suffix="sec"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
      </SectionCard>

      {/* Feature Flags */}
      <SectionCard title="Feature Flags">
        <ConfigInput
          label="Dynamic Channels"
          configKey="feature.meshrelay_dynamic_channels"
          value={features.meshrelay_dynamic_channels ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Relay Chains"
          configKey="feature.meshrelay_relay_chains"
          value={features.meshrelay_relay_chains ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
        <ConfigInput
          label="Reverse Auctions"
          configKey="feature.meshrelay_reverse_auctions"
          value={features.meshrelay_reverse_auctions ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={onSuccess}
        />
      </SectionCard>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main Integrations page                                             */
/* ------------------------------------------------------------------ */

export default function Integrations({ adminKey }: IntegrationsProps) {
  const [activeTab, setActiveTab] = useState<TabId>('meshrelay')
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
    return <div className="text-gray-400">Loading configuration...</div>
  }

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load configuration. Check your admin key.
      </div>
    )
  }

  const config = data || {}

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Integrations</h1>

      {/* Tabs */}
      <div className="flex border-b border-gray-700 mb-8">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-6 py-3 text-sm font-medium transition-colors relative ${
              activeTab === tab.id
                ? 'text-em-400 border-b-2 border-em-600'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'meshrelay' && (
        <MeshRelayTab
          config={config}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      )}
      {activeTab === 'chat' && (
        <ChatPanel adminKey={adminKey} config={config} onConfigUpdate={handleSuccess} />
      )}
      {activeTab === 'swarm' && (
        <SwarmPanel adminKey={adminKey} config={config} onConfigUpdate={handleSuccess} />
      )}
      {activeTab === 'describenet' && (
        <DescribeNetPanel adminKey={adminKey} config={config} onConfigUpdate={handleSuccess} />
      )}
    </div>
  )
}

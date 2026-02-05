import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { adminGet, adminPut } from '../lib/api'

interface SettingsProps {
  adminKey: string
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
}: {
  label: string
  configKey: string
  value: string | number | boolean
  type?: 'number' | 'text' | 'boolean'
  suffix?: string
  adminKey: string
  onSuccess: () => void
  saveDivisor?: number
}) {
  const [editing, setEditing] = useState(false)
  const [newValue, setNewValue] = useState(String(value))
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: () => {
      let parsedValue: any = type === 'number' ? parseFloat(newValue) :
                         type === 'boolean' ? newValue === 'true' : newValue
      if (type === 'number' && saveDivisor) {
        parsedValue = parsedValue / saveDivisor
      }
      return adminPut(`/api/v1/admin/config/${configKey}`, adminKey, { value: parsedValue, reason })
    },
    onSuccess: () => {
      setEditing(false)
      setReason('')
      onSuccess()
    },
  })

  if (!editing) {
    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-700">
        <span className="text-gray-300">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-white font-mono">
            {type === 'boolean' ? (value ? 'Yes' : 'No') : value}
            {suffix && <span className="text-gray-400 ml-1">{suffix}</span>}
          </span>
          <button
            onClick={() => setEditing(true)}
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
            type={type}
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            className="bg-gray-700 text-white px-3 py-1 rounded border border-gray-600 w-32 text-right"
            step={type === 'number' ? '0.01' : undefined}
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

function ConfigSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span>{icon}</span>
        {title}
      </h2>
      <div>{children}</div>
    </div>
  )
}

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
      <div className="text-gray-400">Loading configuration...</div>
    )
  }

  if (error) {
    return (
      <div className="text-red-400">
        Failed to load configuration. Check your admin key.
      </div>
    )
  }

  const { fees = {}, limits = {}, timing = {}, features = {}, payments = {} } = data || {}

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-8">Platform Settings</h1>

      <ConfigSection title="Fees" icon="💰">
        <ConfigInput
          label="Platform Fee"
          configKey="fees.platform_fee_pct"
          value={(fees.platform_fee_pct || 0.08) * 100}
          saveDivisor={100}
          suffix="%"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Partial Release on Submission"
          configKey="fees.partial_release_pct"
          value={(fees.partial_release_pct || 0.30) * 100}
          saveDivisor={100}
          suffix="%"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Minimum Fee"
          configKey="fees.min_fee_usd"
          value={fees.min_fee_usd || 0.01}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </ConfigSection>

      <ConfigSection title="Bounty Limits" icon="🎯">
        <ConfigInput
          label="Minimum Bounty"
          configKey="bounty.min_usd"
          value={limits.min_usd || 0.25}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Maximum Bounty"
          configKey="bounty.max_usd"
          value={limits.max_usd || 10000}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </ConfigSection>

      <ConfigSection title="Tier-Based Fees" icon="📊">
        <div className="py-3 border-b border-gray-700">
          <div className="text-gray-300 mb-3">Fee Structure by Tier</div>
          <div className="bg-gray-700/50 rounded p-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400">
                  <th className="text-left py-1">Tier</th>
                  <th className="text-left py-1">Range</th>
                  <th className="text-left py-1">Fee</th>
                  <th className="text-left py-1">Work Deadline</th>
                  <th className="text-left py-1">Dispute Window</th>
                </tr>
              </thead>
              <tbody className="text-white">
                <tr><td className="py-1">Micro</td><td>&lt;$5</td><td>Flat $0.25</td><td>2 hours</td><td>24 hours</td></tr>
                <tr><td className="py-1">Standard</td><td>$5-$50</td><td>8%</td><td>24 hours</td><td>7 days</td></tr>
                <tr><td className="py-1">Premium</td><td>$50-$200</td><td>6%</td><td>48 hours</td><td>14 days</td></tr>
                <tr><td className="py-1">Enterprise</td><td>$200+</td><td>4%</td><td>7 days</td><td>30 days</td></tr>
              </tbody>
            </table>
          </div>
          <p className="text-gray-500 text-xs mt-2">
            Tier boundaries and timing are enforced on-chain at AUTHORIZE time.
          </p>
        </div>
        <ConfigInput
          label="Instant Payment Threshold"
          configKey="fees.instant_payment_max_usd"
          value={fees.instant_payment_max_usd || 5}
          suffix="USD"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Instant Payment Min Reputation"
          configKey="fees.instant_payment_min_reputation"
          value={fees.instant_payment_min_reputation || 90}
          suffix="%"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </ConfigSection>

      <ConfigSection title="Timeouts" icon="⏱️">
        <ConfigInput
          label="Approval Timeout"
          configKey="timeout.approval_hours"
          value={timing.approval_hours || 48}
          suffix="hours"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Default Task Deadline"
          configKey="timeout.task_default_hours"
          value={timing.task_default_hours || 24}
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
      </ConfigSection>

      <ConfigSection title="Limits" icon="🔧">
        <ConfigInput
          label="Max Resubmissions"
          configKey="limits.max_resubmissions"
          value={limits.max_resubmissions || 3}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Active Tasks per Agent"
          configKey="limits.max_active_tasks_per_agent"
          value={limits.max_active_tasks_per_agent || 100}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Max Applications per Task"
          configKey="limits.max_applications_per_task"
          value={limits.max_applications_per_task || 50}
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </ConfigSection>

      <ConfigSection title="Feature Flags" icon="🚀">
        <ConfigInput
          label="Disputes Enabled"
          configKey="feature.disputes_enabled"
          value={features.disputes_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Reputation System Enabled"
          configKey="feature.reputation_enabled"
          value={features.reputation_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Auto-matching Enabled"
          configKey="feature.auto_matching_enabled"
          value={features.auto_matching_enabled ?? false}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
        <ConfigInput
          label="Partial Release Enabled"
          configKey="feature.partial_release_enabled"
          value={features.partial_release_enabled ?? true}
          type="boolean"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </ConfigSection>

      <ConfigSection title="Payment Networks" icon="💳">
        <div className="py-3 border-b border-gray-700">
          <span className="text-gray-300">Supported Networks</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {(payments.supported_networks || ['base']).map((network: string) => (
              <span key={network} className="bg-gray-700 text-white px-3 py-1 rounded text-sm">
                {network}
              </span>
            ))}
          </div>
        </div>
        <div className="py-3 border-b border-gray-700">
          <span className="text-gray-300">Supported Tokens</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {(payments.supported_tokens || ['USDC']).map((token: string) => (
              <span key={token} className="bg-gray-700 text-white px-3 py-1 rounded text-sm">
                {token}
              </span>
            ))}
          </div>
        </div>
        <ConfigInput
          label="Preferred Network"
          configKey="x402.preferred_network"
          value={payments.preferred_network || 'base'}
          type="text"
          adminKey={adminKey}
          onSuccess={handleSuccess}
        />
      </ConfigSection>
    </div>
  )
}

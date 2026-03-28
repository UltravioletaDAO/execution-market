import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef } from 'react'
import { adminGet, adminPut, adminPost } from '../lib/api'

interface SettingsProps {
  adminKey: string
}

// -- Import types --
interface ImportChange {
  key: string
  old: any
  new: any
  status: 'updated' | 'unchanged' | 'error'
  error?: string
}

interface ImportResult {
  updated: number
  skipped: number
  changes: ImportChange[]
  errors: string[]
  dry_run: boolean
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

// =============================================================================
// Import Modal
// =============================================================================

function ImportModal({
  adminKey,
  onClose,
  onApplied,
}: {
  adminKey: string
  onClose: () => void
  onApplied: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [parsed, setParsed] = useState<Record<string, any> | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [result, setResult] = useState<ImportResult | null>(null)
  const [loading, setLoading] = useState(false)

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setParseError(null)
    setParsed(null)
    setResult(null)

    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const json = JSON.parse(ev.target?.result as string)
        // Accept either {configs: {...}} or flat {key: value}
        const configs = json.configs || json
        if (typeof configs !== 'object' || Array.isArray(configs)) {
          setParseError('JSON must be an object with key-value pairs (or {configs: {...}})')
          return
        }
        setParsed(configs)
      } catch {
        setParseError('Invalid JSON file')
      }
    }
    reader.readAsText(file)
  }

  const runImport = async (dryRun: boolean) => {
    if (!parsed) return
    setLoading(true)
    setResult(null)
    try {
      const res = await adminPost<ImportResult>(
        '/api/v1/admin/config/import',
        adminKey,
        { configs: parsed, reason: reason || undefined, dry_run: dryRun },
      )
      setResult(res)
      if (!dryRun && res.updated > 0) {
        onApplied()
      }
    } catch (err: any) {
      setResult({
        updated: 0,
        skipped: 0,
        changes: [],
        errors: [err.message || 'Import failed'],
        dry_run: dryRun,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg w-full max-w-3xl max-h-[90vh] flex flex-col border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Import Configuration</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-xl leading-none"
          >
            x
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {/* File input */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Select JSON file</label>
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              onChange={handleFile}
              className="block w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:bg-gray-700 file:text-white hover:file:bg-gray-600"
            />
          </div>

          {parseError && (
            <p className="text-red-400 text-sm">{parseError}</p>
          )}

          {/* Reason */}
          {parsed && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">Reason for change</label>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Quarterly fee adjustment"
                className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 text-sm"
              />
            </div>
          )}

          {/* Preview table (from parsed or result) */}
          {(parsed && !result) && (
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">
                {Object.keys(parsed).length} key(s) to import
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-700">
                      <th className="text-left py-2 pr-4">Key</th>
                      <th className="text-left py-2 pr-4">New Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(parsed).map(([key, val]) => (
                      <tr key={key} className="border-b border-gray-700/50">
                        <td className="py-2 pr-4 text-gray-300 font-mono text-xs">{key}</td>
                        <td className="py-2 pr-4 text-white font-mono text-xs">{JSON.stringify(val)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Result table */}
          {result && (
            <div>
              <div className="flex gap-4 mb-3 text-sm">
                <span className="text-green-400">Updated: {result.updated}</span>
                <span className="text-gray-400">Skipped: {result.skipped}</span>
                {result.errors.length > 0 && (
                  <span className="text-red-400">Errors: {result.errors.length}</span>
                )}
                {result.dry_run && (
                  <span className="text-yellow-400 font-medium">[DRY RUN]</span>
                )}
              </div>

              {result.errors.length > 0 && (
                <div className="bg-red-900/30 border border-red-700 rounded p-3 mb-3">
                  <p className="text-red-400 text-sm font-medium mb-1">Errors:</p>
                  {result.errors.map((err, i) => (
                    <p key={i} className="text-red-300 text-xs">{err}</p>
                  ))}
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-700">
                      <th className="text-left py-2 pr-4">Key</th>
                      <th className="text-left py-2 pr-4">Current</th>
                      <th className="text-left py-2 pr-4">New</th>
                      <th className="text-left py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.changes.map((ch) => (
                      <tr
                        key={ch.key}
                        className={`border-b border-gray-700/50 ${
                          ch.status === 'updated'
                            ? 'bg-green-900/10'
                            : ch.status === 'error'
                            ? 'bg-red-900/10'
                            : ''
                        }`}
                      >
                        <td className="py-2 pr-4 text-gray-300 font-mono text-xs">{ch.key}</td>
                        <td className="py-2 pr-4 font-mono text-xs text-gray-400">
                          {ch.old !== null && ch.old !== undefined ? JSON.stringify(ch.old) : '--'}
                        </td>
                        <td className={`py-2 pr-4 font-mono text-xs ${
                          ch.status === 'updated' ? 'text-green-400' : 'text-white'
                        }`}>
                          {JSON.stringify(ch.new)}
                        </td>
                        <td className="py-2 text-xs">
                          {ch.status === 'updated' && (
                            <span className="text-green-400">changed</span>
                          )}
                          {ch.status === 'unchanged' && (
                            <span className="text-gray-500">same</span>
                          )}
                          {ch.status === 'error' && (
                            <span className="text-red-400" title={ch.error}>error</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white"
          >
            Close
          </button>
          {parsed && (
            <>
              <button
                onClick={() => runImport(true)}
                disabled={loading}
                className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded disabled:opacity-50"
              >
                {loading ? '...' : 'Dry Run'}
              </button>
              <button
                onClick={() => {
                  if (window.confirm('Apply all changes? This will update the live platform configuration.')) {
                    runImport(false)
                  }
                }}
                disabled={loading}
                className="px-4 py-2 text-sm bg-em-600 hover:bg-em-700 text-white rounded disabled:opacity-50"
              >
                {loading ? '...' : 'Apply Changes'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Config Toolbar (Export / Import)
// =============================================================================

function ConfigToolbar({ adminKey, onImported }: { adminKey: string; onImported: () => void }) {
  const [exporting, setExporting] = useState(false)
  const [showImport, setShowImport] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const data = await adminGet<{ configs: Record<string, any>; exported_at: string; total: number }>(
        '/api/v1/admin/config/export',
        adminKey,
      )
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const date = new Date().toISOString().slice(0, 10)
      const a = document.createElement('a')
      a.href = url
      a.download = `em-config-${date}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
      alert('Failed to export configuration. Check console for details.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <div className="flex items-center gap-3 mb-6 bg-gray-800 rounded-lg p-4 border border-gray-700">
        <span className="text-gray-400 text-sm mr-auto">Bulk Operations</span>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded border border-gray-600 disabled:opacity-50"
        >
          {exporting ? 'Exporting...' : 'Export Config'}
        </button>
        <button
          onClick={() => setShowImport(true)}
          className="px-4 py-2 text-sm bg-em-600 hover:bg-em-700 text-white rounded disabled:opacity-50"
        >
          Import Config
        </button>
      </div>
      {showImport && (
        <ImportModal
          adminKey={adminKey}
          onClose={() => setShowImport(false)}
          onApplied={() => {
            onImported()
          }}
        />
      )}
    </>
  )
}

// =============================================================================
// Settings Page
// =============================================================================

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

      <ConfigToolbar adminKey={adminKey} onImported={handleSuccess} />

      <ConfigSection title="Fees" icon="$">
        <ConfigInput
          label="Platform Fee"
          configKey="fees.platform_fee_pct"
          value={(fees.platform_fee_pct || 0.13) * 100}
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

      <ConfigSection title="Bounty Limits" icon="#">
        <ConfigInput
          label="Minimum Bounty"
          configKey="bounty.min_usd"
          value={limits.min_usd || 0.01}
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

      <ConfigSection title="Tier-Based Fees" icon="%">
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

      <ConfigSection title="Timeouts" icon="~">
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

      <ConfigSection title="Limits" icon="=">
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

      <ConfigSection title="Feature Flags" icon="*">
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

      <ConfigSection title="Payment Networks" icon="@">
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

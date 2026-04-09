/**
 * DisputesPage: Inbox for human arbiters to review and resolve
 * Ring 2 escalated disputes.
 *
 * Route: /disputes
 *
 * Shows:
 *   - List of open disputes with arbiter verdict snapshot
 *   - Filter by category
 *   - Dispute detail view with ring scores + evidence hashes
 *   - Resolve form (release / refund / split)
 */

import { useCallback, useEffect, useState } from 'react'
import { ArbiterVerdictBadge } from '../components/ArbiterVerdictBadge'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

const API_KEY = import.meta.env.VITE_API_KEY as string | undefined

// --------------------------------------------------------------------------
// Types
// --------------------------------------------------------------------------

interface DisputeSummary {
  id: string
  task_id: string
  submission_id: string | null
  agent_id: string
  executor_id: string | null
  reason: string
  description: string
  status: string
  priority: number
  escalation_tier: number
  disputed_amount_usdc: number | null
  created_at: string
  response_deadline: string | null
  resolved_at: string | null
  winner: string | null
}

interface RingScoreEntry {
  ring?: string
  provider?: string
  model?: string
  score?: number
  decision?: string
  confidence?: number
  reason?: string | null
}

interface ArbiterVerdictData {
  decision?: string
  tier?: string
  aggregate_score?: number
  confidence?: number
  reason?: string | null
  disagreement?: boolean
  ring_scores?: RingScoreEntry[]
  evidence_hash?: string
  commitment_hash?: string
}

interface DisputeDetail extends DisputeSummary {
  arbiter_verdict_data: ArbiterVerdictData | null
  agent_evidence: Record<string, unknown> | null
  executor_response: string | null
  executor_evidence: Record<string, unknown> | null
  agent_refund_usdc: number | null
  executor_payout_usdc: number | null
  resolution_notes: string | null
  metadata: Record<string, unknown> | null
}

type VerdictChoice = 'release' | 'refund' | 'split'

// --------------------------------------------------------------------------
// API helpers
// --------------------------------------------------------------------------

function buildHeaders(): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (API_KEY) headers['x-api-key'] = API_KEY
  return headers
}

async function fetchAvailableDisputes(
  category: string | null,
): Promise<DisputeSummary[]> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : ''
  const res = await fetch(
    `${API_BASE_URL}/api/v1/disputes/available${qs}`,
    { headers: buildHeaders() },
  )
  if (!res.ok) throw new Error(`Failed to list disputes (${res.status})`)
  const data = await res.json()
  return data.items ?? []
}

async function fetchDisputeDetail(id: string): Promise<DisputeDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/disputes/${id}`, {
    headers: buildHeaders(),
  })
  if (!res.ok) throw new Error(`Failed to fetch dispute (${res.status})`)
  return res.json()
}

async function resolveDispute(
  id: string,
  body: { verdict: VerdictChoice; reason: string; split_pct?: number },
): Promise<{
  success: boolean
  agent_refund_usdc: number
  executor_payout_usdc: number
  action_triggered: string | null
}> {
  const res = await fetch(`${API_BASE_URL}/api/v1/disputes/${id}/resolve`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// --------------------------------------------------------------------------
// Subcomponents
// --------------------------------------------------------------------------

function DisputeRow({
  dispute,
  selected,
  onClick,
}: {
  dispute: DisputeSummary
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left p-3 border rounded-lg transition-colors ${
        selected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-xs text-gray-500 truncate">
            {dispute.id}
          </div>
          <div className="text-sm font-medium text-gray-900 mt-1 line-clamp-2">
            {dispute.description || '(no description)'}
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <span className="font-mono">{dispute.reason}</span>
            <span>·</span>
            <span>P{dispute.priority}</span>
            {dispute.disputed_amount_usdc != null && (
              <>
                <span>·</span>
                <span className="font-mono">
                  ${dispute.disputed_amount_usdc.toFixed(2)}
                </span>
              </>
            )}
          </div>
        </div>
        <span className="text-[10px] uppercase tracking-wide text-gray-500 whitespace-nowrap">
          tier {dispute.escalation_tier}
        </span>
      </div>
    </button>
  )
}

function ResolveForm({
  disputeId,
  disputedAmount,
  onResolved,
}: {
  disputeId: string
  disputedAmount: number
  onResolved: () => void
}) {
  const [verdict, setVerdict] = useState<VerdictChoice>('release')
  const [reason, setReason] = useState('')
  const [splitPct, setSplitPct] = useState<number>(50)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const handleSubmit = useCallback(async () => {
    if (reason.length < 5) {
      setError('Reason must be at least 5 characters')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const res = await resolveDispute(disputeId, {
        verdict,
        reason,
        split_pct: verdict === 'split' ? splitPct : undefined,
      })
      setResult(
        `Resolved: agent $${res.agent_refund_usdc.toFixed(4)}, worker $${res.executor_payout_usdc.toFixed(4)} (${res.action_triggered || 'pending'})`,
      )
      onResolved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Resolve failed')
    } finally {
      setSubmitting(false)
    }
  }, [reason, verdict, splitPct, disputeId, onResolved])

  const previewAgent =
    verdict === 'refund'
      ? disputedAmount
      : verdict === 'split'
        ? (disputedAmount * splitPct) / 100
        : 0
  const previewWorker = disputedAmount - previewAgent

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-white">
      <h3 className="text-sm font-semibold text-gray-900">Resolve dispute</h3>

      <div className="grid grid-cols-3 gap-2">
        {(['release', 'refund', 'split'] as const).map((v) => {
          const selected = verdict === v
          const labels = {
            release: 'Release (worker wins)',
            refund: 'Refund (agent wins)',
            split: 'Split (partial)',
          }
          return (
            <button
              type="button"
              key={v}
              onClick={() => setVerdict(v)}
              className={`text-left p-2 border rounded text-xs transition-colors ${
                selected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <div className="font-semibold text-gray-900">{v}</div>
              <div className="text-gray-600">{labels[v]}</div>
            </button>
          )
        })}
      </div>

      {verdict === 'split' && (
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Agent refund % ({splitPct}%)
          </label>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={splitPct}
            onChange={(e) => setSplitPct(parseInt(e.target.value, 10))}
            className="w-full"
          />
        </div>
      )}

      <div className="text-xs text-gray-600 font-mono">
        Preview: agent ${previewAgent.toFixed(4)} · worker $
        {previewWorker.toFixed(4)}
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Reason (5-2000 chars, stored in audit trail)
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
          placeholder="Explain your decision..."
          maxLength={2000}
        />
      </div>

      {error && (
        <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}
      {result && (
        <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded p-2">
          {result}
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={submitting || reason.length < 5}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-semibold"
      >
        {submitting ? 'Submitting...' : 'Submit verdict'}
      </button>
    </div>
  )
}

function DisputeDetailPanel({
  dispute,
  onResolved,
}: {
  dispute: DisputeDetail
  onResolved: () => void
}) {
  const vdata = dispute.arbiter_verdict_data
  const disputedAmount = dispute.disputed_amount_usdc ?? 0
  const isResolved = !!dispute.resolved_at

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs text-gray-500 font-mono">{dispute.id}</div>
            <h2 className="text-lg font-semibold text-gray-900 mt-1">
              Dispute
            </h2>
          </div>
          {vdata?.decision && (
            <ArbiterVerdictBadge
              verdict={
                vdata.decision as 'pass' | 'fail' | 'inconclusive' | 'skipped'
              }
              tier={vdata.tier as 'cheap' | 'standard' | 'max' | null}
              score={vdata.aggregate_score}
              confidence={vdata.confidence}
              size="lg"
            />
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-xs text-gray-500">Task</div>
            <div className="font-mono text-xs truncate">{dispute.task_id}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Submission</div>
            <div className="font-mono text-xs truncate">
              {dispute.submission_id ?? '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Reason</div>
            <div className="text-sm">{dispute.reason}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Status</div>
            <div className="text-sm">{dispute.status}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Disputed amount</div>
            <div className="text-sm font-mono">
              ${disputedAmount.toFixed(4)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Priority</div>
            <div className="text-sm">{dispute.priority}</div>
          </div>
        </div>

        <div>
          <div className="text-xs text-gray-500 mb-1">Description</div>
          <div className="text-sm text-gray-800 whitespace-pre-wrap">
            {dispute.description}
          </div>
        </div>

        {vdata?.reason && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Arbiter reason</div>
            <div className="text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded p-2">
              {vdata.reason}
            </div>
          </div>
        )}

        {vdata?.disagreement && (
          <div className="text-xs text-amber-700 font-medium bg-amber-50 border border-amber-200 rounded p-2">
            Ring disagreement detected — rings could not reach consensus
          </div>
        )}

        {Array.isArray(vdata?.ring_scores) && vdata.ring_scores.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Ring breakdown</div>
            <div className="space-y-1">
              {vdata.ring_scores.map((rs, i) => (
                <div
                  key={`${rs.ring}-${i}`}
                  className="flex items-center justify-between text-xs border-b border-gray-100 py-1 last:border-0"
                >
                  <span className="text-gray-600">
                    {rs.ring} · {rs.provider ?? '?'}/{rs.model ?? '?'}
                  </span>
                  <span className="font-mono text-gray-500">
                    {typeof rs.score === 'number'
                      ? `${Math.round(rs.score * 100)}%`
                      : '—'}{' '}
                    {rs.decision ? `· ${rs.decision}` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {vdata?.evidence_hash && (
          <div className="text-[10px] font-mono text-gray-400 break-all">
            evidence_hash: {vdata.evidence_hash}
          </div>
        )}
      </div>

      {!isResolved ? (
        <ResolveForm
          disputeId={dispute.id}
          disputedAmount={disputedAmount}
          onResolved={onResolved}
        />
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
          <div className="font-semibold text-green-900">
            Resolved: {dispute.winner}
          </div>
          {dispute.resolution_notes && (
            <div className="text-green-800 mt-1">
              {dispute.resolution_notes}
            </div>
          )}
          <div className="text-xs text-green-700 mt-2 font-mono">
            Agent: ${(dispute.agent_refund_usdc ?? 0).toFixed(4)} · Worker: $
            {(dispute.executor_payout_usdc ?? 0).toFixed(4)}
          </div>
        </div>
      )}
    </div>
  )
}

// --------------------------------------------------------------------------
// Main page
// --------------------------------------------------------------------------

export default function DisputesPage() {
  const [disputes, setDisputes] = useState<DisputeSummary[]>([])
  const [selected, setSelected] = useState<DisputeDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const items = await fetchAvailableDisputes(null)
      setDisputes(items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load disputes')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleSelect = useCallback(async (id: string) => {
    try {
      const detail = await fetchDisputeDetail(id)
      setSelected(detail)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch dispute')
    }
  }, [])

  const handleResolved = useCallback(() => {
    // Refresh both list and detail after a successful resolve
    load()
    if (selected) {
      fetchDisputeDetail(selected.id).then(setSelected).catch(() => {})
    }
  }, [load, selected])

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Disputes</h1>
        <p className="text-sm text-gray-600 mt-1">
          Ring 2 escalated disputes awaiting human arbiter review
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: list */}
        <div className="lg:col-span-1 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              {loading ? 'Loading...' : `${disputes.length} open`}
            </h2>
            <button
              type="button"
              onClick={load}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              Refresh
            </button>
          </div>
          {disputes.length === 0 && !loading ? (
            <div className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded p-4">
              No open disputes
            </div>
          ) : (
            disputes.map((d) => (
              <DisputeRow
                key={d.id}
                dispute={d}
                selected={selected?.id === d.id}
                onClick={() => handleSelect(d.id)}
              />
            ))
          )}
        </div>

        {/* Right: detail + resolve form */}
        <div className="lg:col-span-2">
          {selected ? (
            <DisputeDetailPanel
              dispute={selected}
              onResolved={handleResolved}
            />
          ) : (
            <div className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
              Select a dispute from the list to see details and resolve it
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

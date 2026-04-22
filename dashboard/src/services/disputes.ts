/**
 * Disputes API service.
 *
 * Wraps POST /api/v1/disputes (Phase 3.1, INC-2026-04-22) — publisher-
 * initiated dispute creation. Replaces the silent Ring 2 auto-escalation
 * that was removed in Phase 1.
 *
 * Auth: the backend requires ERC-8128 wallet signing (parity with /resolve).
 * We attach the Supabase JWT via buildAuthHeaders for now; a dedicated
 * wallet-signing layer is tracked separately.
 */
import { buildAuthHeaders } from '../lib/auth'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

export type DisputeReason =
  | 'incomplete_work'
  | 'poor_quality'
  | 'wrong_deliverable'
  | 'late_delivery'
  | 'fake_evidence'
  | 'no_response'
  | 'payment_issue'
  | 'unfair_rejection'
  | 'other'

export interface CreateDisputeRequest {
  submission_id: string
  reason: DisputeReason
  description: string
}

export interface CreateDisputeResponse {
  id: string
  task_id: string
  submission_id: string | null
  reason: string
  description: string
  status: string
  escalation_tier: number
  disputed_amount_usdc: number | null
  created_at: string
}

export async function createDispute(
  body: CreateDisputeRequest,
): Promise<CreateDisputeResponse> {
  const headers = await buildAuthHeaders({ 'Content-Type': 'application/json' })
  const res = await fetch(`${API_BASE_URL}/api/v1/disputes`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

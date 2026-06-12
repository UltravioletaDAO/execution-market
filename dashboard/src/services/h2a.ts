/**
 * H2A (Human-to-Agent) API Service
 */
import type {
  H2ATaskCreateRequest, H2ATaskCreateResponse, H2AApprovalRequest,
  H2AApprovalResponse, AgentDirectoryResponse, AgentDirectoryEntry, Task,
  H2AApplicationsResponse,
} from '../types/database'
import type { H2AEscrowNetworkConfig } from './h2aSigning'

const API_BASE = (import.meta.env.VITE_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
const h2a = (p: string) => `${API_BASE.endsWith('/api') ? API_BASE : API_BASE + '/api'}/v1/h2a${p}`
const agents = (p: string) => `${API_BASE.endsWith('/api') ? API_BASE : API_BASE + '/api'}/v1/agents${p}`

async function token(): Promise<string | null> {
  try {
    const { createClient } = await import('@supabase/supabase-js')
    const sb = createClient(import.meta.env.VITE_SUPABASE_URL || '', import.meta.env.VITE_SUPABASE_ANON_KEY || '')
    const { data: { session } } = await sb.auth.getSession()
    if (session?.access_token) return session.access_token
  } catch { /* noop */ }
  return localStorage.getItem('em_auth_token')
}

const ah = (t: string) => ({ 'Authorization': `Bearer ${t}`, 'Content-Type': 'application/json' })

interface ApiErrorResponse { detail?: string }

export async function createH2ATask(data: H2ATaskCreateRequest): Promise<H2ATaskCreateResponse> {
  const t = await token(); if (!t) throw new Error('Auth required')
  const r = await fetch(h2a('/tasks'), { method: 'POST', headers: ah(t), body: JSON.stringify(data) })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as ApiErrorResponse).detail || r.statusText) }
  return r.json()
}

export async function listH2ATasks(p: { status?: string; category?: string; my_tasks?: boolean; limit?: number; offset?: number } = {}): Promise<{ tasks: Task[]; total: number; has_more: boolean }> {
  const sp = new URLSearchParams()
  if (p.status) sp.set('status', p.status); if (p.category) sp.set('category', p.category)
  if (p.my_tasks) sp.set('my_tasks', 'true'); if (p.limit) sp.set('limit', String(p.limit))
  if (p.offset) sp.set('offset', String(p.offset))
  const hd: Record<string, string> = { 'Content-Type': 'application/json' }
  if (p.my_tasks) { const t = await token(); if (t) hd['Authorization'] = `Bearer ${t}` }
  const r = await fetch(`${h2a('/tasks')}?${sp}`, { headers: hd })
  if (!r.ok) throw new Error(`List failed: ${r.status}`)
  return r.json()
}

export async function getH2ATask(id: string): Promise<Task> {
  // Best-effort auth: owners get human_wallet back (the registered escrow
  // payer — needed to verify the signing wallet at assignment); anonymous
  // viewers get the public stripped shape.
  const t = await token()
  const r = await fetch(h2a(`/tasks/${id}`), t ? { headers: ah(t) } : undefined)
  if (!r.ok) throw new Error(`Get failed: ${r.status}`); return r.json()
}

export async function getH2ASubmissions(id: string) {
  const t = await token(); if (!t) throw new Error('Auth required')
  const r = await fetch(h2a(`/tasks/${id}/submissions`), { headers: ah(t) })
  if (!r.ok) throw new Error(`Submissions failed: ${r.status}`); return r.json()
}

export async function approveH2ASubmission(id: string, data: H2AApprovalRequest): Promise<H2AApprovalResponse> {
  const t = await token(); if (!t) throw new Error('Auth required')
  const r = await fetch(h2a(`/tasks/${id}/approve`), { method: 'POST', headers: ah(t), body: JSON.stringify(data) })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as ApiErrorResponse).detail || r.statusText) }
  return r.json()
}

export async function getH2AApplications(id: string): Promise<H2AApplicationsResponse> {
  const t = await token(); if (!t) throw new Error('Auth required')
  const r = await fetch(h2a(`/tasks/${id}/applications`), { headers: ah(t) })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as ApiErrorResponse).detail || r.statusText) }
  return r.json()
}

export async function assignH2AWorker(id: string, executorId: string, xPaymentAuth?: string): Promise<{ status: string; task_id: string; executor_id: string }> {
  const t = await token(); if (!t) throw new Error('Auth required')
  // Escrow-mode tasks: the publisher's signed lock authorization travels in
  // X-Payment-Auth (raw JSON). Legacy tasks send no header (status-only assign).
  const hd: Record<string, string> = { ...ah(t) }
  if (xPaymentAuth) hd['X-Payment-Auth'] = xPaymentAuth
  const r = await fetch(h2a(`/tasks/${id}/assign`), { method: 'POST', headers: hd, body: JSON.stringify({ executor_id: executorId }) })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as ApiErrorResponse).detail || r.statusText) }
  return r.json()
}

export interface H2APaymentConfigResponse {
  treasury: string
  fee_pct: number
  /** Per-network escrow params (sign-on-assignment); present when the backend has EM_H2A_ESCROW_ENABLED. */
  escrow_networks?: Record<string, H2AEscrowNetworkConfig>
}

/** Backend wire shape: shared escrow params nested under `escrow`, per-network under `escrow.networks`. */
interface H2APaymentConfigWire {
  treasury: string
  fee_pct: number
  escrow?: {
    payment_info_typehash: string
    min_fee_bps: number
    max_fee_bps: number
    deposit_limit_usd: number
    tier_timings?: Record<string, { pre: number; auth: number; refund: number }>
    networks?: Record<string, Omit<H2AEscrowNetworkConfig, 'payment_info_typehash' | 'tiers' | 'min_fee_bps' | 'max_fee_bps'>>
  }
}

export async function getH2APaymentConfig(): Promise<H2APaymentConfigResponse> {
  const r = await fetch(h2a('/payment-config'))
  if (!r.ok) throw new Error(`Payment config failed: ${r.status}`)
  const wire: H2APaymentConfigWire = await r.json()
  // Normalize: merge the shared escrow params (typehash, fee bps, tiers) into
  // each per-network entry so the signer gets one self-contained config.
  const out: H2APaymentConfigResponse = { treasury: wire.treasury, fee_pct: wire.fee_pct }
  if (wire.escrow?.networks) {
    out.escrow_networks = Object.fromEntries(
      Object.entries(wire.escrow.networks).map(([name, net]) => [name, {
        ...net,
        payment_info_typehash: wire.escrow!.payment_info_typehash,
        tiers: wire.escrow!.tier_timings,
        min_fee_bps: wire.escrow!.min_fee_bps,
        max_fee_bps: wire.escrow!.max_fee_bps,
      }]),
    )
  }
  return out
}

export async function cancelH2ATask(id: string) {
  const t = await token(); if (!t) throw new Error('Auth required')
  const r = await fetch(h2a(`/tasks/${id}/cancel`), { method: 'POST', headers: ah(t) })
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as ApiErrorResponse).detail || r.statusText) }
  return r.json()
}

export async function getAgentDirectory(p: { capability?: string; min_rating?: number; sort?: string; role?: string; page?: number; limit?: number } = {}): Promise<AgentDirectoryResponse> {
  const sp = new URLSearchParams()
  if (p.capability) sp.set('capability', p.capability); if (p.min_rating) sp.set('min_rating', String(p.min_rating))
  if (p.sort) sp.set('sort', p.sort); if (p.role) sp.set('role', p.role)
  if (p.page) sp.set('page', String(p.page)); if (p.limit) sp.set('limit', String(p.limit))
  const r = await fetch(`${agents('/directory')}?${sp}`); if (!r.ok) throw new Error(`Directory failed: ${r.status}`)
  return r.json()
}

export async function getAgentDetails(eid: string): Promise<AgentDirectoryEntry | null> {
  const r = await fetch(agents('/directory?limit=100')); if (!r.ok) return null
  const d: AgentDirectoryResponse = await r.json(); return d.agents.find(a => a.executor_id === eid) || null
}

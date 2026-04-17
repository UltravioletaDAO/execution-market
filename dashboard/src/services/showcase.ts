/**
 * Showcase service — Proof Wall evidence feed client.
 *
 * Thin wrapper over GET /api/v1/showcase/evidence. Keeps types in sync with
 * mcp_server/api/routers/showcase.py and converts snake_case → camelCase
 * at the boundary so React components stay idiomatic.
 */

import { toCamelCase } from './api'

// ============================ Types ============================

export type ShowcaseOrder = 'recent' | 'highest_paid' | 'most_verified'

export interface VerificationBadges {
  gpsVerified: boolean
  exifVerified: boolean
  timestampVerified: boolean
  worldIdVerified: boolean
}

export interface ShowcaseExecutor {
  displayName: string
  avatarUrl: string | null
  rating: number | null
}

export interface ShowcaseEvidencePreview {
  primaryImageUrl: string
  imageCount: number
  blurhash: string | null
  verification: VerificationBadges
}

export interface ShowcaseEvidence {
  id: string
  taskTitle: string
  taskDescription: string
  category: string
  bountyUsd: number
  paymentToken: string | null
  paymentNetwork: string | null
  paidAt: string
  completedAt: string | null
  executor: ShowcaseExecutor
  evidence: ShowcaseEvidencePreview
}

export interface ShowcaseResponse {
  items: ShowcaseEvidence[]
  nextCursor: string | null
  generatedAt: string
}

export interface FetchShowcaseParams {
  limit?: number
  category?: string
  network?: string
  order?: ShowcaseOrder
  cursor?: string
  signal?: AbortSignal
}

// ============================ URL builder ============================

const API_BASE = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

function buildShowcaseUrl(params: FetchShowcaseParams): string {
  const path = API_BASE.endsWith('/api')
    ? `${API_BASE}/v1/showcase/evidence`
    : `${API_BASE}/api/v1/showcase/evidence`

  const qs = new URLSearchParams()
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  if (params.category) qs.set('category', params.category)
  if (params.network) qs.set('network', params.network)
  if (params.order) qs.set('order', params.order)
  if (params.cursor) qs.set('cursor', params.cursor)

  const query = qs.toString()
  return query ? `${path}?${query}` : path
}

// ============================ Client ============================

/**
 * Fetch one page of showcase evidence.
 *
 * Backend caches 60s and emits Cache-Control + ETag, so refetching is cheap.
 * Pass `cursor` from a previous response's `nextCursor` to paginate.
 */
export async function fetchShowcase(
  params: FetchShowcaseParams = {}
): Promise<ShowcaseResponse> {
  const url = buildShowcaseUrl(params)

  const response = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: params.signal,
  })

  if (!response.ok) {
    throw new Error(
      `Showcase fetch failed (${response.status}): ${await response.text().catch(() => '')}`
    )
  }

  const raw = await response.json()
  return toCamelCase<ShowcaseResponse>(raw)
}

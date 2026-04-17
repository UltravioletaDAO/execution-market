/**
 * useShowcaseData — TanStack Query hook for the Proof Wall carousel.
 *
 * Wraps fetchShowcase() from services/showcase.ts. The backend already caches
 * 60s in-process and emits Cache-Control + ETag, so the browser is doubly
 * cheap: HTTP cache + React Query staleTime keeps the carousel fresh without
 * hammering the API.
 */

import { useQuery } from '@tanstack/react-query'
import { fetchShowcase } from '../services/showcase'
import type {
  FetchShowcaseParams,
  ShowcaseResponse,
  ShowcaseEvidence,
  ShowcaseOrder,
} from '../services/showcase'

export type UseShowcaseDataOptions = Pick<
  FetchShowcaseParams,
  'limit' | 'category' | 'network' | 'order' | 'cursor'
> & {
  /** Disable the query without unmounting the component. */
  enabled?: boolean
}

function buildQueryKey(opts: UseShowcaseDataOptions): readonly unknown[] {
  return [
    'showcase',
    'evidence',
    {
      limit: opts.limit ?? null,
      category: opts.category ?? null,
      network: opts.network ?? null,
      order: opts.order ?? null,
      cursor: opts.cursor ?? null,
    },
  ] as const
}

export function useShowcaseData(options: UseShowcaseDataOptions = {}) {
  const { enabled = true, ...params } = options

  return useQuery<ShowcaseResponse>({
    queryKey: buildQueryKey(options),
    queryFn: ({ signal }) => fetchShowcase({ ...params, signal }),
    enabled,
    staleTime: 5 * 60_000, // 5 min — matches backend TTL + SWR window
    gcTime: 15 * 60_000,
    refetchOnWindowFocus: false,
    retry: 1,
  })
}

export type { ShowcaseEvidence, ShowcaseResponse, ShowcaseOrder }

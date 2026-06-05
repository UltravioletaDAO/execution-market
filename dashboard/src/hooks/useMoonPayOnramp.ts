/**
 * useMoonPayOnramp — watch a wallet (Base by default, or Solana) during an in-progress MoonPay buy.
 *
 * Phase 4.9 of MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO. Once the agent taps Apple
 * Pay in the headless overlay (Phase 4.8), MoonPay needs anywhere from 5s
 * to several minutes to deliver USDC to the destination wallet. The hook
 * races two sources so we surface "balance arrived" as fast as possible:
 *
 *   1. RPC poll — `getTokenAccountsByOwner` + USDC mint, every 1.5s. Wins
 *      when the chain reflects the SPL transfer before MoonPay's webhook
 *      reaches our backend (common on Solana mainnet — block times ~400ms,
 *      webhooks often lag 5–15s).
 *   2. Supabase Realtime — `moonpay_transactions` filtered by wallet. Wins
 *      when the user is on a flaky Solana RPC but our webhook fires (rare,
 *      but the safety net for the demo: a single event drives the UI).
 *
 * The hook stays *observation-only*: it never decides on its own that the
 * agent can publish a task. The caller compares `balance >= targetUsdc`
 * and reacts (e.g. resume the publish_task flow, fire `onComplete`). This
 * matches the migration 109 contract that `moonpay_transactions` is a
 * mirror, not an authority.
 *
 * Stop conditions (in order):
 *   - `enabled === false` ............ caller wants idle
 *   - `balance >= targetUsdc` ........ on-chain says "enough"
 *   - newest Realtime row reaches a terminal status ('completed'/'failed')
 *
 * After any stop, polling and the channel subscription are torn down so we
 * don't leak intervals during the 30+ minute demo session.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { readSolanaUsdcBalance, resolveSolanaRpc } from '../services/solana-balance'
import { readEvmUsdcBalance, resolveEvmRpc } from '../services/evm-balance'

const DEFAULT_POLL_MS = 1500

type TerminalStatus = 'completed' | 'failed'
type ActiveStatus =
  | 'pending'
  | 'waitingPayment'
  | 'waitingAuthorization'
  | 'waitingForDeposit'
  | 'pendingAuthorization'
  | 'processing'
type TxnStatus = TerminalStatus | ActiveStatus | string

export interface MoonPayTransactionRow {
  id: string
  moonpay_transaction_id: string | null
  external_customer_id: string | null
  wallet_address: string
  crypto_currency_code: string
  base_amount: number | null
  quote_amount: number | null
  fee_amount: number | null
  status: TxnStatus
  crypto_transaction_id: string | null
  created_at: string
  updated_at: string
}

export type OnrampPhase =
  | 'idle'
  | 'watching'
  | 'arrived'
  | 'failed'
  | 'cancelled'

export interface UseMoonPayOnrampOptions {
  /** When false, the hook tears down and stops polling. */
  enabled?: boolean
  /** Chain the deposit lands on. Default 'base' (the trustless EM funding path). */
  chain?: 'base' | 'solana'
  /** USDC threshold (human units, 6-decimal). When balance >= target, phase → 'arrived'. */
  targetUsdc?: number
  /** Override the RPC. Defaults to VITE_BASE_RPC_URL / VITE_SOLANA_RPC_URL or public. */
  rpcUrl?: string
  /** Polling cadence in ms. Defaults to 1500ms (matches Phase 4.9 spec). */
  pollIntervalMs?: number
  /** Fires once when phase transitions to 'arrived' or 'failed'. */
  onComplete?: (result: { phase: 'arrived' | 'failed'; balance: number; lastEvent: MoonPayTransactionRow | null }) => void
}

export interface UseMoonPayOnrampReturn {
  balance: number
  /** Newest webhook event seen for this wallet (any status). Null until first realtime hit or refresh. */
  lastEvent: MoonPayTransactionRow | null
  phase: OnrampPhase
  error: Error | null
  /** Force-fetch the latest balance + latest moonpay_transactions row. Useful after the overlay closes. */
  refresh: () => Promise<void>
}

function isTerminal(status: TxnStatus | undefined | null): status is TerminalStatus {
  return status === 'completed' || status === 'failed'
}

export function useMoonPayOnramp(
  walletAddress: string | null | undefined,
  options: UseMoonPayOnrampOptions = {},
): UseMoonPayOnrampReturn {
  const {
    enabled = true,
    chain = 'base',
    targetUsdc,
    rpcUrl,
    pollIntervalMs = DEFAULT_POLL_MS,
    onComplete,
  } = options

  const [balance, setBalance] = useState(0)
  const [lastEvent, setLastEvent] = useState<MoonPayTransactionRow | null>(null)
  const [phase, setPhase] = useState<OnrampPhase>('idle')
  const [error, setError] = useState<Error | null>(null)

  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete
  const completedRef = useRef(false)
  // Mirror the latest webhook event for the polling/complete closures without
  // making it an effect dependency. Depending on `lastEvent` would tear down
  // and restart the channel on every Realtime row, which can cancel the watch
  // before the terminal event lands (F-14).
  const lastEventRef = useRef<MoonPayTransactionRow | null>(null)

  const resolvedRpc = useMemo(
    () => (chain === 'solana' ? resolveSolanaRpc(rpcUrl) : resolveEvmRpc('base', rpcUrl)),
    [rpcUrl, chain],
  )

  const fetchBalance = useCallback(async () => {
    if (!walletAddress) return 0
    try {
      const next =
        chain === 'solana'
          ? await readSolanaUsdcBalance(walletAddress, resolvedRpc)
          : await readEvmUsdcBalance(walletAddress, resolvedRpc, 'base')
      setBalance(next)
      setError(null)
      return next
    } catch (err) {
      setError(err instanceof Error ? err : new Error('RPC balance read failed'))
      return 0
    }
  }, [walletAddress, resolvedRpc, chain])

  const fetchLatestEvent = useCallback(async () => {
    if (!walletAddress) return null
    try {
      const { data, error: dbErr } = await supabase
        .from('moonpay_transactions')
        .select('*')
        .eq('wallet_address', walletAddress)
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()
      if (dbErr) throw dbErr
      const row = (data as MoonPayTransactionRow | null) ?? null
      lastEventRef.current = row
      setLastEvent(row)
      return row
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Supabase select failed'))
      return null
    }
  }, [walletAddress])

  const refresh = useCallback(async () => {
    await Promise.all([fetchBalance(), fetchLatestEvent()])
  }, [fetchBalance, fetchLatestEvent])

  useEffect(() => {
    completedRef.current = false
    if (!enabled || !walletAddress) {
      setPhase('idle')
      return
    }

    let cancelled = false
    let interval: ReturnType<typeof setInterval> | null = null

    function complete(result: 'arrived' | 'failed', latestBalance: number, latestEvent: MoonPayTransactionRow | null) {
      if (completedRef.current) return
      completedRef.current = true
      setPhase(result)
      onCompleteRef.current?.({ phase: result, balance: latestBalance, lastEvent: latestEvent })
      if (interval) clearInterval(interval)
    }

    async function poll() {
      if (cancelled || completedRef.current) return
      const next = await fetchBalance()
      if (cancelled || completedRef.current) return
      if (typeof targetUsdc === 'number' && next >= targetUsdc) {
        complete('arrived', next, lastEventRef.current)
      }
    }

    setPhase('watching')
    void poll()
    interval = setInterval(poll, pollIntervalMs)

    const channel = supabase
      .channel(`moonpay-onramp-${walletAddress}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'moonpay_transactions',
          filter: `wallet_address=eq.${walletAddress}`,
        },
        (payload: { new?: MoonPayTransactionRow; old?: MoonPayTransactionRow }) => {
          const row = (payload.new ?? payload.old) as MoonPayTransactionRow | undefined
          if (!row || cancelled || completedRef.current) return
          lastEventRef.current = row
          setLastEvent(row)
          if (isTerminal(row.status)) {
            void fetchBalance().then((latest) => {
              if (cancelled) return
              complete(row.status === 'completed' ? 'arrived' : 'failed', latest, row)
            })
          }
        },
      )
      .subscribe()

    // Seed lastEvent so the UI shows any pre-mount history (e.g. a refresh
    // mid-buy lands on a wallet that already has a 'pending' row).
    void fetchLatestEvent()

    return () => {
      cancelled = true
      if (interval) clearInterval(interval)
      void supabase.removeChannel(channel)
      if (!completedRef.current) setPhase('cancelled')
    }
  }, [enabled, walletAddress, pollIntervalMs, targetUsdc, fetchBalance, fetchLatestEvent])

  return { balance, lastEvent, phase, error, refresh }
}

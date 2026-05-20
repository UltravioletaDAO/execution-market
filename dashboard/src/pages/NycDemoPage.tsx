/**
 * NycDemoPage — single URL for the MoonPay NYC demo (Phase 5.7).
 *
 * The whole demo arc on one page, choreographed in five beats:
 *
 *   1. wallet      — Saul enters / confirms his Solana address
 *   2. balance     — read on-chain USDC; if short, open MoonPay overlay
 *                    (with the Phase 4.10 fallback wired in)
 *   3. publish     — fire `createTask` with `payment_network: 'solana'`,
 *                    which forces the backend into solana_session mode
 *   4. binding     — wait for the worker robot to open the pay.sh session
 *                    and bind a channelId to the task. Saul can paste it
 *                    by hand from his ops terminal if the binding stalls.
 *   5. execute     — render <TaskExecutionScene>, which owns the live
 *                    taxímetro + settlement animation
 *
 * Designed to be deep-linkable: every step accepts a URL param so the
 * demo can be pre-armed on the live laptop. Open the URL with
 * `?wallet=&channel=&task=&barcode=&cap=&rate=&network=` and the page
 * skips straight to beat 5. Bare URL → walk through all five beats.
 *
 * One screen per beat, B&W per brand-canonical, no animations beyond
 * those that serve the cinematic moment. Auth-free on purpose — the
 * stage laptop will hold the wallet keys / agent identity outside this
 * page (OWS terminal + ECS-backed publish endpoint with API key).
 */

import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MoonPayFailureFallback } from '../components/MoonPayFailureFallback'
import { MoonPayFrame } from '../components/MoonPayFrame'
import {
  MoonPayError,
  requestMoonPaySignedUrl,
  type OnrampPayload,
} from '../services/moonpay'
import { readSolanaUsdcBalance, resolveSolanaRpc } from '../services/solana-balance'
import { createTask } from '../services/tasks'
import type { SettlementNetwork } from '../components/SettlementAnimation'
import { TaskExecutionScene } from './TaskExecutionScene'

type Beat = 'wallet' | 'balance' | 'publish' | 'binding' | 'execute'

interface FormState {
  title: string
  instructions: string
  bountyUsd: number
  deadlineHours: number
  ratePerSec: number
}

const DEFAULT_FORM: FormState = {
  title: 'Robot fetches a barcode-tagged item from shelf A-3',
  instructions: 'Scan the on-stage code, traverse to A-3, pick the item, return.',
  bountyUsd: 5,
  deadlineHours: 1,
  ratePerSec: 0.05,
}

function parseNumberParam(value: string | null, fallback?: number): number | undefined {
  if (!value) return fallback
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function parseNetworkParam(value: string | null): SettlementNetwork {
  if (value === 'devnet' || value === 'surfpool') return value
  return 'mainnet-beta'
}

export function NycDemoPage() {
  const [params, setParams] = useSearchParams()

  // URL-controlled initial state — lets the stage laptop deep-link in.
  const initialWallet = params.get('wallet') ?? ''
  const initialChannel = params.get('channel') ?? ''
  const initialTaskId = params.get('task') ?? ''
  const initialBarcode = params.get('barcode') ?? ''
  const urlCap = parseNumberParam(params.get('cap'))
  const urlRate = parseNumberParam(params.get('rate'))
  const network = parseNetworkParam(params.get('network'))
  const explorerBaseUrl = params.get('explorer') ?? undefined

  const initialBeat: Beat = initialChannel ? 'execute' : initialWallet ? 'balance' : 'wallet'

  const [beat, setBeat] = useState<Beat>(initialBeat)
  const [wallet, setWallet] = useState(initialWallet)
  const [balance, setBalance] = useState<number | null>(null)
  const [balanceError, setBalanceError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const [onramp, setOnramp] = useState<OnrampPayload | null>(null)
  const [onrampError, setOnrampError] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>({
    ...DEFAULT_FORM,
    bountyUsd: urlCap ?? DEFAULT_FORM.bountyUsd,
    ratePerSec: urlRate ?? DEFAULT_FORM.ratePerSec,
  })
  const [publishing, setPublishing] = useState(false)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [taskId, setTaskId] = useState(initialTaskId)
  const [channelId, setChannelId] = useState(initialChannel)
  const [barcodeValue, setBarcodeValue] = useState(initialBarcode)

  const required = useMemo(() => {
    const targetUsdc = form.bountyUsd
    return { targetUsdc }
  }, [form.bountyUsd])

  // Push state into the URL as it advances so the stage laptop can be
  // reloaded mid-demo without losing the beat.
  useEffect(() => {
    const next = new URLSearchParams(params)
    if (wallet) next.set('wallet', wallet)
    if (taskId) next.set('task', taskId)
    if (channelId) next.set('channel', channelId)
    if (barcodeValue) next.set('barcode', barcodeValue)
    if (next.toString() !== params.toString()) setParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wallet, taskId, channelId, barcodeValue])

  async function runBalanceCheck(target: number) {
    if (!wallet) return
    setChecking(true)
    setBalanceError(null)
    try {
      const latest = await readSolanaUsdcBalance(wallet, resolveSolanaRpc())
      setBalance(latest)
      if (latest >= target) setBeat('publish')
    } catch (err) {
      setBalanceError(err instanceof Error ? err.message : String(err))
    } finally {
      setChecking(false)
    }
  }

  async function openMoonPay() {
    setOnrampError(null)
    try {
      const result = await requestMoonPaySignedUrl({
        walletAddress: wallet,
        baseCurrencyAmount: Math.max(20, Math.ceil(form.bountyUsd)),
        baseCurrencyCode: 'usd',
        currencyCode: 'usdc_sol',
      })
      setOnramp(result)
    } catch (err) {
      if (err instanceof MoonPayError) {
        setOnrampError(`Sign-URL failed (${err.status}): ${err.message}`)
      } else {
        setOnrampError(err instanceof Error ? err.message : String(err))
      }
    }
  }

  async function handlePublish() {
    setPublishing(true)
    setPublishError(null)
    try {
      const task = await createTask({
        agentId: wallet, // backend resolves agent identity from auth + wallet
        title: form.title,
        instructions: form.instructions,
        category: 'simple_action',
        bountyUsd: form.bountyUsd,
        deadlineHours: form.deadlineHours,
        evidenceRequired: ['photo'],
        paymentToken: 'USDC',
        paymentNetwork: 'solana',
      })
      setTaskId(task.id)
      if (!barcodeValue) setBarcodeValue(task.id)
      setBeat('binding')
    } catch (err) {
      setPublishError(err instanceof Error ? err.message : String(err))
    } finally {
      setPublishing(false)
    }
  }

  function handleEnterExecute() {
    if (!channelId) return
    setBeat('execute')
  }

  // ---------- Beat 5: execute (renders the cinematic scene) ----------
  if (beat === 'execute' && channelId) {
    return (
      <TaskExecutionScene
        channelId={channelId}
        barcodeValue={barcodeValue || taskId || channelId}
        taskTitle={form.title}
        cap={form.bountyUsd}
        ratePerSec={form.ratePerSec}
        network={network}
        explorerBaseUrl={explorerBaseUrl}
      />
    )
  }

  // ---------- Beats 1–4: prelude (form-driven) ----------
  return (
    <div className="min-h-screen bg-white font-mono text-black">
      <header className="border-b-2 border-black px-10 py-6">
        <div className="text-xs uppercase tracking-[0.3em] text-zinc-600">
          Execution Market · MoonPay NYC demo
        </div>
        <h1 className="mt-1 text-3xl font-bold md:text-4xl">Stage prelude</h1>
        <ol className="mt-4 flex gap-3 text-xs uppercase tracking-widest text-zinc-600">
          {(['wallet', 'balance', 'publish', 'binding'] as const).map((b, i) => (
            <li
              key={b}
              className={
                'border-l-4 pl-2 ' +
                (b === beat ? 'border-black text-black font-bold' : 'border-zinc-300')
              }
            >
              {i + 1}. {b}
            </li>
          ))}
        </ol>
      </header>

      <main className="mx-auto max-w-3xl px-10 py-10">
        {beat === 'wallet' && (
          <section>
            <h2 className="text-2xl font-bold">Solana wallet</h2>
            <p className="mt-1 text-sm text-zinc-600">
              The base58 address that holds USDC and signs the publish.
            </p>
            <input
              value={wallet}
              onChange={(e) => setWallet(e.target.value)}
              placeholder="So1ana...wallet"
              className="mt-4 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm"
            />
            <button
              type="button"
              disabled={!wallet}
              onClick={() => setBeat('balance')}
              className="mt-4 bg-black px-4 py-2 text-sm uppercase tracking-wider text-white disabled:bg-zinc-400"
            >
              Continue
            </button>
          </section>
        )}

        {beat === 'balance' && (
          <section>
            <h2 className="text-2xl font-bold">USDC balance check</h2>
            <p className="mt-1 text-sm text-zinc-600">
              Need at least ${required.targetUsdc.toFixed(2)} USDC on Solana to
              fund the bounty.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => runBalanceCheck(required.targetUsdc)}
                disabled={checking}
                className="bg-black px-4 py-2 text-sm uppercase tracking-wider text-white disabled:bg-zinc-400"
              >
                {checking ? 'Checking…' : 'Check balance'}
              </button>
              <button
                type="button"
                onClick={openMoonPay}
                className="border-2 border-black bg-white px-4 py-2 text-sm uppercase tracking-wider text-black"
              >
                Open MoonPay
              </button>
            </div>

            {balance !== null && (
              <div className="mt-4 border-t border-black pt-3 text-sm">
                <div>
                  Balance:{' '}
                  <span className="font-bold tabular-nums">${balance.toFixed(4)}</span>
                </div>
                {balance < required.targetUsdc && (
                  <div className="mt-1 text-zinc-700">
                    Short ${Math.max(0, required.targetUsdc - balance).toFixed(4)}.
                    Use MoonPay or the fallback below.
                  </div>
                )}
              </div>
            )}
            {balanceError && (
              <p className="mt-3 text-xs text-zinc-700">RPC error: {balanceError}</p>
            )}

            {onramp && (
              <div className="mt-6 border-t border-black pt-4">
                <MoonPayFrame
                  onramp={onramp}
                  onEvent={() => undefined}
                  onError={(err) =>
                    setOnrampError(err instanceof Error ? err.message : String(err))
                  }
                  onClose={() => setOnramp(null)}
                />
              </div>
            )}
            {onrampError && (
              <p className="mt-3 text-xs text-zinc-700">MoonPay: {onrampError}</p>
            )}

            {wallet && (
              <div className="mt-6">
                <MoonPayFailureFallback
                  walletAddress={wallet}
                  targetUsdc={required.targetUsdc}
                  reason="stage prelude"
                  onSkip={(bal) => {
                    setBalance(bal)
                    setBeat('publish')
                  }}
                  onRetry={openMoonPay}
                />
              </div>
            )}
          </section>
        )}

        {beat === 'publish' && (
          <section>
            <h2 className="text-2xl font-bold">Publish task</h2>
            <p className="mt-1 text-sm text-zinc-600">
              Fires <code>createTask</code> with{' '}
              <code>payment_network: 'solana'</code>, which routes to the pay.sh
              session backend.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3">
              <label className="text-xs uppercase tracking-widest text-zinc-600">
                Title
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm normal-case"
                />
              </label>
              <label className="text-xs uppercase tracking-widest text-zinc-600">
                Instructions
                <textarea
                  value={form.instructions}
                  onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                  rows={3}
                  className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm normal-case"
                />
              </label>
              <div className="grid grid-cols-3 gap-3">
                <label className="text-xs uppercase tracking-widest text-zinc-600">
                  Bounty (USDC)
                  <input
                    type="number"
                    min={0.01}
                    step={0.01}
                    value={form.bountyUsd}
                    onChange={(e) =>
                      setForm({ ...form, bountyUsd: Number(e.target.value) })
                    }
                    className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm"
                  />
                </label>
                <label className="text-xs uppercase tracking-widest text-zinc-600">
                  Rate (USDC/s)
                  <input
                    type="number"
                    min={0}
                    step={0.001}
                    value={form.ratePerSec}
                    onChange={(e) =>
                      setForm({ ...form, ratePerSec: Number(e.target.value) })
                    }
                    className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm"
                  />
                </label>
                <label className="text-xs uppercase tracking-widest text-zinc-600">
                  Deadline (h)
                  <input
                    type="number"
                    min={1}
                    value={form.deadlineHours}
                    onChange={(e) =>
                      setForm({ ...form, deadlineHours: Number(e.target.value) })
                    }
                    className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm"
                  />
                </label>
              </div>
            </div>
            <button
              type="button"
              onClick={handlePublish}
              disabled={publishing}
              className="mt-4 bg-black px-4 py-2 text-sm uppercase tracking-wider text-white disabled:bg-zinc-400"
            >
              {publishing ? 'Publishing…' : 'Publish task on Solana'}
            </button>
            {publishError && (
              <p className="mt-3 text-xs text-zinc-700">{publishError}</p>
            )}
          </section>
        )}

        {beat === 'binding' && (
          <section>
            <h2 className="text-2xl font-bold">Awaiting channel binding</h2>
            <p className="mt-1 text-sm text-zinc-600">
              Task <code className="font-mono">{taskId}</code> is published. The
              robot needs to open its pay.sh session, which mints a{' '}
              <code>channelId</code> the meter can subscribe to.
            </p>
            <p className="mt-3 text-xs text-zinc-600">
              Paste the channel id from the ops terminal (the robot prints it
              after <code>robot_open_payshell_session</code>).
            </p>
            <input
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              placeholder="channel id (32+ chars)"
              className="mt-3 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm"
            />
            <label className="mt-3 block text-xs uppercase tracking-widest text-zinc-600">
              Barcode value (defaults to task id)
              <input
                value={barcodeValue || taskId}
                onChange={(e) => setBarcodeValue(e.target.value)}
                className="mt-1 w-full border-2 border-black bg-white px-3 py-2 font-mono text-sm normal-case"
              />
            </label>
            <button
              type="button"
              onClick={handleEnterExecute}
              disabled={!channelId}
              className="mt-4 bg-black px-4 py-2 text-sm uppercase tracking-wider text-white disabled:bg-zinc-400"
            >
              Enter execution scene
            </button>
          </section>
        )}
      </main>
    </div>
  )
}

export default NycDemoPage

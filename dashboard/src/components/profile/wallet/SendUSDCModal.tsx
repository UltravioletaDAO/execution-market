// SendUSDCModal — signs and broadcasts an ERC-20 USDC transfer via the
// user's Dynamic wallet (viem WalletClient under the hood). Fees are paid by
// the worker's own wallet on whichever chain they pick — pre-ADR-001 there
// was no flow for this because funds sat on a custodial balance.

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'
import { isEthereumWallet } from '@dynamic-labs/ethereum'
import { erc20Abi, parseUnits, isAddress, type Address } from 'viem'
import { LIVE_NETWORKS } from '../../../config/networks'
import type { ChainBalance } from '../../../hooks/useOnchainBalance'
import { truncateAddress } from '../../../lib/utils'
import { Modal } from '../../ui/Modal'

interface SendUSDCModalProps {
  open: boolean
  onClose: () => void
  balances: ChainBalance[]
  /** Canonical wallet (Supabase row + ERC-8004 identity). Used to flag the case
   *  where the active wallet (which signs the tx) is different from where the
   *  user's task rewards land. */
  identityAddress?: string
  onSuccess?: (txHash: string) => void
}

const USDC_ADDRESSES: Record<string, Address> = {
  base: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  ethereum: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
  polygon: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
  arbitrum: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
  optimism: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
  avalanche: '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E',
  celo: '0xcebA9300f2b948710d2653dD7B07f33A8B32118C',
}

const CHAIN_IDS: Record<string, number> = {
  base: 8453,
  ethereum: 1,
  polygon: 137,
  arbitrum: 42161,
  optimism: 10,
  avalanche: 43114,
  celo: 42220,
}

type SendState =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'success'; txHash: string }
  | { kind: 'error'; message: string }

export function SendUSDCModal({ open, onClose, balances, identityAddress, onSuccess }: SendUSDCModalProps) {
  const { t } = useTranslation()
  const { primaryWallet } = useDynamicContext()

  const fromAddress = primaryWallet?.address || ''
  const isEmbedded = Boolean(primaryWallet?.connector?.isEmbeddedWallet)
  const fromDiffersFromIdentity =
    !!identityAddress &&
    !!fromAddress &&
    identityAddress.toLowerCase() !== fromAddress.toLowerCase()

  const sendableChains = useMemo(
    () => balances.filter((b) => !b.error && b.balance > 0 && USDC_ADDRESSES[b.network.key]),
    [balances],
  )

  const [chainKey, setChainKey] = useState<string>(() => sendableChains[0]?.network.key ?? 'base')
  const [recipient, setRecipient] = useState('')
  const [amount, setAmount] = useState('')
  const [state, setState] = useState<SendState>({ kind: 'idle' })

  const selectedBalance = balances.find((b) => b.network.key === chainKey)
  const maxBalance = selectedBalance?.balance ?? 0
  const recipientOk = recipient.length > 0 && isAddress(recipient)
  const amountNum = Number(amount)
  const amountOk = amount.length > 0 && amountNum > 0 && amountNum <= maxBalance
  const isSubmitting = state.kind === 'submitting'
  const canSubmit =
    !isSubmitting && recipientOk && amountOk && !!USDC_ADDRESSES[chainKey]

  const handleSend = async () => {
    if (!primaryWallet) {
      setState({ kind: 'error', message: t('wallet.send.errorNoWallet', 'No wallet connected.') })
      return
    }
    if (!isEthereumWallet(primaryWallet)) {
      setState({
        kind: 'error',
        message: t('wallet.send.errorNonEvm', 'Only EVM wallets can send USDC here.'),
      })
      return
    }

    setState({ kind: 'submitting' })
    try {
      const chainId = CHAIN_IDS[chainKey]
      const walletClient = await primaryWallet.getWalletClient(String(chainId))
      if (!walletClient) {
        throw new Error('Wallet client unavailable for this chain.')
      }

      const usdc = USDC_ADDRESSES[chainKey]
      const value = parseUnits(amount, 6)

      const txHash = await walletClient.writeContract({
        address: usdc,
        abi: erc20Abi,
        functionName: 'transfer',
        args: [recipient as Address, value],
        account: walletClient.account,
        chain: walletClient.chain,
      })

      setState({ kind: 'success', txHash })
      onSuccess?.(txHash)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Transaction failed'
      setState({ kind: 'error', message })
    }
  }

  const handleClose = () => {
    setRecipient('')
    setAmount('')
    setState({ kind: 'idle' })
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      size="md"
      labelledBy="send-usdc-title"
      dismissOnEsc={!isSubmitting}
      dismissOnBackdrop={!isSubmitting}
    >
      <Modal.Header onClose={isSubmitting ? undefined : handleClose}>
        <h2 id="send-usdc-title" className="text-lg font-bold text-zinc-900">
          {t('wallet.send.title', 'Send USDC')}
        </h2>
        <p className="text-sm text-zinc-500 mt-1">
          {t('wallet.send.subtitle', 'You pay the gas on the selected chain.')}
        </p>
      </Modal.Header>

      <Modal.Body>
        {state.kind === 'success' ? (
          <div className="flex flex-col items-center text-center py-6">
            <div className="w-12 h-12 rounded-full bg-green-50 text-green-600 flex items-center justify-center mb-3">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="font-semibold text-zinc-900">
              {t('wallet.send.successTitle', 'Transfer submitted')}
            </h3>
            <p className="text-sm text-zinc-500 mt-1 mb-3">
              {t('wallet.send.successBody', 'Your USDC is on the way.')}
            </p>
            <code className="text-xs font-mono bg-zinc-50 border border-zinc-200 rounded px-2 py-1 break-all">
              {state.txHash}
            </code>
            <button
              onClick={handleClose}
              className="mt-4 px-4 py-2 text-sm font-medium text-white bg-zinc-900 rounded-lg hover:bg-zinc-800"
            >
              {t('common.done', 'Done')}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* From wallet — explicit so user always knows which wallet signs.
                When this differs from their identity wallet (rewards inbox),
                we surface that as a soft note: not an error, just clarity. */}
            {fromAddress && (
              <div className="flex items-center justify-between p-3 bg-zinc-50 border border-zinc-100 rounded-lg">
                <div className="text-xs text-zinc-500">
                  {t('wallet.send.fromLabel', 'From')}
                </div>
                <div className="flex items-center gap-2">
                  <code className="text-xs font-mono text-zinc-800">{truncateAddress(fromAddress)}</code>
                  <span className="text-[10px] uppercase tracking-wide font-semibold text-zinc-500">
                    {isEmbedded
                      ? t('wallet.send.embedded', 'Embedded')
                      : t('wallet.send.external', 'External')}
                  </span>
                </div>
              </div>
            )}
            {fromDiffersFromIdentity && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                {t(
                  'wallet.send.differsNote',
                  'Heads up: this isn\'t your rewards inbox. This transfer leaves the wallet you\'re currently signing with. Task rewards still land in {{identity}}.',
                  { identity: truncateAddress(identityAddress || '') },
                )}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">
                {t('wallet.send.chainLabel', 'Network')}
              </label>
              <select
                value={chainKey}
                onChange={(e) => setChainKey(e.target.value)}
                className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900"
              >
                {LIVE_NETWORKS.filter((n) => USDC_ADDRESSES[n.key]).map((n) => {
                  const bal = balances.find((b) => b.network.key === n.key)
                  const suffix = bal && !bal.error ? ` — $${bal.balance.toFixed(2)}` : ''
                  return (
                    <option key={n.key} value={n.key}>
                      {n.name}
                      {suffix}
                    </option>
                  )
                })}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-700 mb-1">
                {t('wallet.send.recipientLabel', 'Recipient address')}
              </label>
              <input
                type="text"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value.trim())}
                placeholder="0x..."
                className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-zinc-900"
                spellCheck={false}
                autoComplete="off"
              />
              {recipient.length > 0 && !recipientOk && (
                <p className="mt-1 text-xs text-red-600">
                  {t('wallet.send.invalidAddress', 'Not a valid EVM address.')}
                </p>
              )}
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-1">
                <label className="block text-xs font-medium text-zinc-700">
                  {t('wallet.send.amountLabel', 'Amount (USDC)')}
                </label>
                <button
                  type="button"
                  onClick={() => setAmount(maxBalance.toString())}
                  className="text-xs text-zinc-700 hover:text-zinc-900 hover:underline"
                >
                  {t('wallet.send.max', 'Max')}: ${maxBalance.toFixed(2)}
                </button>
              </div>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                max={maxBalance}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900"
              />
              {amount.length > 0 && !amountOk && (
                <p className="mt-1 text-xs text-red-600">
                  {amountNum > maxBalance
                    ? t('wallet.send.overBalance', 'Amount exceeds your balance on this chain.')
                    : t('wallet.send.invalidAmount', 'Enter a positive amount.')}
                </p>
              )}
            </div>

            {state.kind === 'error' && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-900">
                {state.message}
              </div>
            )}

            <button
              onClick={handleSend}
              disabled={!canSubmit}
              className="w-full px-4 py-2.5 text-sm font-medium text-white bg-zinc-900 rounded-lg hover:bg-zinc-800 disabled:bg-zinc-100 disabled:text-zinc-400 disabled:cursor-not-allowed"
            >
              {isSubmitting
                ? t('wallet.send.sending', 'Sending...')
                : t('wallet.send.submit', 'Send USDC')}
            </button>
          </div>
        )}
      </Modal.Body>
    </Modal>
  )
}

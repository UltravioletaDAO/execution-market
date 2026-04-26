// Phase 4 — change the executor's payment wallet via PATCH /api/v1/account/wallet.
//
// The backend rejects the call unless the *new* wallet signs a fresh challenge
// proving ownership, so this helper walks through the canonical message
// format, asks Dynamic's active wallet to personal_sign it, and posts the
// result with the Supabase JWT for the executor.
//
// The active wallet (Dynamic's primaryWallet) MUST already equal the wallet
// the user wants to use as their rewards inbox before calling this — that's
// what proves ownership. The banner enforces this by only being visible when
// active != identity, and by signing with whatever Dynamic has primary.

import { isEthereumWallet } from '@dynamic-labs/ethereum'
import type { Wallet } from '@dynamic-labs/wallet-connector-core'
import { buildAuthHeaders } from '../lib/auth'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

export interface UpdateWalletResponse {
  message: string
  wallet_address: string
  previous_wallet_address: string | null
  executor_id: string
  changed: boolean
}

interface UpdateWalletParams {
  /** Wallet to set as the executor's rewards inbox. Must match the address
   *  currently active in Dynamic so the user can sign the challenge. */
  newWalletAddress: string
  executorId: string
  /** Dynamic's `primaryWallet` from `useDynamicContext()`. May be null while
   *  the SDK is still hydrating. `isEthereumWallet` narrows it at runtime. */
  primaryWallet: Wallet | null
}

export async function updateWalletAddress({
  newWalletAddress,
  executorId,
  primaryWallet,
}: UpdateWalletParams): Promise<UpdateWalletResponse> {
  if (!primaryWallet || !isEthereumWallet(primaryWallet)) {
    throw new Error('Connect an EVM wallet to change your payment wallet.')
  }

  const newWallet = newWalletAddress.toLowerCase()
  const activeWallet = primaryWallet.address?.toLowerCase()
  if (activeWallet !== newWallet) {
    throw new Error(
      'Switch to the wallet you want as your rewards inbox before signing.',
    )
  }

  const timestamp = new Date().toISOString()
  const message =
    `Execution Market: change wallet to ${newWallet} ` +
    `for executor ${executorId} at ${timestamp}`

  // Chain id is irrelevant for personal_sign but Dynamic's getWalletClient
  // needs *some* chain — pick Base since every executor is funded there.
  const walletClient = await primaryWallet.getWalletClient('8453')
  if (!walletClient) {
    throw new Error('Wallet client unavailable.')
  }

  const signature = await walletClient.signMessage({
    message,
    account: walletClient.account,
  })

  const headers = await buildAuthHeaders({
    'Content-Type': 'application/json',
    'X-Client-Info': 'execution-market-dashboard',
  })

  const response = await fetch(`${API_BASE_URL}/api/v1/account/wallet`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({
      new_wallet_address: newWallet,
      message,
      signature,
    }),
  })

  if (!response.ok) {
    const text = await response.text()
    let detail = `Wallet change failed (${response.status})`
    try {
      const data = JSON.parse(text)
      detail = data.detail || data.message || detail
    } catch {
      // Use default detail
    }
    throw new Error(detail)
  }

  return response.json()
}

// Link the active wallet to the current Supabase session via
// POST /api/v1/account/link-wallet.
//
// This is the bootstrap that binds executors.user_id to the Supabase JWT sub,
// so worker-auth endpoints (apply, submit, withdraw) can resolve the executor.
// It replaces the revoked link_wallet_to_session RPC (migration 092) and the
// anon-revoked get_or_create_executor (migration 111). The wallet must sign a
// fresh challenge proving ownership — that's what authorizes the bind under
// migration 111's "proven owner" rule.

import { isEthereumWallet } from '@dynamic-labs/ethereum'
import type { Wallet } from '@dynamic-labs/wallet-connector-core'
import { buildAuthHeaders } from '../lib/auth'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'https://api.execution.market'
).replace(/\/+$/, '')

export interface LinkWalletResponse {
  message: string
  executor_id: string
  wallet_address: string
  linked: boolean
}

interface LinkWalletParams {
  /** Wallet to link. Must match the address currently active in Dynamic so the
   *  user can sign the ownership challenge. */
  walletAddress: string
  /** Dynamic's `primaryWallet` from `useDynamicContext()`. */
  primaryWallet: Wallet | null
}

export async function linkWalletSession({
  walletAddress,
  primaryWallet,
}: LinkWalletParams): Promise<LinkWalletResponse> {
  if (!primaryWallet || !isEthereumWallet(primaryWallet)) {
    throw new Error('Connect an EVM wallet to link your account.')
  }

  const wallet = walletAddress.toLowerCase()
  const activeWallet = primaryWallet.address?.toLowerCase()
  if (activeWallet !== wallet) {
    throw new Error('Switch to the wallet you want to link before signing.')
  }

  const timestamp = new Date().toISOString()
  const message =
    `Execution Market: link wallet ${wallet} to session at ${timestamp}`

  // personal_sign is chain-agnostic, but Dynamic's getWalletClient needs some
  // chain — Base, since every executor is funded there.
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

  const response = await fetch(`${API_BASE_URL}/api/v1/account/link-wallet`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      wallet_address: wallet,
      message,
      signature,
    }),
  })

  if (!response.ok) {
    const text = await response.text()
    let detail = `Wallet link failed (${response.status})`
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

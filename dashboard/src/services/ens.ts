/**
 * ENS API client for Execution Market
 *
 * Calls the backend ENS endpoints for resolution, linking, and subname claiming.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.execution.market'

export interface ENSResolveResult {
  name: string | null
  address: string | null
  resolved: boolean
  avatar: string | null
  network: string
  ens_link: string | null
  error: string | null
}

export interface ENSLinkResult {
  linked: boolean
  ens_name: string | null
  ens_avatar: string | null
  message: string
}

export interface ClaimSubnameResult {
  success: boolean
  subname: string | null
  tx_hash: string | null
  explorer: string | null
  message: string
}

export async function resolveENS(nameOrAddress: string): Promise<ENSResolveResult> {
  const resp = await fetch(`${API_BASE}/api/v1/ens/resolve/${encodeURIComponent(nameOrAddress)}`)
  if (!resp.ok) {
    return {
      name: null,
      address: null,
      resolved: false,
      avatar: null,
      network: 'mainnet',
      ens_link: null,
      error: `HTTP ${resp.status}`,
    }
  }
  return resp.json()
}

export async function linkENS(executorId: string): Promise<ENSLinkResult> {
  const resp = await fetch(`${API_BASE}/api/v1/ens/link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ executor_id: executorId }),
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: 'Unknown error' }))
    return {
      linked: false,
      ens_name: null,
      ens_avatar: null,
      message: data.detail || `Error ${resp.status}`,
    }
  }
  return resp.json()
}

export async function claimSubname(executorId: string, label: string): Promise<ClaimSubnameResult> {
  const resp = await fetch(`${API_BASE}/api/v1/ens/claim-subname`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ executor_id: executorId, label }),
  })
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: 'Unknown error' }))
    return {
      success: false,
      subname: null,
      tx_hash: null,
      explorer: null,
      message: data.detail || `Error ${resp.status}`,
    }
  }
  return resp.json()
}

// useOnchainBalance — reads USDC balance per chain for a wallet.
//
// Under ADR-001, funds are never custodied by the platform. Payments settle
// straight to the worker's wallet on whatever chain the agent chose. There is
// no single "balance" to show — each chain has its own. This hook returns the
// per-chain breakdown and a total.
//
// Data path: dashboard → EM balances Lambda (Function URL) → private QuikNode
// RPCs (from `facilitator-rpc-mainnet` Secrets Manager). The Lambda exists so
// that (1) we don't ship private RPC URLs in the browser bundle and (2) public
// RPCs don't rate-limit every dashboard render. See infrastructure/terraform/
// em_balances.tf and lambda/em_balances.py.
//
// If `VITE_BALANCES_LAMBDA_URL` is unset, the hook falls back to direct viem
// reads against public RPCs — useful for local dev before the Lambda is
// deployed, but expect rate-limit errors in production traffic.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPublicClient, http, erc20Abi, formatUnits, type Address } from 'viem'
import {
  mainnet,
  base,
  polygon,
  arbitrum,
  optimism,
  avalanche,
  celo,
  type Chain,
} from 'viem/chains'
import { LIVE_NETWORKS, type NetworkInfo } from '../config/networks'

const USDC_DECIMALS = 6

interface ChainEntry {
  network: NetworkInfo
  chain: Chain
  usdc: Address
}

const CHAINS: ChainEntry[] = (
  [
    { key: 'base', chain: base as Chain, usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' },
    { key: 'ethereum', chain: mainnet as Chain, usdc: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48' },
    { key: 'polygon', chain: polygon as Chain, usdc: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359' },
    { key: 'arbitrum', chain: arbitrum as Chain, usdc: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831' },
    { key: 'optimism', chain: optimism as Chain, usdc: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85' },
    { key: 'avalanche', chain: avalanche as Chain, usdc: '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E' },
    { key: 'celo', chain: celo as Chain, usdc: '0xcebA9300f2b948710d2653dD7B07f33A8B32118C' },
  ] as const
)
  .map(({ key, chain, usdc }) => {
    const network = LIVE_NETWORKS.find((n) => n.key === key)
    if (!network) return null
    return { network, chain, usdc: usdc as Address }
  })
  .filter((entry): entry is ChainEntry => entry !== null)

export interface ChainBalance {
  network: NetworkInfo
  balance: number
  raw: bigint
  error: string | null
  loading: boolean
}

export interface UseOnchainBalanceReturn {
  balances: ChainBalance[]
  totalUsdc: number
  loading: boolean
  error: Error | null
  lastUpdated: Date | null
  refetch: () => Promise<void>
}

function isValidAddress(value: unknown): value is Address {
  return typeof value === 'string' && /^0x[a-fA-F0-9]{40}$/.test(value)
}

const LAMBDA_URL = (import.meta.env.VITE_BALANCES_LAMBDA_URL as string | undefined)?.replace(/\/$/, '')

interface LambdaChainResult {
  raw: string | null
  balance: number
  error: string | null
}

interface LambdaResponse {
  wallet: string
  balances: Record<string, LambdaChainResult>
  total_usdc: number
  cached_at: number
  ttl_seconds: number
}

async function fetchFromLambda(wallet: Address): Promise<ChainBalance[]> {
  if (!LAMBDA_URL) throw new Error('VITE_BALANCES_LAMBDA_URL not configured')
  const res = await fetch(`${LAMBDA_URL}?wallet=${wallet}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Balances Lambda ${res.status}: ${text || res.statusText}`)
  }
  const data = (await res.json()) as LambdaResponse
  return CHAINS.map((entry) => {
    const result = data.balances[entry.network.key]
    if (!result) {
      return {
        network: entry.network,
        balance: 0,
        raw: 0n,
        error: 'no result from Lambda',
        loading: false,
      }
    }
    if (result.error) {
      return {
        network: entry.network,
        balance: 0,
        raw: 0n,
        error: result.error,
        loading: false,
      }
    }
    const raw = result.raw ? BigInt(result.raw) : 0n
    return {
      network: entry.network,
      balance: result.balance,
      raw,
      error: null,
      loading: false,
    }
  })
}

async function readUsdcBalanceViaViem(entry: ChainEntry, wallet: Address): Promise<ChainBalance> {
  const client = createPublicClient({ chain: entry.chain, transport: http() })
  try {
    const raw = (await client.readContract({
      address: entry.usdc,
      abi: erc20Abi,
      functionName: 'balanceOf',
      args: [wallet],
    })) as bigint
    return {
      network: entry.network,
      balance: Number(formatUnits(raw, USDC_DECIMALS)),
      raw,
      error: null,
      loading: false,
    }
  } catch (err) {
    return {
      network: entry.network,
      balance: 0,
      raw: 0n,
      error: err instanceof Error ? err.message : 'RPC read failed',
      loading: false,
    }
  }
}

async function fetchAllBalances(wallet: Address): Promise<ChainBalance[]> {
  if (LAMBDA_URL) return fetchFromLambda(wallet)
  return Promise.all(CHAINS.map((entry) => readUsdcBalanceViaViem(entry, wallet)))
}

export function useOnchainBalance(walletAddress: string | null | undefined): UseOnchainBalanceReturn {
  const [balances, setBalances] = useState<ChainBalance[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const normalizedWallet = useMemo<Address | null>(() => {
    if (!isValidAddress(walletAddress)) return null
    return walletAddress.toLowerCase() as Address
  }, [walletAddress])

  const fetchAll = useCallback(async () => {
    if (!normalizedWallet) {
      setBalances([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const results = await fetchAllBalances(normalizedWallet)
      setBalances(results)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Balance fetch failed'))
    } finally {
      setLoading(false)
    }
  }, [normalizedWallet])

  useEffect(() => {
    void fetchAll()
  }, [fetchAll])

  const totalUsdc = useMemo(
    () => balances.reduce((sum, b) => sum + (b.error ? 0 : b.balance), 0),
    [balances],
  )

  return { balances, totalUsdc, loading, error, lastUpdated, refetch: fetchAll }
}

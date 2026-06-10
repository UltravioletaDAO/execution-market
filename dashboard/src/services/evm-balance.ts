/**
 * EVM ERC-20 USDC balance reader — twin of `solana-balance.ts` for the Base
 * on-ramp watcher (`useMoonPayOnramp`). Issues a read-only `eth_call` to
 * USDC's `balanceOf(address)`; no signing happens here. USDC is 6 decimals on
 * every EVM chain we support.
 *
 * USDC contracts cross-checked against the backend NETWORK_CONFIG and MoonPay
 * /v3/currencies (contractAddress) on 2026-06-04.
 */

const BALANCE_OF_SELECTOR = '0x70a08231' // keccak256("balanceOf(address)")[:4]
const USDC_DECIMALS = 6

interface EvmNetworkConfig {
  usdc: string
  defaultRpc: string
  envKey: string
}

export const EVM_USDC: Record<string, EvmNetworkConfig> = {
  base: {
    usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    defaultRpc: 'https://mainnet.base.org',
    envKey: 'VITE_BASE_RPC_URL',
  },
  ethereum: {
    usdc: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    defaultRpc: 'https://eth.llamarpc.com',
    envKey: 'VITE_ETHEREUM_RPC_URL',
  },
  polygon: {
    usdc: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
    defaultRpc: 'https://polygon-rpc.com',
    envKey: 'VITE_POLYGON_RPC_URL',
  },
  arbitrum: {
    usdc: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
    defaultRpc: 'https://arb1.arbitrum.io/rpc',
    envKey: 'VITE_ARBITRUM_RPC_URL',
  },
  optimism: {
    usdc: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
    defaultRpc: 'https://mainnet.optimism.io',
    envKey: 'VITE_OPTIMISM_RPC_URL',
  },
  avalanche: {
    usdc: '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E',
    defaultRpc: 'https://api.avax.network/ext/bc/C/rpc',
    envKey: 'VITE_AVALANCHE_RPC_URL',
  },
}

function encodeBalanceOf(wallet: string): string {
  const addr = wallet.toLowerCase().replace(/^0x/, '')
  return BALANCE_OF_SELECTOR + addr.padStart(64, '0')
}

// EM balances Lambda (Function URL). Holds the private QuikNode RPCs in Secrets
// Manager so the browser never hits a public RPC directly — that direct path is
// what rate-limits and surfaces "RPC error" / Get-Node failures in the UI. See
// infrastructure/terraform/lambda/em_balances.py + hooks/useOnchainBalance.ts.
const BALANCES_LAMBDA_URL = (
  import.meta.env.VITE_BALANCES_LAMBDA_URL as string | undefined
)?.replace(/\/$/, '')

interface LambdaBalances {
  balances?: Record<string, { balance: number; error: string | null }>
}

/**
 * Read one chain's USDC balance via the balances Lambda. Returns null (not throw)
 * when the Lambda is unconfigured or the chain errored, so the caller can fall
 * back to a direct eth_call. The Lambda caches per wallet for ~60s — fine for a
 * displayed balance, and the onramp watcher has a Supabase Realtime backstop for
 * fast "funds arrived" detection.
 */
async function readViaBalancesLambda(
  wallet: string,
  network: string,
): Promise<number | null> {
  if (!BALANCES_LAMBDA_URL) return null
  try {
    const res = await fetch(`${BALANCES_LAMBDA_URL}?wallet=${wallet}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) return null
    const data = (await res.json()) as LambdaBalances
    const entry = data.balances?.[network]
    if (!entry || entry.error !== null) return null
    return entry.balance
  } catch {
    return null
  }
}

/**
 * Read a wallet's USDC balance on an EVM network (default Base) via a single
 * `eth_call`. Returns the human-readable amount (6-decimal). Throws on RPC
 * error so the caller (hook) can surface it — mirrors readSolanaUsdcBalance.
 */
export async function readEvmUsdcBalance(
  wallet: string,
  rpcUrl?: string,
  network: string = 'base',
): Promise<number> {
  const cfg = EVM_USDC[network]
  if (!cfg) throw new Error(`unsupported EVM network: ${network}`)

  // Prefer the balances Lambda (private RPCs, no browser rate-limits). Only when
  // it's unconfigured (local dev) or returns an error do we fall back to a direct
  // eth_call against the resolved RPC below.
  const viaLambda = await readViaBalancesLambda(wallet, network)
  if (viaLambda !== null) return viaLambda

  const url = resolveEvmRpc(network, rpcUrl)
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'eth_call',
      params: [{ to: cfg.usdc, data: encodeBalanceOf(wallet) }, 'latest'],
    }),
  })
  if (!resp.ok) throw new Error(`EVM RPC ${resp.status}`)
  const body = (await resp.json()) as { result?: string; error?: { message?: string } }
  if (body.error) throw new Error(`EVM RPC: ${body.error.message ?? 'unknown'}`)
  const raw = body.result
  if (!raw || !raw.startsWith('0x')) return 0
  // 6-decimal USDC: a wallet balance never overflows Number's safe range
  // (max safe ~9e15 base units = ~9e9 USDC), so BigInt→Number is exact here.
  const units = BigInt(raw)
  return Number(units) / 10 ** USDC_DECIMALS
}

/**
 * Read any ERC-20 stablecoin balance on an EVM chain via a single read-only
 * `eth_call` to `balanceOf(address)`. Generalises readEvmUsdcBalance for the
 * H2H publish flow's network/stablecoin selector (USDC/USDT/EURC/AUSD/PYUSD).
 *
 * The balances Lambda only knows each chain's USDC, so we only route through it
 * when the requested token IS that chain's USDC; every other token reads the
 * RPC directly. All five stablecoins are 6-decimal, but `decimals` is passed in
 * so this stays correct if that ever changes. Returns 0 on empty/garbage result.
 */
export async function readEvmStablecoinBalance(
  wallet: string,
  network: string,
  tokenAddress: string,
  decimals: number,
  rpcUrl: string,
): Promise<number> {
  const usdcCfg = EVM_USDC[network]
  if (usdcCfg && tokenAddress.toLowerCase() === usdcCfg.usdc.toLowerCase()) {
    const viaLambda = await readViaBalancesLambda(wallet, network)
    if (viaLambda !== null) return viaLambda
  }

  const resp = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'eth_call',
      params: [{ to: tokenAddress, data: encodeBalanceOf(wallet) }, 'latest'],
    }),
  })
  if (!resp.ok) throw new Error(`EVM RPC ${resp.status}`)
  const body = (await resp.json()) as { result?: string; error?: { message?: string } }
  if (body.error) throw new Error(`EVM RPC: ${body.error.message ?? 'unknown'}`)
  const raw = body.result
  if (!raw || !raw.startsWith('0x')) return 0
  return Number(BigInt(raw)) / 10 ** decimals
}

/**
 * Resolve the EVM RPC URL: explicit override > VITE_<NETWORK>_RPC_URL >
 * public default. Mirrors resolveSolanaRpc. Prefers QuikNode private RPCs
 * from env per the repo RPC policy.
 */
export function resolveEvmRpc(network: string = 'base', rpcUrl?: string): string {
  if (rpcUrl) return rpcUrl
  const cfg = EVM_USDC[network]
  if (!cfg) return EVM_USDC.base.defaultRpc
  const envRpc = (import.meta.env[cfg.envKey] as string | undefined)?.trim()
  return envRpc && envRpc.length > 0 ? envRpc : cfg.defaultRpc
}

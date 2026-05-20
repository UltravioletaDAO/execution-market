/**
 * Solana SPL balance reader — shared by the on-ramp watcher
 * (`useMoonPayOnramp`) and the failure-fallback ("I already have USDC").
 *
 * Uses the public JSON-RPC `getTokenAccountsByOwner` with the USDC mint
 * filter and sums `tokenAmount.uiAmount(String)` across every SPL account
 * the wallet owns. No signing happens here — a read-only RPC is fine.
 */

export const SOLANA_USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
export const SOLANA_DEFAULT_RPC = 'https://api.mainnet-beta.solana.com'

interface RpcResponse {
  result?: {
    value?: Array<{
      account?: {
        data?: {
          parsed?: {
            info?: {
              tokenAmount?: {
                uiAmountString?: string
                uiAmount?: number
              }
            }
          }
        }
      }
    }>
  }
  error?: { message?: string }
}

export async function readSolanaUsdcBalance(
  wallet: string,
  rpcUrl: string = SOLANA_DEFAULT_RPC,
): Promise<number> {
  const resp = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'getTokenAccountsByOwner',
      params: [wallet, { mint: SOLANA_USDC_MINT }, { encoding: 'jsonParsed' }],
    }),
  })
  if (!resp.ok) throw new Error(`Solana RPC ${resp.status}`)
  const body = (await resp.json()) as RpcResponse
  if (body.error) throw new Error(`Solana RPC: ${body.error.message ?? 'unknown'}`)
  const accounts = body.result?.value ?? []
  let total = 0
  for (const acc of accounts) {
    const ui = acc.account?.data?.parsed?.info?.tokenAmount
    if (!ui) continue
    const parsed = ui.uiAmountString ? Number(ui.uiAmountString) : (ui.uiAmount ?? 0)
    if (Number.isFinite(parsed)) total += parsed
  }
  return total
}

/**
 * Resolve the Solana RPC URL the same way the hook does:
 *   explicit override > VITE_SOLANA_RPC_URL > public mainnet-beta.
 */
export function resolveSolanaRpc(rpcUrl?: string): string {
  if (rpcUrl) return rpcUrl
  const envRpc = (import.meta.env.VITE_SOLANA_RPC_URL as string | undefined)?.trim()
  return envRpc && envRpc.length > 0 ? envRpc : SOLANA_DEFAULT_RPC
}

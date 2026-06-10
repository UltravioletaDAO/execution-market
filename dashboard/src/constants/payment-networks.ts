/**
 * Payment networks + stablecoins for the H2H services publish flow.
 *
 * MIRRORS the backend single source of truth — `NETWORK_CONFIG` in
 * `mcp_server/integrations/x402/sdk_client.py`. Only the 9 EVM networks that
 * have an x402r escrow + PaymentOperator deployed are listed here, because
 * publishing a task locks publisher funds in escrow (Fase 2 trustless). Solana
 * is Fase 1 (no escrow) and is intentionally excluded.
 *
 * 5 stablecoins across these networks: USDC, USDT, EURC, AUSD, PYUSD.
 * Addresses cross-checked against sdk_client.py on 2026-06-10. If the backend
 * registry changes, update this file too (CI has no automated sync for it).
 */

export interface StablecoinInfo {
  symbol: string
  address: string
  decimals: number
}

export interface PaymentNetworkInfo {
  key: string
  label: string
  /** Vite env var that overrides the public RPC (QuikNode private RPC per repo policy). */
  rpcEnvKey: string
  defaultRpc: string
  stablecoins: StablecoinInfo[]
}

const USDC = (address: string): StablecoinInfo => ({ symbol: 'USDC', address, decimals: 6 })
const USDT = (address: string): StablecoinInfo => ({ symbol: 'USDT', address, decimals: 6 })
const EURC = (address: string): StablecoinInfo => ({ symbol: 'EURC', address, decimals: 6 })
const AUSD = (address: string): StablecoinInfo => ({ symbol: 'AUSD', address, decimals: 6 })
const PYUSD = (address: string): StablecoinInfo => ({ symbol: 'PYUSD', address, decimals: 6 })

export const PAYMENT_NETWORKS: PaymentNetworkInfo[] = [
  {
    key: 'base',
    label: 'Base',
    rpcEnvKey: 'VITE_BASE_RPC_URL',
    defaultRpc: 'https://mainnet.base.org',
    stablecoins: [
      USDC('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
      EURC('0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42'),
    ],
  },
  {
    key: 'ethereum',
    label: 'Ethereum',
    rpcEnvKey: 'VITE_ETHEREUM_RPC_URL',
    defaultRpc: 'https://ethereum-rpc.publicnode.com',
    stablecoins: [
      USDC('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
      EURC('0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c'),
      PYUSD('0x6c3ea9036406852006290770BEdFcAbA0e23A0e8'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a'),
    ],
  },
  {
    key: 'polygon',
    label: 'Polygon',
    rpcEnvKey: 'VITE_POLYGON_RPC_URL',
    defaultRpc: 'https://polygon-bor-rpc.publicnode.com',
    stablecoins: [
      USDC('0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a'),
    ],
  },
  {
    key: 'arbitrum',
    label: 'Arbitrum',
    rpcEnvKey: 'VITE_ARBITRUM_RPC_URL',
    defaultRpc: 'https://arb1.arbitrum.io/rpc',
    stablecoins: [
      USDC('0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
      USDT('0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a'),
    ],
  },
  {
    key: 'celo',
    label: 'Celo',
    rpcEnvKey: 'VITE_CELO_RPC_URL',
    defaultRpc: 'https://forno.celo.org',
    stablecoins: [
      USDC('0xcebA9300f2b948710d2653dD7B07f33A8B32118C'),
      USDT('0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e'),
    ],
  },
  {
    key: 'monad',
    label: 'Monad',
    rpcEnvKey: 'VITE_MONAD_RPC_URL',
    defaultRpc: 'https://rpc.monad.xyz',
    stablecoins: [
      USDC('0x754704Bc059F8C67012fEd69BC8A327a5aafb603'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a'),
    ],
  },
  {
    key: 'avalanche',
    label: 'Avalanche',
    rpcEnvKey: 'VITE_AVALANCHE_RPC_URL',
    defaultRpc: 'https://api.avax.network/ext/bc/C/rpc',
    stablecoins: [
      USDC('0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E'),
      EURC('0xC891EB4cbdEFf6e073e859e987815Ed1505c2ACD'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a'),
    ],
  },
  {
    key: 'optimism',
    label: 'Optimism',
    rpcEnvKey: 'VITE_OPTIMISM_RPC_URL',
    defaultRpc: 'https://mainnet.optimism.io',
    stablecoins: [
      USDC('0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
      USDT('0x01bff41798a0bcf287b996046ca68b395dbc1071'),
    ],
  },
  {
    key: 'skale',
    label: 'SKALE',
    rpcEnvKey: 'VITE_SKALE_RPC_URL',
    defaultRpc: 'https://skale-base.skalenodes.com/v1/base',
    stablecoins: [USDC('0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20')],
  },
]

export function getPaymentNetwork(key: string): PaymentNetworkInfo {
  return PAYMENT_NETWORKS.find((n) => n.key === key) ?? PAYMENT_NETWORKS[0]
}

/** Resolve a network's RPC: env override > public default. */
export function resolvePaymentRpc(net: PaymentNetworkInfo): string {
  const envRpc = (import.meta.env[net.rpcEnvKey] as string | undefined)?.trim()
  return envRpc && envRpc.length > 0 ? envRpc : net.defaultRpc
}

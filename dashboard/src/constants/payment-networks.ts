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
  /** EIP-712 domain `name` for EIP-3009 signing (TransferWithAuthorization). */
  eip712Name: string
  /** EIP-712 domain `version` for EIP-3009 signing. */
  eip712Version: string
}

export interface PaymentNetworkInfo {
  key: string
  label: string
  /** EVM chain id — needed for the EIP-712 domain + Dynamic wallet client. */
  chainId: number
  /** Vite env var that overrides the public RPC (QuikNode private RPC per repo policy). */
  rpcEnvKey: string
  defaultRpc: string
  stablecoins: StablecoinInfo[]
}

// EIP-712 name/version per token mirror NETWORK_CONFIG in sdk_client.py — they
// MUST match the on-chain token's domain or EIP-3009 signatures are rejected.
const coin =
  (symbol: string) =>
  (address: string, eip712Name: string, eip712Version: string): StablecoinInfo => ({
    symbol,
    address,
    decimals: 6,
    eip712Name,
    eip712Version,
  })
const USDC = coin('USDC')
const USDT = coin('USDT')
const EURC = coin('EURC')
const AUSD = coin('AUSD')
const PYUSD = coin('PYUSD')

export const PAYMENT_NETWORKS: PaymentNetworkInfo[] = [
  {
    key: 'base',
    label: 'Base',
    chainId: 8453,
    rpcEnvKey: 'VITE_BASE_RPC_URL',
    defaultRpc: 'https://mainnet.base.org',
    stablecoins: [
      USDC('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', 'USD Coin', '2'),
      EURC('0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42', 'EURC', '2'),
    ],
  },
  {
    key: 'ethereum',
    label: 'Ethereum',
    chainId: 1,
    rpcEnvKey: 'VITE_ETHEREUM_RPC_URL',
    defaultRpc: 'https://ethereum-rpc.publicnode.com',
    stablecoins: [
      USDC('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'USD Coin', '2'),
      EURC('0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c', 'Euro Coin', '2'),
      PYUSD('0x6c3ea9036406852006290770BEdFcAbA0e23A0e8', 'PayPal USD', '1'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a', 'Agora Dollar', '1'),
    ],
  },
  {
    key: 'polygon',
    label: 'Polygon',
    chainId: 137,
    rpcEnvKey: 'VITE_POLYGON_RPC_URL',
    defaultRpc: 'https://polygon-bor-rpc.publicnode.com',
    stablecoins: [
      USDC('0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', 'USD Coin', '2'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a', 'Agora Dollar', '1'),
    ],
  },
  {
    key: 'arbitrum',
    label: 'Arbitrum',
    chainId: 42161,
    rpcEnvKey: 'VITE_ARBITRUM_RPC_URL',
    defaultRpc: 'https://arb1.arbitrum.io/rpc',
    stablecoins: [
      USDC('0xaf88d065e77c8cC2239327C5EDb3A432268e5831', 'USD Coin', '2'),
      USDT('0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', 'USD₮0', '1'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a', 'Agora Dollar', '1'),
    ],
  },
  {
    key: 'celo',
    label: 'Celo',
    chainId: 42220,
    rpcEnvKey: 'VITE_CELO_RPC_URL',
    defaultRpc: 'https://forno.celo.org',
    stablecoins: [
      USDC('0xcebA9300f2b948710d2653dD7B07f33A8B32118C', 'USDC', '2'),
      USDT('0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e', 'Tether USD', '1'),
    ],
  },
  {
    key: 'monad',
    label: 'Monad',
    chainId: 143,
    rpcEnvKey: 'VITE_MONAD_RPC_URL',
    defaultRpc: 'https://rpc.monad.xyz',
    stablecoins: [
      USDC('0x754704Bc059F8C67012fEd69BC8A327a5aafb603', 'USDC', '2'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a', 'Agora Dollar', '1'),
    ],
  },
  {
    key: 'avalanche',
    label: 'Avalanche',
    chainId: 43114,
    rpcEnvKey: 'VITE_AVALANCHE_RPC_URL',
    defaultRpc: 'https://api.avax.network/ext/bc/C/rpc',
    stablecoins: [
      USDC('0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E', 'USD Coin', '2'),
      EURC('0xC891EB4cbdEFf6e073e859e987815Ed1505c2ACD', 'Euro Coin', '2'),
      AUSD('0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a', 'Agora Dollar', '1'),
    ],
  },
  {
    key: 'optimism',
    label: 'Optimism',
    chainId: 10,
    rpcEnvKey: 'VITE_OPTIMISM_RPC_URL',
    defaultRpc: 'https://mainnet.optimism.io',
    stablecoins: [
      USDC('0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85', 'USD Coin', '2'),
      USDT('0x01bff41798a0bcf287b996046ca68b395dbc1071', 'Tether USD', '1'),
    ],
  },
  {
    key: 'skale',
    label: 'SKALE',
    chainId: 1187947933,
    rpcEnvKey: 'VITE_SKALE_RPC_URL',
    defaultRpc: 'https://skale-base.skalenodes.com/v1/base',
    stablecoins: [USDC('0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20', 'Bridged USDC (SKALE Bridge)', '2')],
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

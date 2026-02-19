/**
 * Karma Kadabra V2 — Chain Configuration
 *
 * Single source of truth for all 8 supported EVM chains.
 * Mirrors NETWORK_CONFIG from mcp_server/integrations/x402/sdk_client.py.
 */

import {
  type Chain,
  type Address,
  defineChain,
} from "viem";
import {
  base,
  mainnet,
  polygon,
  arbitrum,
  celo,
  avalanche,
  optimism,
} from "viem/chains";

// Monad not in viem's built-in chains yet
export const monad: Chain = defineChain({
  id: 143,
  name: "Monad",
  nativeCurrency: { name: "MON", symbol: "MON", decimals: 18 },
  rpcUrls: { default: { http: ["https://rpc.monad.xyz"] } },
});

// ---------------------------------------------------------------------------
// Chain Info
// ---------------------------------------------------------------------------

export interface ChainInfo {
  name: string;
  chain: Chain;
  chainId: number;
  rpcUrl: string;
  usdc: Address;
  nativeSymbol: string;
  /** Disperse.app deployed and verified on this chain */
  disperseAvailable: boolean;
  /** deBridge DLN chain ID (may differ from native, e.g. Monad = 100000030) */
  debridgeChainId: string | null;
  /** Squid supports this chain */
  squidSupported: boolean;
}

/**
 * Disperse.app — same CREATE2 address on all chains where deployed.
 * Sends tokens/ETH to N recipients in 1 TX (45% gas savings).
 */
export const DISPERSE_ADDRESS: Address =
  "0xD152f549545093347A162Dce210e7293f1452150";

export const DISPERSE_ABI = [
  {
    name: "disperseEther",
    type: "function",
    stateMutability: "payable",
    inputs: [
      { name: "recipients", type: "address[]" },
      { name: "values", type: "uint256[]" },
    ],
    outputs: [],
  },
  {
    name: "disperseToken",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "token", type: "address" },
      { name: "recipients", type: "address[]" },
      { name: "values", type: "uint256[]" },
    ],
    outputs: [],
  },
] as const;

export const ERC20_ABI = [
  {
    name: "approve",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
  {
    name: "balanceOf",
    type: "function",
    stateMutability: "view",
    inputs: [{ name: "account", type: "address" }],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    name: "allowance",
    type: "function",
    stateMutability: "view",
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    name: "transfer",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "to", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
] as const;

// ---------------------------------------------------------------------------
// The 8 Target Chains
// ---------------------------------------------------------------------------

export const CHAINS: Record<string, ChainInfo> = {
  base: {
    name: "Base",
    chain: base,
    chainId: 8453,
    rpcUrl: "https://mainnet.base.org",
    usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    nativeSymbol: "ETH",
    disperseAvailable: true,
    debridgeChainId: "8453",
    squidSupported: true,
  },
  ethereum: {
    name: "Ethereum",
    chain: mainnet,
    chainId: 1,
    rpcUrl: "https://eth.llamarpc.com",
    usdc: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    nativeSymbol: "ETH",
    disperseAvailable: true,
    debridgeChainId: "1",
    squidSupported: true,
  },
  polygon: {
    name: "Polygon",
    chain: polygon,
    chainId: 137,
    rpcUrl: "https://polygon-bor-rpc.publicnode.com",
    usdc: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    nativeSymbol: "POL",
    disperseAvailable: true,
    debridgeChainId: "137",
    squidSupported: true,
  },
  arbitrum: {
    name: "Arbitrum",
    chain: arbitrum,
    chainId: 42161,
    rpcUrl: "https://arb1.arbitrum.io/rpc",
    usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    nativeSymbol: "ETH",
    disperseAvailable: true,
    debridgeChainId: "42161",
    squidSupported: true,
  },
  avalanche: {
    name: "Avalanche",
    chain: avalanche,
    chainId: 43114,
    rpcUrl: "https://api.avax.network/ext/bc/C/rpc",
    usdc: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    nativeSymbol: "AVAX",
    disperseAvailable: true,
    debridgeChainId: "43114",
    squidSupported: true,
  },
  optimism: {
    name: "Optimism",
    chain: optimism,
    chainId: 10,
    rpcUrl: "https://mainnet.optimism.io",
    usdc: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    nativeSymbol: "ETH",
    disperseAvailable: true,
    debridgeChainId: "10",
    squidSupported: true,
  },
  celo: {
    name: "Celo",
    chain: celo,
    chainId: 42220,
    rpcUrl: "https://forno.celo.org",
    usdc: "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
    nativeSymbol: "CELO",
    disperseAvailable: false, // Not verified — fallback to sequential
    debridgeChainId: null, // NOT supported by deBridge
    squidSupported: true,
  },
  monad: {
    name: "Monad",
    chain: monad,
    chainId: 143,
    rpcUrl: "https://rpc.monad.xyz",
    usdc: "0x754704Bc059F8C67012fEd69BC8A327a5aafb603",
    nativeSymbol: "MON",
    disperseAvailable: false, // Not verified — fallback to sequential
    debridgeChainId: "100000030", // DLN internal ID, NOT 143
    squidSupported: false, // NOT supported by Squid
  },
};

/** Default gas amounts per agent per chain (enough for ~10-20 TXs) */
export const DEFAULT_GAS_AMOUNTS: Record<string, string> = {
  base: "0.0005",      // ~$1.60 in ETH
  ethereum: "0.001",   // ~$3.20 in ETH
  polygon: "0.1",      // ~$0.04 in POL
  arbitrum: "0.0005",  // ~$1.60 in ETH
  avalanche: "0.01",   // ~$0.25 in AVAX
  optimism: "0.0005",  // ~$1.60 in ETH
  celo: "0.01",        // ~$0.005 in CELO
  monad: "0.01",       // ~$0.01 in MON
};

/** Get chain names sorted for consistent iteration */
export function getChainNames(): string[] {
  return Object.keys(CHAINS);
}

/** Get chain info or throw */
export function getChain(name: string): ChainInfo {
  const info = CHAINS[name];
  if (!info) throw new Error(`Unknown chain: ${name}. Valid: ${getChainNames().join(", ")}`);
  return info;
}

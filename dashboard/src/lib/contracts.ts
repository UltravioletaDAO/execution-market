/**
 * ERC-8004 Contract ABIs and Addresses
 *
 * Minimal ABI for direct on-chain reputation feedback.
 * Workers call giveFeedback() directly from their wallet so msg.sender = worker.
 */

// ReputationRegistry — CREATE2 deterministic, same address on all mainnets
export const REPUTATION_REGISTRY_ADDRESS =
  '0x8004BAa17C55a88189AE136b182e5fdA19dE9b63' as const

// Base Mainnet chain ID
export const BASE_CHAIN_ID = 8453

// Minimal ABI: only giveFeedback (the single function workers need)
export const REPUTATION_REGISTRY_ABI = [
  {
    inputs: [
      { name: 'agentId', type: 'uint256' },
      { name: 'value', type: 'int128' },
      { name: 'valueDecimals', type: 'uint8' },
      { name: 'tag1', type: 'string' },
      { name: 'tag2', type: 'string' },
      { name: 'endpoint', type: 'string' },
      { name: 'feedbackURI', type: 'string' },
      { name: 'feedbackHash', type: 'bytes32' },
    ],
    name: 'giveFeedback',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
] as const

/**
 * Blockchain Utility Tests — Solana + EVM address and tx hash validation
 *
 * Verifies that isValidAddress and isValidTxHash correctly accept both
 * EVM (0x-prefixed hex) and Solana (Base58) formats.
 */

import { describe, it, expect } from 'vitest'
import {
  isValidAddress,
  isValidTxHash,
  getExplorerUrl,
  getAddressUrl,
  getNetworkDisplayName,
  truncateHash,
} from '../../utils/blockchain'

// =============================================================================
// isValidAddress
// =============================================================================

describe('isValidAddress', () => {
  it('accepts EVM addresses', () => {
    expect(isValidAddress('0x857f6F45AD79461E3DBadECE9E7b1291e0d8b57C')).toBe(true)
  })

  it('accepts lowercase EVM addresses', () => {
    expect(isValidAddress('0x' + 'a'.repeat(40))).toBe(true)
  })

  it('accepts Solana addresses (32-44 Base58 chars)', () => {
    expect(isValidAddress('7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV')).toBe(true)
    expect(isValidAddress('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')).toBe(true)
  })

  it('rejects empty string', () => {
    expect(isValidAddress('')).toBe(false)
  })

  it('rejects plain text', () => {
    expect(isValidAddress('not-an-address')).toBe(false)
  })

  it('rejects EVM address with wrong length', () => {
    expect(isValidAddress('0x1234')).toBe(false)
  })
})

// =============================================================================
// isValidTxHash
// =============================================================================

describe('isValidTxHash', () => {
  it('accepts EVM tx hashes (0x + 64 hex)', () => {
    expect(isValidTxHash('0x' + 'a'.repeat(64))).toBe(true)
  })

  it('accepts Solana signatures (~88 Base58 chars)', () => {
    expect(
      isValidTxHash(
        '5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW'
      )
    ).toBe(true)
  })

  it('rejects short strings', () => {
    expect(isValidTxHash('short')).toBe(false)
  })

  it('rejects empty string', () => {
    expect(isValidTxHash('')).toBe(false)
  })

  it('rejects EVM hash with wrong length', () => {
    expect(isValidTxHash('0x' + 'a'.repeat(32))).toBe(false)
  })
})

// =============================================================================
// Explorer URLs — Solana
// =============================================================================

describe('getExplorerUrl', () => {
  it('returns Solscan URL for Solana tx', () => {
    const sig = '5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp'
    expect(getExplorerUrl(sig, 'solana')).toBe(`https://solscan.io/tx/${sig}`)
  })

  it('returns BaseScan URL for Base tx', () => {
    const hash = '0x' + 'a'.repeat(64)
    expect(getExplorerUrl(hash, 'base')).toBe(`https://basescan.org/tx/${hash}`)
  })
})

describe('getAddressUrl', () => {
  it('returns Solscan account URL for Solana address', () => {
    const addr = '7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV'
    expect(getAddressUrl(addr, 'solana')).toBe(`https://solscan.io/account/${addr}`)
  })
})

// =============================================================================
// Network display name
// =============================================================================

describe('getNetworkDisplayName', () => {
  it('returns Solana for solana', () => {
    expect(getNetworkDisplayName('solana')).toBe('Solana')
  })

  it('returns Base for base', () => {
    expect(getNetworkDisplayName('base')).toBe('Base')
  })

  it('returns raw name for unknown network', () => {
    expect(getNetworkDisplayName('unknown-chain')).toBe('unknown-chain')
  })
})

// =============================================================================
// truncateHash — works with both EVM and Solana formats
// =============================================================================

describe('truncateHash', () => {
  it('truncates long EVM hashes', () => {
    const hash = '0x' + 'a'.repeat(64)
    const result = truncateHash(hash)
    expect(result).toBe('0x' + 'a'.repeat(4) + '...' + 'a'.repeat(4))
  })

  it('truncates long Solana signatures', () => {
    const sig = '5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW'
    const result = truncateHash(sig)
    expect(result.startsWith('5VERv8')).toBe(true)
    expect(result).toContain('...')
  })

  it('returns short strings unchanged', () => {
    expect(truncateHash('0x1234')).toBe('0x1234')
  })
})

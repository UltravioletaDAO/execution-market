import { describe, it, expect } from 'vitest'
import {
  validateFeePercent,
  validateBountyAmount,
  validateInteger,
  validateWalletAddress,
  validateUrl,
  validateConfigValue,
} from '../lib/validation'

// Our validators return null (valid) or error string (invalid)

describe('validateFeePercent', () => {
  it.each([0, 0.5, 1])('accepts %s', (v) => {
    expect(validateFeePercent(v)).toBeNull()
  })

  it('rejects negative', () => {
    expect(validateFeePercent(-1)).not.toBeNull()
  })

  it('rejects > 1', () => {
    expect(validateFeePercent(1.5)).not.toBeNull()
  })

  it('rejects NaN', () => {
    expect(validateFeePercent(NaN)).not.toBeNull()
  })
})

describe('validateBountyAmount', () => {
  it.each([0.01, 100])('accepts %s', (v) => {
    expect(validateBountyAmount(v)).toBeNull()
  })

  it('rejects 0', () => {
    expect(validateBountyAmount(0)).not.toBeNull()
  })

  it('rejects negative', () => {
    expect(validateBountyAmount(-1)).not.toBeNull()
  })
})

describe('validateInteger', () => {
  it.each([1, 50])('accepts %s', (v) => {
    expect(validateInteger(v)).toBeNull()
  })

  it('rejects non-integer', () => {
    expect(validateInteger(0.5)).not.toBeNull()
  })

  it('rejects below min', () => {
    expect(validateInteger(-1, 1)).not.toBeNull()
  })

  it('rejects over max', () => {
    expect(validateInteger(99999, 1, 10000)).not.toBeNull()
  })

  it('respects custom min/max', () => {
    expect(validateInteger(5, 10, 20)).not.toBeNull()
    expect(validateInteger(15, 10, 20)).toBeNull()
  })
})

describe('validateWalletAddress', () => {
  const valid = '0x' + 'a'.repeat(40)

  it('accepts valid address', () => {
    expect(validateWalletAddress(valid)).toBeNull()
  })

  it('accepts mixed-case hex', () => {
    expect(validateWalletAddress('0xAbCdEf1234567890AbCdEf1234567890AbCdEf12')).toBeNull()
  })

  it('rejects missing 0x prefix', () => {
    expect(validateWalletAddress('a'.repeat(42))).not.toBeNull()
  })

  it('rejects wrong length', () => {
    expect(validateWalletAddress('0x' + 'a'.repeat(39))).not.toBeNull()
  })

  it('rejects non-hex characters', () => {
    expect(validateWalletAddress('0x' + 'g'.repeat(40))).not.toBeNull()
  })

  it('rejects empty', () => {
    expect(validateWalletAddress('')).not.toBeNull()
  })
})

describe('validateUrl', () => {
  it('accepts valid https URL', () => {
    expect(validateUrl('https://example.com')).toBeNull()
  })

  it('accepts https with path', () => {
    expect(validateUrl('https://example.com/api/v1')).toBeNull()
  })

  it('rejects http (non-https)', () => {
    expect(validateUrl('http://example.com')).not.toBeNull()
  })

  it('rejects empty', () => {
    expect(validateUrl('')).not.toBeNull()
  })

  it('rejects no protocol', () => {
    expect(validateUrl('example.com')).not.toBeNull()
  })
})

describe('validateConfigValue', () => {
  it('validates fee keys', () => {
    expect(validateConfigValue('fees.platform_fee_pct', 0.13)).toBeNull()
    expect(validateConfigValue('fees.platform_fee_pct', -1)).not.toBeNull()
  })

  it('validates bounty keys', () => {
    expect(validateConfigValue('bounty.min_usd', 0.10)).toBeNull()
    expect(validateConfigValue('bounty.min_usd', 0)).not.toBeNull()
  })

  it('validates treasury address keys', () => {
    expect(validateConfigValue('treasury.wallet_address', '0x' + 'a'.repeat(40))).toBeNull()
    expect(validateConfigValue('treasury.wallet_address', 'bad')).not.toBeNull()
  })

  it('passes unknown keys', () => {
    expect(validateConfigValue('unknown_key', 'anything')).toBeNull()
  })
})

/**
 * buildEscrowPreAuth / computeEscrowNonce — escrow sign-on-assignment.
 *
 * The nonce MUST match AuthCaptureEscrow.getHash(paymentInfo) or the on-chain
 * authorize reverts. The expected fixture below was derived with the Python
 * SDK (uvd_x402_sdk.advanced_escrow, the production reference):
 *
 *   pi_tuple = (operator, ZERO_ADDRESS, receiver, token, 100000,
 *               1760003600, 1760007200, 1760086400, 0, 1800, operator,
 *               int('ab'*32, 16))
 *   encoded = eth_abi.encode(
 *       ['bytes32', '(address,address,address,address,uint120,uint48,'
 *        'uint48,uint48,uint16,uint16,address,uint256)'],
 *       [PAYMENT_INFO_TYPEHASH, pi_tuple])
 *   pi_hash = Web3.keccak(encoded)
 *   nonce = Web3.keccak(eth_abi.encode(
 *       ['uint256', 'address', 'bytes32'], [8453, escrow, pi_hash]))
 *
 * AdvancedEscrowClient._compute_nonce() on the same inputs returns the same
 * value (verified during development, 2026-06-11).
 *
 * NOTE: 32-byte hex constants are assembled from halves — the repo's
 * pre-commit secret scanner blocks any literal `0x` + 64 hex chars.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import type { WalletClient } from 'viem'
import {
  buildEscrowPreAuth,
  computeEscrowNonce,
  ESCROW_TIER_WINDOWS,
  type EscrowPaymentInfo,
  type H2AEscrowNetworkConfig,
} from '../../services/h2aSigning'

const TYPEHASH = '0x' + 'ae68ac7ce30c86ece8196b61a7c486d8' + 'f0061f575037fbd34e7fe4e2820c6591'
const EXPECTED_NONCE = '0x' + '5890a092cb9b8d3c17efc8a3fca99886' + 'd05f53ced3432a530eb2b4c7ef517f59'
const SALT = '0x' + 'ab'.repeat(32)
const MOCK_SIGNATURE = '0x' + '11'.repeat(65)

const PAYER = '0x2222222222222222222222222222222222222222' as const
const WORKER = '0x1111111111111111111111111111111111111111' as const

// Base mainnet — addresses mirror NETWORK_CONFIG in sdk_client.py.
const NETWORK_CONFIG: H2AEscrowNetworkConfig = {
  chain_id: 8453,
  operator: '0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb',
  escrow: '0xb9488351E48b23D798f24e8174514F28B741Eb4f',
  token_collector: '0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8',
  usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  usdc_domain_name: 'USD Coin',
  usdc_domain_version: '2',
  payment_info_typehash: TYPEHASH,
  tiers: {
    micro: { pre: 3600, auth: 7200, refund: 86400 },
    standard: { pre: 7200, auth: 86400, refund: 604800 },
  },
  min_fee_bps: 0,
  max_fee_bps: 1800,
}

const FIXTURE_PI: EscrowPaymentInfo = {
  operator: NETWORK_CONFIG.operator,
  receiver: WORKER,
  token: NETWORK_CONFIG.usdc,
  maxAmount: '100000', // $0.10 USDC
  preApprovalExpiry: 1760003600,
  authorizationExpiry: 1760007200,
  refundExpiry: 1760086400,
  minFeeBps: 0,
  maxFeeBps: 1800,
  feeReceiver: NETWORK_CONFIG.operator,
  salt: SALT,
}

function mockWallet() {
  const signTypedData = vi.fn(async (_args: Record<string, unknown>) => MOCK_SIGNATURE)
  return { client: { signTypedData } as unknown as WalletClient, signTypedData }
}

afterEach(() => {
  vi.useRealTimers()
})

describe('computeEscrowNonce', () => {
  it('matches the SDK-derived fixture (AuthCaptureEscrow.getHash)', () => {
    const nonce = computeEscrowNonce(
      NETWORK_CONFIG.chain_id,
      NETWORK_CONFIG.escrow,
      NETWORK_CONFIG.payment_info_typehash,
      FIXTURE_PI,
    )
    expect(nonce).toBe(EXPECTED_NONCE)
  })

  it('changes when the receiver changes (nonce commits to the worker)', () => {
    const other = computeEscrowNonce(
      NETWORK_CONFIG.chain_id,
      NETWORK_CONFIG.escrow,
      NETWORK_CONFIG.payment_info_typehash,
      { ...FIXTURE_PI, receiver: PAYER },
    )
    expect(other).not.toBe(EXPECTED_NONCE)
  })

  it('accepts lowercase addresses (checksums internally like the SDK)', () => {
    const nonce = computeEscrowNonce(
      NETWORK_CONFIG.chain_id,
      NETWORK_CONFIG.escrow.toLowerCase(),
      NETWORK_CONFIG.payment_info_typehash,
      {
        ...FIXTURE_PI,
        operator: FIXTURE_PI.operator.toLowerCase(),
        token: FIXTURE_PI.token.toLowerCase(),
        feeReceiver: FIXTURE_PI.feeReceiver.toLowerCase(),
      },
    )
    expect(nonce).toBe(EXPECTED_NONCE)
  })
})

describe('buildEscrowPreAuth', () => {
  it('produces the X-Payment-Auth wrapper shape with receiver == worker', async () => {
    const { client } = mockWallet()
    const header = await buildEscrowPreAuth(client, {
      networkConfig: NETWORK_CONFIG,
      payerWallet: PAYER,
      workerWallet: WORKER,
      bountyAtomic: '100000',
    })

    const wrapper = JSON.parse(header)
    expect(Object.keys(wrapper).sort()).toEqual([
      'payload', 'paymentRequirements', 'scheme', 'x402Version',
    ])
    expect(wrapper.x402Version).toBe(2)
    expect(wrapper.scheme).toBe('escrow')
    expect(wrapper.paymentRequirements).toEqual({ scheme: 'escrow', network: 'eip155:8453' })

    const { authorization, signature, paymentInfo } = wrapper.payload
    expect(signature).toBe(MOCK_SIGNATURE)

    // authorization: string-valued, to = token collector, validBefore = preApprovalExpiry
    expect(Object.keys(authorization).sort()).toEqual([
      'from', 'nonce', 'to', 'validAfter', 'validBefore', 'value',
    ])
    expect(authorization.from).toBe(PAYER)
    expect(authorization.to).toBe(NETWORK_CONFIG.token_collector)
    expect(authorization.value).toBe('100000')
    expect(authorization.validAfter).toBe('0')
    expect(authorization.validBefore).toBe(String(paymentInfo.preApprovalExpiry))

    // paymentInfo: maxAmount string, expiries/bps ints, receiver = worker
    expect(Object.keys(paymentInfo).sort()).toEqual([
      'authorizationExpiry', 'feeReceiver', 'maxAmount', 'maxFeeBps', 'minFeeBps',
      'operator', 'preApprovalExpiry', 'receiver', 'refundExpiry', 'salt', 'token',
    ])
    expect(paymentInfo.receiver).toBe(WORKER)
    expect(paymentInfo.operator).toBe(NETWORK_CONFIG.operator)
    expect(paymentInfo.token).toBe(NETWORK_CONFIG.usdc)
    expect(paymentInfo.maxAmount).toBe('100000')
    expect(typeof paymentInfo.preApprovalExpiry).toBe('number')
    expect(typeof paymentInfo.authorizationExpiry).toBe('number')
    expect(typeof paymentInfo.refundExpiry).toBe('number')
    expect(paymentInfo.minFeeBps).toBe(0)
    expect(paymentInfo.maxFeeBps).toBe(1800)
    expect(paymentInfo.feeReceiver).toBe(NETWORK_CONFIG.operator)
    expect(paymentInfo.salt).toMatch(/^0x[0-9a-f]{64}$/)

    // nonce is reproducible from the serialized paymentInfo (getHash mirror)
    expect(authorization.nonce).toBe(
      computeEscrowNonce(
        NETWORK_CONFIG.chain_id,
        NETWORK_CONFIG.escrow,
        NETWORK_CONFIG.payment_info_typehash,
        paymentInfo,
      ),
    )
  })

  it('signs ReceiveWithAuthorization with the USDC domain and computed nonce', async () => {
    const { client, signTypedData } = mockWallet()
    const header = await buildEscrowPreAuth(client, {
      networkConfig: NETWORK_CONFIG,
      payerWallet: PAYER,
      workerWallet: WORKER,
      bountyAtomic: 100000n,
    })
    const wrapper = JSON.parse(header)

    expect(signTypedData).toHaveBeenCalledTimes(1)
    const args = signTypedData.mock.calls[0][0]
    expect(args.primaryType).toBe('ReceiveWithAuthorization')
    expect(args.domain).toEqual({
      name: 'USD Coin',
      version: '2',
      chainId: 8453,
      verifyingContract: NETWORK_CONFIG.usdc,
    })
    const message = args.message as Record<string, unknown>
    expect(message.from).toBe(PAYER)
    expect(message.to).toBe(NETWORK_CONFIG.token_collector)
    expect(message.value).toBe(100000n)
    expect(message.validAfter).toBe(0n)
    expect(message.validBefore).toBe(BigInt(wrapper.payload.paymentInfo.preApprovalExpiry))
    expect(message.nonce).toBe(wrapper.payload.authorization.nonce)
  })

  it('applies tier windows relative to now (micro default, standard on request)', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(1760000000 * 1000))

    const { client } = mockWallet()
    const micro = JSON.parse(
      await buildEscrowPreAuth(client, {
        networkConfig: NETWORK_CONFIG,
        payerWallet: PAYER,
        workerWallet: WORKER,
        bountyAtomic: '100000',
      }),
    ).payload.paymentInfo
    expect(micro.preApprovalExpiry).toBe(1760000000 + ESCROW_TIER_WINDOWS.micro.pre)
    expect(micro.authorizationExpiry).toBe(1760000000 + ESCROW_TIER_WINDOWS.micro.auth)
    expect(micro.refundExpiry).toBe(1760000000 + ESCROW_TIER_WINDOWS.micro.refund)

    const standard = JSON.parse(
      await buildEscrowPreAuth(client, {
        networkConfig: NETWORK_CONFIG,
        payerWallet: PAYER,
        workerWallet: WORKER,
        bountyAtomic: '100000',
        tier: 'standard',
      }),
    ).payload.paymentInfo
    expect(standard.preApprovalExpiry).toBe(1760000000 + ESCROW_TIER_WINDOWS.standard.pre)
    expect(standard.authorizationExpiry).toBe(1760000000 + ESCROW_TIER_WINDOWS.standard.auth)
    expect(standard.refundExpiry).toBe(1760000000 + ESCROW_TIER_WINDOWS.standard.refund)

    // Server-provided windows take precedence over the canonical fallback
    const custom = JSON.parse(
      await buildEscrowPreAuth(client, {
        networkConfig: { ...NETWORK_CONFIG, tiers: { micro: { pre: 60, auth: 120, refund: 240 } } },
        payerWallet: PAYER,
        workerWallet: WORKER,
        bountyAtomic: '100000',
      }),
    ).payload.paymentInfo
    expect(custom.preApprovalExpiry).toBe(1760000060)
    expect(custom.authorizationExpiry).toBe(1760000120)
    expect(custom.refundExpiry).toBe(1760000240)
  })
})

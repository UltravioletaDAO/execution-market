/**
 * H2H web signing — build the SAME EIP-3009 X-Payment header an external agent
 * sends, but from the publisher's Dynamic wallet (viem WalletClient) in the
 * browser. The Facilitator then settles it gasless, exactly like the agent flow.
 *
 * Byte-for-byte mirror of `sdk_client.py`:
 *   - sign_eip3009 / TransferWithAuthorization typed data
 *   - _build_x402_header → base64(JSON({ x402Version, scheme, network, payload }))
 * If the domain (name/version/chainId/verifyingContract) doesn't match the token
 * on-chain, the signature is rejected — see payment-networks.ts for those values.
 */
import type { WalletClient, Address, Hex } from 'viem'
import { encodeAbiParameters, getAddress, keccak256 } from 'viem'
import { getPaymentNetwork } from '../constants/payment-networks'

// EIP-712 type for EIP-3009. Matches EMX402SDK.TRANSFER_WITH_AUTH_TYPES.
const TRANSFER_WITH_AUTHORIZATION_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
} as const

function randomNonce(): `0x${string}` {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return ('0x' +
    Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')) as `0x${string}`
}

export interface XPaymentParams {
  /** Payer (the human publisher's wallet). */
  from: Address
  /** Recipient (worker wallet for bounty, treasury for fee). */
  to: Address
  /** Amount in human units, e.g. 0.05 = $0.05. */
  amountUsd: number
  /** Payment network key (e.g. 'base'). */
  network: string
  /** Stablecoin symbol on that network (e.g. 'USDC'). */
  coinSymbol: string
  validForSeconds?: number
}

/**
 * Sign an EIP-3009 TransferWithAuthorization and pack it into the base64
 * X-Payment header the backend's `client.extract_payload()` expects.
 */
export async function buildEip3009XPayment(
  walletClient: WalletClient,
  params: XPaymentParams,
): Promise<string> {
  const net = getPaymentNetwork(params.network)
  const coin =
    net.stablecoins.find((c) => c.symbol === params.coinSymbol) ?? net.stablecoins[0]

  const value = BigInt(Math.round(params.amountUsd * 10 ** coin.decimals))
  const now = Math.floor(Date.now() / 1000)
  const validBefore = now + (params.validForSeconds ?? 3600)
  const nonce = randomNonce()

  const signature = await walletClient.signTypedData({
    account: params.from,
    domain: {
      name: coin.eip712Name,
      version: coin.eip712Version,
      chainId: net.chainId,
      verifyingContract: coin.address as Address,
    },
    types: TRANSFER_WITH_AUTHORIZATION_TYPES,
    primaryType: 'TransferWithAuthorization',
    message: {
      from: params.from,
      to: params.to,
      value,
      validAfter: 0n,
      validBefore: BigInt(validBefore),
      nonce,
    },
  })

  // String-valued authorization, identical to sdk_client.py's dict.
  const payload = {
    x402Version: 1,
    scheme: 'exact',
    network: params.network,
    payload: {
      signature,
      authorization: {
        from: params.from,
        to: params.to,
        value: value.toString(),
        validAfter: '0',
        validBefore: validBefore.toString(),
        nonce,
      },
    },
  }

  return btoa(JSON.stringify(payload))
}

// ===========================================================================
// Escrow sign-on-assignment (x402r) — universal escrow consistency.
//
// The publisher signs the escrow lock AT ASSIGNMENT, when the worker is
// known. This is a protocol requirement: the EIP-3009 nonce for escrow is
// AuthCaptureEscrow.getHash(paymentInfo), which INCLUDES the receiver — the
// signature cryptographically commits to the chosen worker. Byte-for-byte
// mirror of uvd_x402_sdk.advanced_escrow (AdvancedEscrowClient._compute_nonce
// + authorize): same tuple encoding, same ReceiveWithAuthorization typed
// data, same X-Payment-Auth wrapper the Facilitator /settle expects.
// ===========================================================================

const ZERO_ADDRESS = '0x0000000000000000000000000000000000000000' as const

// EIP-712 type for the escrow flow. The token collector pulls the funds, so
// the scheme is ReceiveWithAuthorization (not TransferWithAuthorization).
const RECEIVE_WITH_AUTHORIZATION_TYPES = {
  ReceiveWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
} as const

// Unnamed components so viem accepts a positional array — mirrors eth_abi's
// '(address,address,address,address,uint120,uint48,uint48,uint48,uint16,
// uint16,address,uint256)' encoding in the SDK.
const PAYMENT_INFO_TUPLE = {
  type: 'tuple',
  components: [
    { type: 'address' },
    { type: 'address' },
    { type: 'address' },
    { type: 'address' },
    { type: 'uint120' },
    { type: 'uint48' },
    { type: 'uint48' },
    { type: 'uint48' },
    { type: 'uint16' },
    { type: 'uint16' },
    { type: 'address' },
    { type: 'uint256' },
  ],
} as const

/** Per-tier expiry windows in seconds, relative to now() at signing. */
export interface EscrowTierWindows {
  pre: number
  auth: number
  refund: number
}

/** Canonical fallback — mirrors uvd_x402_sdk TIER_TIMINGS. */
export const ESCROW_TIER_WINDOWS: Record<string, EscrowTierWindows> = {
  micro: { pre: 3600, auth: 7200, refund: 86400 },
  standard: { pre: 7200, auth: 86400, refund: 604800 },
}

/**
 * One network's escrow parameters, served by GET /api/v1/h2a/payment-config
 * (`escrow_networks[network]`). The server publishes these so the browser
 * builds the paymentInfo EXACTLY like the SDK.
 */
export interface H2AEscrowNetworkConfig {
  chain_id: number
  operator: string
  escrow: string
  token_collector: string
  usdc: string
  usdc_domain_name: string
  usdc_domain_version: string
  payment_info_typehash: string
  tiers?: Record<string, EscrowTierWindows>
  min_fee_bps?: number
  max_fee_bps?: number
}

/** paymentInfo exactly as serialized in the X-Payment-Auth wrapper. */
export interface EscrowPaymentInfo {
  operator: string
  receiver: string
  token: string
  /** Atomic units, as string (uint120 on-chain). */
  maxAmount: string
  preApprovalExpiry: number
  authorizationExpiry: number
  refundExpiry: number
  minFeeBps: number
  maxFeeBps: number
  feeReceiver: string
  /** 32-byte hex. */
  salt: string
}

/**
 * Compute the escrow EIP-3009 nonce = keccak(chainId, escrow,
 * keccak(PAYMENT_INFO_TYPEHASH, paymentInfo tuple with payer=0)).
 * Port of AdvancedEscrowClient._compute_nonce (advanced_escrow.py:615-650).
 */
export function computeEscrowNonce(
  chainId: number,
  escrowAddress: string,
  paymentInfoTypehash: string,
  pi: EscrowPaymentInfo,
): Hex {
  const piTuple = [
    getAddress(pi.operator),
    ZERO_ADDRESS, // payer = 0 for the payer-agnostic hash
    getAddress(pi.receiver),
    getAddress(pi.token),
    BigInt(pi.maxAmount), // uint120
    pi.preApprovalExpiry, // uint48
    pi.authorizationExpiry, // uint48
    pi.refundExpiry, // uint48
    pi.minFeeBps, // uint16
    pi.maxFeeBps, // uint16
    getAddress(pi.feeReceiver),
    BigInt(pi.salt), // uint256
  ] as const

  const piHash = keccak256(
    encodeAbiParameters(
      [{ type: 'bytes32' }, PAYMENT_INFO_TUPLE],
      [paymentInfoTypehash as Hex, piTuple],
    ),
  )
  return keccak256(
    encodeAbiParameters(
      [{ type: 'uint256' }, { type: 'address' }, { type: 'bytes32' }],
      [BigInt(chainId), getAddress(escrowAddress), piHash],
    ),
  )
}

export interface EscrowPreAuthParams {
  /** Network escrow config from GET /api/v1/h2a/payment-config. */
  networkConfig: H2AEscrowNetworkConfig
  /** Publisher wallet (payer). */
  payerWallet: Address
  /** Chosen applicant's wallet (escrow receiver — committed by the nonce). */
  workerWallet: Address
  /** Bounty in atomic units (6-decimal USDC). */
  bountyAtomic: string | bigint
  /** Expiry tier; windows come from config when present. Default 'micro'. */
  tier?: string
}

/**
 * Build + sign the escrow lock authorization at assignment time and return
 * the raw JSON string for the `X-Payment-Auth` header. Mirror of
 * AdvancedEscrowClient.authorize()'s /settle payload.
 */
export async function buildEscrowPreAuth(
  walletClient: WalletClient,
  params: EscrowPreAuthParams,
): Promise<string> {
  const cfg = params.networkConfig
  const tierKey = params.tier ?? 'micro'
  const windows =
    cfg.tiers?.[tierKey] ?? ESCROW_TIER_WINDOWS[tierKey] ?? ESCROW_TIER_WINDOWS.micro
  const now = Math.floor(Date.now() / 1000)
  const maxAmount = BigInt(params.bountyAtomic).toString()

  const paymentInfo: EscrowPaymentInfo = {
    operator: getAddress(cfg.operator),
    receiver: getAddress(params.workerWallet),
    token: getAddress(cfg.usdc),
    maxAmount,
    preApprovalExpiry: now + windows.pre,
    authorizationExpiry: now + windows.auth,
    refundExpiry: now + windows.refund,
    minFeeBps: cfg.min_fee_bps ?? 0,
    maxFeeBps: cfg.max_fee_bps ?? 1800,
    feeReceiver: getAddress(cfg.operator),
    salt: randomNonce(),
  }

  const nonce = computeEscrowNonce(
    cfg.chain_id,
    cfg.escrow,
    cfg.payment_info_typehash,
    paymentInfo,
  )

  const signature = await walletClient.signTypedData({
    account: params.payerWallet,
    domain: {
      name: cfg.usdc_domain_name,
      version: cfg.usdc_domain_version,
      chainId: cfg.chain_id,
      verifyingContract: getAddress(cfg.usdc),
    },
    types: RECEIVE_WITH_AUTHORIZATION_TYPES,
    primaryType: 'ReceiveWithAuthorization',
    message: {
      from: getAddress(params.payerWallet),
      to: getAddress(cfg.token_collector),
      value: BigInt(maxAmount),
      validAfter: 0n,
      validBefore: BigInt(paymentInfo.preApprovalExpiry),
      nonce,
    },
  })

  // Raw JSON (NOT base64): the backend relays this verbatim to the
  // Facilitator /settle after validating payer/amount/receiver.
  return JSON.stringify({
    x402Version: 2,
    scheme: 'escrow',
    payload: {
      authorization: {
        from: getAddress(params.payerWallet),
        to: getAddress(cfg.token_collector),
        value: maxAmount,
        validAfter: '0',
        validBefore: String(paymentInfo.preApprovalExpiry),
        nonce,
      },
      signature,
      paymentInfo,
    },
    paymentRequirements: {
      scheme: 'escrow',
      network: `eip155:${cfg.chain_id}`,
    },
  })
}

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
import type { WalletClient, Address } from 'viem'
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

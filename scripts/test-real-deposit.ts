/**
 * Test REAL x402r escrow deposit on Base Mainnet.
 *
 * Flow:
 * 1. Agent signs EIP-3009 transferWithAuthorization for USDC
 * 2. Calls relay's deposit function with the signature
 * 3. Relay executes transferWithAuthorization → USDC to relay → to escrow
 * 4. Escrow records deposit
 *
 * Usage: npx tsx test-real-deposit.ts [amount_usdc]
 * Example: npx tsx test-real-deposit.ts 0.01
 */
import {
  createPublicClient,
  createWalletClient,
  http,
  parseAbi,
  formatUnits,
  parseUnits,
  encodeFunctionData,
  keccak256,
  encodeAbiParameters,
  parseAbiParameters,
  type Hex,
} from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import crypto from 'crypto'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const pk = process.env.WALLET_PRIVATE_KEY as `0x${string}`
const account = privateKeyToAccount(pk)

const rpcUrl = process.env.BASE_MAINNET_RPC_URL || 'https://base-mainnet.g.alchemy.com/v2/demo'
const publicClient = createPublicClient({ chain: base, transport: http(rpcUrl) })
const walletClient = createWalletClient({ account, chain: base, transport: http(rpcUrl) })

const RELAY = '0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3' as const
const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const
const VAULT = '0x0b3fC8BA8952C6cA6807F667894b0b7c9C40FC8b' as const

// EIP-3009 domain for USDC on Base
const USDC_DOMAIN = {
  name: 'USD Coin',
  version: '2',
  chainId: 8453,
  verifyingContract: USDC,
} as const

// EIP-3009 TransferWithAuthorization types
const TRANSFER_WITH_AUTH_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
} as const

// The relay deposit function selector: 0x1f36ab90
// Params: (address from, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s)
const RELAY_DEPOSIT_ABI = parseAbi([
  'function executeDeposit(address from, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s)',
])

async function getBalance(address: `0x${string}`) {
  return publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [address],
  })
}

async function main() {
  const amountStr = process.argv[2] || '0.01'
  const amountUsdc = parseFloat(amountStr)
  const amountAtomic = parseUnits(amountStr, 6)

  console.log('=== Real x402r Escrow Deposit ===')
  console.log('Wallet:', account.address)
  console.log('Amount:', amountUsdc, 'USDC')
  console.log('Network: Base Mainnet')
  console.log('')

  // Pre-checks
  const walletUsdc = await getBalance(account.address)
  const walletEth = await publicClient.getBalance({ address: account.address })
  console.log('Wallet USDC:', formatUnits(walletUsdc, 6))
  console.log('Wallet ETH:', formatUnits(walletEth, 18))

  if (walletUsdc < amountAtomic) {
    console.error('Insufficient USDC balance!')
    process.exit(1)
  }

  // State before
  const relayBefore = await getBalance(RELAY)
  const escrowBefore = await getBalance(ESCROW)
  const vaultBefore = await getBalance(VAULT)
  const tpBefore = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })

  console.log('\nBefore deposit:')
  console.log('  Relay USDC:', formatUnits(relayBefore, 6))
  console.log('  Escrow USDC:', formatUnits(escrowBefore, 6))
  console.log('  Vault USDC:', formatUnits(vaultBefore, 6))
  console.log('  totalPrincipal:', formatUnits(tpBefore, 6))

  // Step 1: Sign EIP-3009 TransferWithAuthorization
  console.log('\n--- Step 1: Sign EIP-3009 Authorization ---')

  const nonce = ('0x' + crypto.randomBytes(32).toString('hex')) as Hex
  const validAfter = 0n
  const validBefore = BigInt(Math.floor(Date.now() / 1000) + 3600) // 1 hour from now

  console.log('Nonce:', nonce)
  console.log('Valid before:', new Date(Number(validBefore) * 1000).toISOString())

  const signature = await walletClient.signTypedData({
    domain: USDC_DOMAIN,
    types: TRANSFER_WITH_AUTH_TYPES,
    primaryType: 'TransferWithAuthorization',
    message: {
      from: account.address,
      to: RELAY,
      value: amountAtomic,
      validAfter,
      validBefore,
      nonce,
    },
  })

  console.log('Signature:', signature.substring(0, 20) + '...')

  // Parse signature into v, r, s
  const r = ('0x' + signature.slice(2, 66)) as Hex
  const s = ('0x' + signature.slice(66, 130)) as Hex
  const v = parseInt(signature.slice(130, 132), 16)

  console.log('v:', v, 'r:', r.substring(0, 10) + '...', 's:', s.substring(0, 10) + '...')

  // Step 2: Call relay deposit function
  console.log('\n--- Step 2: Call Relay Deposit ---')

  // Encode the call manually using the selector 0x1f36ab90
  const calldata = encodeAbiParameters(
    parseAbiParameters('address, uint256, uint256, uint256, bytes32, uint8, bytes32, bytes32'),
    [account.address, amountAtomic, validAfter, validBefore, nonce, v, r, s],
  )
  const fullCalldata = ('0x1f36ab90' + calldata.slice(2)) as Hex

  // Execute directly (skip simulation to avoid RPC rate limits)
  console.log('Executing...')
  const txHash = await walletClient.sendTransaction({
    to: RELAY,
    data: fullCalldata,
  })

  console.log('TX:', txHash)
  console.log('BaseScan: https://basescan.org/tx/' + txHash)

  const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash })
  console.log('Status:', receipt.status)
  console.log('Gas used:', receipt.gasUsed.toString())

  for (const log of receipt.logs) {
    console.log('\nLog from:', log.address)
    console.log('  Topics:', log.topics.map(t => t.substring(0, 20) + '...'))
    console.log('  Data:', log.data?.substring(0, 130))
  }

  // State after
  console.log('\n--- After deposit ---')
  const relayAfter = await getBalance(RELAY)
  const escrowAfter = await getBalance(ESCROW)
  const vaultAfter = await getBalance(VAULT)
  const tpAfter = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })
  const walletUsdcAfter = await getBalance(account.address)

  console.log('  Wallet USDC:', formatUnits(walletUsdcAfter, 6), `(was ${formatUnits(walletUsdc, 6)})`)
  console.log('  Relay USDC:', formatUnits(relayAfter, 6), `(was ${formatUnits(relayBefore, 6)})`)
  console.log('  Escrow USDC:', formatUnits(escrowAfter, 6), `(was ${formatUnits(escrowBefore, 6)})`)
  console.log('  Vault USDC:', formatUnits(vaultAfter, 6), `(was ${formatUnits(vaultBefore, 6)})`)
  console.log('  totalPrincipal:', formatUnits(tpAfter, 6), `(was ${formatUnits(tpBefore, 6)})`)

  // Check user deposits
  try {
    const rawResult = await publicClient.call({
      to: ESCROW,
      data: ('0x2a5bf6d2000000000000000000000000' + account.address.slice(2).toLowerCase()) as `0x${string}`,
    })
    console.log('  getUserDeposits:', rawResult.data?.substring(0, 400))
  } catch (e: any) {
    console.log('  getUserDeposits error')
  }

  const ethAfter = await publicClient.getBalance({ address: account.address })
  console.log('\n  ETH remaining:', formatUnits(ethAfter, 18))
  console.log('  ETH spent:', formatUnits(walletEth - ethAfter, 18))
}

main().catch(console.error)

/**
 * Test REAL x402r escrow REFUND on Base Mainnet.
 * Returns escrowed funds back to the agent.
 *
 * Usage: npx tsx test-refund.ts [amount_usdc]
 * Example: npx tsx test-refund.ts 0.01
 */
import {
  createPublicClient,
  createWalletClient,
  http,
  parseAbi,
  formatUnits,
  parseUnits,
  encodeAbiParameters,
  parseAbiParameters,
  type Hex,
} from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const pk = process.env.WALLET_PRIVATE_KEY as `0x${string}`
const account = privateKeyToAccount(pk)
const rpcUrl = process.env.BASE_MAINNET_RPC_URL || 'https://mainnet.base.org'

const publicClient = createPublicClient({ chain: base, transport: http(rpcUrl) })
const walletClient = createWalletClient({ account, chain: base, transport: http(rpcUrl) })

const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const
const VAULT = '0x0b3fC8BA8952C6cA6807F667894b0b7c9C40FC8b' as const

async function bal(addr: `0x${string}`) {
  return publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [addr],
  })
}

async function main() {
  const amountStr = process.argv[2] || '0.01'
  const amountAtomic = parseUnits(amountStr, 6)

  console.log('=== Real x402r Escrow REFUND ===')
  console.log('Wallet:', account.address)
  console.log('Amount:', amountStr, 'USDC')
  console.log('Network: Base Mainnet')
  console.log('')

  // State before
  const walletBefore = await bal(account.address)
  const vaultBefore = await bal(VAULT)
  const tpBefore = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })

  console.log('Before refund:')
  console.log('  Wallet USDC:', formatUnits(walletBefore, 6))
  console.log('  Vault USDC:', formatUnits(vaultBefore, 6))
  console.log('  totalPrincipal:', formatUnits(tpBefore, 6))

  // Call refund(address, uint256) - selector 0x410085df
  console.log('\n--- Executing Refund ---')

  const calldata = encodeAbiParameters(
    parseAbiParameters('address, uint256'),
    [account.address, amountAtomic],
  )
  const fullCalldata = ('0x410085df' + calldata.slice(2)) as Hex

  // Simulate first
  console.log('Simulating...')
  try {
    await publicClient.call({
      to: ESCROW,
      data: fullCalldata,
      account: account.address,
    })
    console.log('Simulation: SUCCESS')
  } catch (e: any) {
    console.log('Simulation error:', e.shortMessage || e.message?.substring(0, 300))
    // Try anyway - might work
  }

  // Execute
  console.log('Executing...')
  try {
    const txHash = await walletClient.sendTransaction({
      to: ESCROW,
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
  } catch (e: any) {
    console.log('TX error:', e.shortMessage || e.message?.substring(0, 400))
    return
  }

  // State after
  console.log('\n--- After Refund ---')
  const walletAfter = await bal(account.address)
  const vaultAfter = await bal(VAULT)
  const tpAfter = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })

  console.log('  Wallet USDC:', formatUnits(walletAfter, 6), `(was ${formatUnits(walletBefore, 6)})`)
  console.log('  Vault USDC:', formatUnits(vaultAfter, 6), `(was ${formatUnits(vaultBefore, 6)})`)
  console.log('  totalPrincipal:', formatUnits(tpAfter, 6), `(was ${formatUnits(tpBefore, 6)})`)

  const diff = walletAfter - walletBefore
  console.log('  USDC recovered:', formatUnits(diff, 6))

  // Check deposits remaining
  const raw = await publicClient.call({
    to: ESCROW,
    data: ('0x2a5bf6d2000000000000000000000000' + account.address.slice(2).toLowerCase()) as `0x${string}`,
  })
  if (raw.data) {
    const hex = raw.data.slice(2)
    const offset1 = parseInt(hex.slice(0, 64), 16) * 2
    const len1 = parseInt(hex.slice(offset1, offset1 + 64), 16)
    console.log('  Deposits remaining:', len1)
  }

  const ethAfter = await publicClient.getBalance({ address: account.address })
  console.log('\n  ETH remaining:', formatUnits(ethAfter, 18))
}

main().catch(console.error)

/**
 * Deploy the relay proxy for our wallet on Base Mainnet.
 * Prerequisite: registerMerchant already called.
 * Usage: npx tsx deploy-relay.ts
 */
import { createPublicClient, createWalletClient, http, parseAbi, formatUnits } from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const account = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY as `0x${string}`)
const publicClient = createPublicClient({ chain: base, transport: http('https://mainnet.base.org') })
const walletClient = createWalletClient({ account, chain: base, transport: http('https://mainnet.base.org') })

const FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as const
const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const
const VAULT = '0x0b3fC8BA8952C6cA6807F667894b0b7c9C40FC8b' as const
const RELAY = '0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3' as const

async function getBalance(address: `0x${string}`) {
  return publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [address],
  })
}

async function main() {
  console.log('=== Deploy Relay ===')
  console.log('Wallet:', account.address)

  // State before
  const relayBefore = await getBalance(RELAY)
  const escrowBefore = await getBalance(ESCROW)
  const vaultBefore = await getBalance(VAULT)
  console.log('\nBefore:')
  console.log('  Relay USDC:', formatUnits(relayBefore, 6))
  console.log('  Escrow USDC:', formatUnits(escrowBefore, 6))
  console.log('  Vault USDC:', formatUnits(vaultBefore, 6))

  const tpBefore = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })
  console.log('  totalPrincipal:', formatUnits(tpBefore, 6))

  // Deploy relay
  console.log('\nDeploying relay...')
  const deployHash = await walletClient.writeContract({
    address: FACTORY,
    abi: parseAbi(['function deployRelay(address) returns (address)']),
    functionName: 'deployRelay',
    args: [account.address],
  })
  console.log('TX:', deployHash)
  console.log('BaseScan: https://basescan.org/tx/' + deployHash)

  const receipt = await publicClient.waitForTransactionReceipt({ hash: deployHash })
  console.log('Status:', receipt.status)
  console.log('Gas used:', receipt.gasUsed.toString())

  for (const log of receipt.logs) {
    console.log('\nLog from:', log.address)
    console.log('  Topics:', log.topics)
    console.log('  Data:', log.data?.substring(0, 200))
  }

  // State after
  const relayAfter = await getBalance(RELAY)
  const escrowAfter = await getBalance(ESCROW)
  const vaultAfter = await getBalance(VAULT)
  console.log('\nAfter:')
  console.log('  Relay USDC:', formatUnits(relayAfter, 6))
  console.log('  Escrow USDC:', formatUnits(escrowAfter, 6))
  console.log('  Vault USDC:', formatUnits(vaultAfter, 6))

  const tpAfter = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })
  console.log('  totalPrincipal:', formatUnits(tpAfter, 6))

  // Check if relay has code now
  const relayCode = await publicClient.getCode({ address: RELAY })
  console.log('  Relay has code:', relayCode ? relayCode.length > 2 : false)

  // Check deposits
  try {
    const rawResult = await publicClient.call({
      to: ESCROW,
      data: ('0x2a5bf6d2000000000000000000000000' + account.address.slice(2).toLowerCase()) as `0x${string}`,
    })
    console.log('  getUserDeposits:', rawResult.data?.substring(0, 300))
  } catch (e: any) {
    console.log('  getUserDeposits error')
  }

  // Final ETH balance
  const ethAfter = await publicClient.getBalance({ address: account.address })
  console.log('\nETH remaining:', formatUnits(ethAfter, 18), 'ETH')
}

main().catch(console.error)

/**
 * Probe the x402r escrow contracts to understand the deposit mechanism.
 * Usage: npx tsx probe-escrow.ts
 */
import { createPublicClient, http, parseAbi, formatUnits } from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const pk = process.env.WALLET_PRIVATE_KEY as `0x${string}`
const account = privateKeyToAccount(pk)

const client = createPublicClient({
  chain: base,
  transport: http('https://mainnet.base.org'),
})

const FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as const
const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const

async function main() {
  console.log('=== x402r Escrow Probe ===')
  console.log('Wallet:', account.address)

  // 1. Check relay status
  const relayAddr = await client.readContract({
    address: FACTORY,
    abi: parseAbi(['function getRelayAddress(address) view returns (address)']),
    functionName: 'getRelayAddress',
    args: [account.address],
  })
  console.log('\nRelay address:', relayAddr)

  const relayCode = await client.getCode({ address: relayAddr })
  const relayDeployed = relayCode != null && relayCode.length > 2
  console.log('Relay deployed:', relayDeployed)

  // 2. USDC balances
  const relayBalance = await client.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [relayAddr],
  })
  console.log('Relay USDC:', formatUnits(relayBalance, 6))

  const walletBalance = await client.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [account.address],
  })
  console.log('Wallet USDC:', formatUnits(walletBalance, 6))

  // 3. Escrow state
  const totalPrincipal = await client.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })
  console.log('\nEscrow totalPrincipal:', formatUnits(totalPrincipal, 6), 'USDC')

  // 4. getArbiter for our wallet
  try {
    const arbiter = await client.readContract({
      address: ESCROW,
      abi: parseAbi(['function getArbiter(address) view returns (address)']),
      functionName: 'getArbiter',
      args: [account.address],
    })
    console.log('getArbiter(wallet):', arbiter)
  } catch (e: any) {
    console.log('getArbiter error:', e.shortMessage || e.message?.substring(0, 100))
  }

  // 5. getUserDeposits
  try {
    const rawResult = await client.call({
      to: ESCROW,
      data: ('0x2a5bf6d2000000000000000000000000' + account.address.slice(2).toLowerCase()) as `0x${string}`,
    })
    console.log('getUserDeposits raw:', rawResult.data?.substring(0, 200))
  } catch (e: any) {
    console.log('getUserDeposits error:', e.shortMessage?.substring(0, 100))
  }

  // 6. Simulate deployRelay
  console.log('\n=== deployRelay Simulation ===')
  try {
    const { result } = await client.simulateContract({
      address: FACTORY,
      abi: parseAbi(['function deployRelay(address) returns (address)']),
      functionName: 'deployRelay',
      args: [account.address],
      account: account.address,
    })
    console.log('deployRelay would succeed, returns:', result)
  } catch (e: any) {
    console.log('deployRelay simulation error:', e.shortMessage || e.message?.substring(0, 300))
  }

  // 7. Check if registerMerchant is needed
  console.log('\n=== registerMerchant check ===')
  try {
    await client.simulateContract({
      address: ESCROW,
      abi: parseAbi(['function registerMerchant(address)']),
      functionName: 'registerMerchant',
      args: [account.address],
      account: account.address,
    })
    console.log('registerMerchant(wallet) would succeed')
  } catch (e: any) {
    console.log('registerMerchant simulation:', e.shortMessage || e.message?.substring(0, 200))
  }

  // 8. Check Factory IMPLEMENTATION
  try {
    const impl = await client.readContract({
      address: FACTORY,
      abi: parseAbi(['function IMPLEMENTATION() view returns (address)']),
      functionName: 'IMPLEMENTATION',
    })
    console.log('\nFactory IMPLEMENTATION:', impl)

    // Check implementation contract bytecode and probe its functions
    const implCode = await client.getCode({ address: impl })
    console.log('Implementation bytecode length:', implCode?.length)
  } catch (e: any) {
    console.log('IMPLEMENTATION error:', e.shortMessage?.substring(0, 100))
  }

  // 9. Factory ESCROW
  try {
    const esc = await client.readContract({
      address: FACTORY,
      abi: parseAbi(['function ESCROW() view returns (address)']),
      functionName: 'ESCROW',
    })
    console.log('Factory ESCROW:', esc)
  } catch (e: any) {
    console.log('ESCROW error:', e.shortMessage?.substring(0, 100))
  }
}

main().catch(console.error)

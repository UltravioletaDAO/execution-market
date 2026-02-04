/**
 * Register as merchant and deploy relay on x402r escrow.
 * This creates the on-chain infrastructure for Execution Market to receive payments.
 *
 * Flow:
 * 1. registerMerchant(wallet) on Escrow - register as merchant
 * 2. deployRelay(wallet) on Factory - deploy relay proxy to sweep USDC into escrow
 *
 * Usage: npx tsx register-and-deploy.ts
 */
import { createPublicClient, createWalletClient, http, parseAbi, formatUnits } from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const pk = process.env.WALLET_PRIVATE_KEY as `0x${string}`
const account = privateKeyToAccount(pk)

const publicClient = createPublicClient({
  chain: base,
  transport: http('https://mainnet.base.org'),
})

const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http('https://mainnet.base.org'),
})

const FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as const
const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const

async function main() {
  console.log('=== x402r Registration & Relay Deployment ===')
  console.log('Wallet:', account.address)
  console.log('Network: Base Mainnet (Chain ID 8453)')
  console.log('')

  // Check balances
  const ethBalance = await publicClient.getBalance({ address: account.address })
  const usdcBalance = await publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [account.address],
  })
  console.log('ETH balance:', formatUnits(ethBalance, 18), 'ETH')
  console.log('USDC balance:', formatUnits(usdcBalance, 6), 'USDC')

  // Check relay state before
  const relayAddr = await publicClient.readContract({
    address: FACTORY,
    abi: parseAbi(['function getRelayAddress(address) view returns (address)']),
    functionName: 'getRelayAddress',
    args: [account.address],
  })
  const relayUSDC = await publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [relayAddr],
  })
  console.log('\nRelay address:', relayAddr)
  console.log('Relay USDC (before):', formatUnits(relayUSDC, 6))

  // Step 1: Register as merchant
  console.log('\n--- Step 1: Register as Merchant ---')
  try {
    const regHash = await walletClient.writeContract({
      address: ESCROW,
      abi: parseAbi(['function registerMerchant(address)']),
      functionName: 'registerMerchant',
      args: [account.address],
    })
    console.log('registerMerchant TX:', regHash)
    console.log('BaseScan: https://basescan.org/tx/' + regHash)

    const regReceipt = await publicClient.waitForTransactionReceipt({ hash: regHash })
    console.log('Status:', regReceipt.status)
    console.log('Gas used:', regReceipt.gasUsed.toString())
  } catch (e: any) {
    if (e.shortMessage?.includes('already registered') || e.message?.includes('already')) {
      console.log('Already registered as merchant (OK)')
    } else {
      console.log('registerMerchant error:', e.shortMessage || e.message?.substring(0, 200))
      // Continue anyway - might already be registered
    }
  }

  // Step 2: Deploy relay
  console.log('\n--- Step 2: Deploy Relay ---')
  try {
    const deployHash = await walletClient.writeContract({
      address: FACTORY,
      abi: parseAbi(['function deployRelay(address) returns (address)']),
      functionName: 'deployRelay',
      args: [account.address],
    })
    console.log('deployRelay TX:', deployHash)
    console.log('BaseScan: https://basescan.org/tx/' + deployHash)

    const deployReceipt = await publicClient.waitForTransactionReceipt({ hash: deployHash })
    console.log('Status:', deployReceipt.status)
    console.log('Gas used:', deployReceipt.gasUsed.toString())
    console.log('Logs:', deployReceipt.logs.length)
    for (const log of deployReceipt.logs) {
      console.log('  Log from:', log.address)
      console.log('  Topics:', log.topics)
      console.log('  Data:', log.data?.substring(0, 130))
    }
  } catch (e: any) {
    console.log('deployRelay error:', e.shortMessage || e.message?.substring(0, 200))
  }

  // Step 3: Check state after
  console.log('\n--- Post-Deployment State ---')

  const relayCodeAfter = await publicClient.getCode({ address: relayAddr })
  console.log('Relay deployed:', relayCodeAfter != null && relayCodeAfter.length > 2)

  const relayUSDCAfter = await publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [relayAddr],
  })
  console.log('Relay USDC (after):', formatUnits(relayUSDCAfter, 6))

  const escrowUSDC = await publicClient.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [ESCROW],
  })
  console.log('Escrow contract USDC:', formatUnits(escrowUSDC, 6))

  const totalPrincipal = await publicClient.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })
  console.log('Escrow totalPrincipal:', formatUnits(totalPrincipal, 6), 'USDC')

  // Check deposits
  try {
    const rawResult = await publicClient.call({
      to: ESCROW,
      data: ('0x2a5bf6d2000000000000000000000000' + account.address.slice(2).toLowerCase()) as `0x${string}`,
    })
    console.log('getUserDeposits raw:', rawResult.data?.substring(0, 300))
  } catch (e: any) {
    console.log('getUserDeposits error:', e.shortMessage?.substring(0, 100))
  }

  // Check getArbiter
  try {
    const arbiter = await publicClient.readContract({
      address: ESCROW,
      abi: parseAbi(['function getArbiter(address) view returns (address)']),
      functionName: 'getArbiter',
      args: [account.address],
    })
    console.log('getArbiter(wallet):', arbiter)
  } catch (e: any) {
    console.log('getArbiter error:', e.shortMessage?.substring(0, 100))
  }

  // Final wallet balance
  const ethAfter = await publicClient.getBalance({ address: account.address })
  console.log('\nETH balance after:', formatUnits(ethAfter, 18), 'ETH')
  console.log('ETH spent:', formatUnits(ethBalance - ethAfter, 18), 'ETH')
}

main().catch(console.error)

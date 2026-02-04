/**
 * Debug escrow permissions to understand who can call refund/release.
 */
import { createPublicClient, http, parseAbi, encodeAbiParameters, parseAbiParameters, type Hex } from 'viem'
import { base } from 'viem/chains'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const rpcUrl = process.env.BASE_MAINNET_RPC_URL!
const client = createPublicClient({ chain: base, transport: http(rpcUrl) })

const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const WALLET = '0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd' as const
const RELAY = '0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3' as const
const FACTORY = '0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814' as const

async function callView(sel: string, arg?: `0x${string}`) {
  const data = arg
    ? (sel + encodeAbiParameters(parseAbiParameters('address'), [arg]).slice(2)) as Hex
    : sel as Hex
  try {
    const r = await client.call({ to: ESCROW, data })
    return r.data
  } catch {
    return null
  }
}

async function main() {
  console.log('=== Debug Escrow Permissions ===')

  // Check various addresses with the unknown selectors
  const addresses = {
    wallet: WALLET,
    relay: RELAY,
    factory: FACTORY,
  }

  // 0xa9246e82 - unknown function (returned wallet for wallet arg)
  console.log('\n--- 0xa9246e82 (unknown view) ---')
  for (const [name, addr] of Object.entries(addresses)) {
    const r = await callView('0xa9246e82', addr as `0x${string}`)
    console.log(`  ${name}: ${r?.substring(0, 66)}`)
  }

  // 0xf101b9cc - unknown (returned 1 for wallet)
  console.log('\n--- 0xf101b9cc (unknown view - isMerchant?) ---')
  for (const [name, addr] of Object.entries(addresses)) {
    const r = await callView('0xf101b9cc', addr as `0x${string}`)
    const val = r ? parseInt(r.slice(2), 16) : 0
    console.log(`  ${name}: ${val}`)
  }

  // getArbiter
  console.log('\n--- getArbiter ---')
  for (const [name, addr] of Object.entries(addresses)) {
    const r = await client.readContract({
      address: ESCROW,
      abi: parseAbi(['function getArbiter(address) view returns (address)']),
      functionName: 'getArbiter',
      args: [addr as `0x${string}`],
    })
    console.log(`  ${name}: ${r}`)
  }

  // getUserDeposits for relay (maybe deposits are tracked under relay, not wallet)
  console.log('\n--- getUserDeposits ---')
  for (const [name, addr] of Object.entries(addresses)) {
    const raw = await client.call({
      to: ESCROW,
      data: ('0x2a5bf6d2000000000000000000000000' + (addr as string).slice(2).toLowerCase()) as Hex,
    })
    if (raw.data) {
      const hex = raw.data.slice(2)
      const offset1 = parseInt(hex.slice(0, 64), 16) * 2
      const len1 = parseInt(hex.slice(offset1, offset1 + 64), 16)
      console.log(`  ${name}: ${len1} deposits`)
      if (len1 > 0) {
        const offset2 = parseInt(hex.slice(64, 128), 16) * 2
        for (let i = 0; i < len1; i++) {
          const amtStart = offset2 + 64 + i * 64
          const amount = BigInt('0x' + hex.slice(amtStart, amtStart + 64))
          console.log(`    amount: ${Number(amount) / 1e6} USDC`)
        }
      }
    }
  }

  // Try release/refund from wallet to wallet on WALLET deposits
  console.log('\n--- Permission tests ---')

  // release(wallet, 10000) from wallet
  const cd = encodeAbiParameters(parseAbiParameters('address, uint256'), [WALLET, 10000n])
  try {
    await client.call({ to: ESCROW, data: ('0x0357371d' + cd.slice(2)) as Hex, account: WALLET })
    console.log('release(wallet, 10000) from wallet: SUCCESS')
  } catch (e: any) {
    console.log('release(wallet, 10000) from wallet:', e.shortMessage?.substring(0, 100))
  }

  // release(wallet, 10000) from relay
  try {
    await client.call({ to: ESCROW, data: ('0x0357371d' + cd.slice(2)) as Hex, account: RELAY })
    console.log('release(wallet, 10000) from relay: SUCCESS')
  } catch (e: any) {
    console.log('release(wallet, 10000) from relay:', e.shortMessage?.substring(0, 100))
  }

  // refund with different combos
  const cdRelay = encodeAbiParameters(parseAbiParameters('address, uint256'), [RELAY, 10000n])

  try {
    await client.call({ to: ESCROW, data: ('0x410085df' + cd.slice(2)) as Hex, account: RELAY })
    console.log('refund(wallet, 10000) from relay: SUCCESS')
  } catch (e: any) {
    console.log('refund(wallet, 10000) from relay:', e.shortMessage?.substring(0, 100))
  }

  try {
    await client.call({ to: ESCROW, data: ('0x410085df' + cdRelay.slice(2)) as Hex, account: WALLET })
    console.log('refund(relay, 10000) from wallet: SUCCESS')
  } catch (e: any) {
    console.log('refund(relay, 10000) from wallet:', e.shortMessage?.substring(0, 100))
  }

  // Check if there's a setArbiter function in the unknowns
  // 0x391f1c31 shared between escrow and relay impl
  console.log('\n--- 0x391f1c31 (shared escrow+relay) ---')
  // Try with (address, address) - could be setArbiter(merchant, arbiter)
  const cdSetArbiter = encodeAbiParameters(parseAbiParameters('address, address'), [RELAY, WALLET])
  try {
    await client.call({ to: ESCROW, data: ('0x391f1c31' + cdSetArbiter.slice(2)) as Hex, account: WALLET })
    console.log('0x391f1c31(relay, wallet) from wallet: SUCCESS')
  } catch (e: any) {
    console.log('0x391f1c31(relay, wallet):', e.shortMessage?.substring(0, 150))
  }

  // Try with just address arg
  try {
    const cdAddr = encodeAbiParameters(parseAbiParameters('address'), [WALLET])
    await client.call({ to: ESCROW, data: ('0x391f1c31' + cdAddr.slice(2)) as Hex, account: WALLET })
    console.log('0x391f1c31(wallet) from wallet: SUCCESS')
  } catch (e: any) {
    console.log('0x391f1c31(wallet):', e.shortMessage?.substring(0, 150))
  }
}

main().catch(console.error)

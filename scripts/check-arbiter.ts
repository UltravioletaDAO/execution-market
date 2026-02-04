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
const WALLET = 'YOUR_DEV_WALLET' as const
const RELAY = '0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3' as const

async function main() {
  // Check arbiters
  const arbiterWallet = await client.readContract({
    address: ESCROW,
    abi: parseAbi(['function getArbiter(address) view returns (address)']),
    functionName: 'getArbiter',
    args: [WALLET],
  })
  console.log('getArbiter(wallet):', arbiterWallet)

  const arbiterRelay = await client.readContract({
    address: ESCROW,
    abi: parseAbi(['function getArbiter(address) view returns (address)']),
    functionName: 'getArbiter',
    args: [RELAY],
  })
  console.log('getArbiter(relay):', arbiterRelay)

  // Try refund with relay as first arg
  console.log('\nSimulating refund(relay, 10000)...')
  const cd1 = encodeAbiParameters(parseAbiParameters('address, uint256'), [RELAY, 10000n])
  try {
    await client.call({ to: ESCROW, data: ('0x410085df' + cd1.slice(2)) as Hex, account: WALLET })
    console.log('  SUCCESS')
  } catch (e: any) {
    console.log('  Error:', e.shortMessage?.substring(0, 150))
  }

  // Try release(wallet, 10000) - release to self
  console.log('\nSimulating release(wallet, 10000)...')
  const cd2 = encodeAbiParameters(parseAbiParameters('address, uint256'), [WALLET, 10000n])
  try {
    await client.call({ to: ESCROW, data: ('0x0357371d' + cd2.slice(2)) as Hex, account: WALLET })
    console.log('  SUCCESS')
  } catch (e: any) {
    console.log('  Error:', e.shortMessage?.substring(0, 150))
  }

  // Try release(relay, 10000) - from wallet, release to relay
  console.log('\nSimulating release(relay, 10000) from wallet...')
  try {
    await client.call({ to: ESCROW, data: ('0x0357371d' + cd1.slice(2)) as Hex, account: WALLET })
    console.log('  SUCCESS')
  } catch (e: any) {
    console.log('  Error:', e.shortMessage?.substring(0, 150))
  }

  // Maybe the function is refund(address payer, uint256 amount) where payer is the payer from the deposit
  // The payer in our deposit was our wallet (EIP-3009 from=wallet)
  console.log('\nSimulating refund(wallet, 10000) from relay (as msg.sender)...')
  try {
    await client.call({ to: ESCROW, data: ('0x410085df' + cd2.slice(2)) as Hex, account: RELAY })
    console.log('  SUCCESS')
  } catch (e: any) {
    console.log('  Error:', e.shortMessage?.substring(0, 150))
  }

  // Check remaining unknown selectors on escrow - maybe there's a different refund
  // 0x391f1c31 and 0xa9246e82 are still unknown
  // Let's try calling them
  console.log('\nProbing unknown escrow selectors:')
  for (const sel of ['0x391f1c31', '0xa9246e82', '0xf101b9cc', '0xf3010014', '0x048387d4', '0x2d182be5']) {
    try {
      // Try with wallet arg
      const cd = encodeAbiParameters(parseAbiParameters('address'), [WALLET])
      const r = await client.call({ to: ESCROW, data: (sel + cd.slice(2)) as Hex, account: WALLET })
      console.log(`  ${sel}(wallet):`, r.data?.substring(0, 130))
    } catch {
      // Try with no args
      try {
        const r = await client.call({ to: ESCROW, data: sel as Hex, account: WALLET })
        console.log(`  ${sel}():`, r.data?.substring(0, 130))
      } catch {
        console.log(`  ${sel}: reverts`)
      }
    }
  }
}

main().catch(console.error)

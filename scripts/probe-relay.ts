/**
 * Probe the deployed relay to find sweep/deposit functions.
 * Usage: npx tsx probe-relay.ts
 */
import { createPublicClient, createWalletClient, http, parseAbi, formatUnits, keccak256, toHex } from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const account = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY as `0x${string}`)
const publicClient = createPublicClient({ chain: base, transport: http('https://mainnet.base.org') })

const RELAY = '0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3' as const
const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const

async function main() {
  console.log('=== Probe Deployed Relay ===')
  console.log('Relay:', RELAY)

  // Get relay bytecode
  const code = await publicClient.getCode({ address: RELAY })
  console.log('Bytecode length:', code?.length)

  // The relay implementation selectors (from earlier analysis):
  // 0x1f36ab90, 0x3c406e73, 0x71f70b07, 0x1d995c9d, 0x2b210169, 0x818c0152, 0x391f1c31
  // Plus known: 0xa9059cbb (transfer), 0x70a08231 (balanceOf)
  const unknownSelectors = [
    '0x1f36ab90', '0x3c406e73', '0x71f70b07', '0x1d995c9d',
    '0x2b210169', '0x818c0152', '0x391f1c31',
  ]

  // Try calling each as a view function (no args)
  console.log('\nProbing selectors with no args:')
  for (const sel of unknownSelectors) {
    try {
      const r = await publicClient.call({ to: RELAY, data: sel as `0x${string}` })
      console.log(' ', sel, '-> returned:', r.data?.substring(0, 130))
    } catch (e: any) {
      const msg = e.shortMessage || e.message || ''
      if (msg.includes('revert')) {
        console.log(' ', sel, '-> reverted (needs args)')
      } else {
        console.log(' ', sel, '-> error:', msg.substring(0, 80))
      }
    }
  }

  // Try more candidate function signatures specific to relay/sweep
  console.log('\nGenerating and matching more candidates:')
  const candidates = [
    // Sweep / forward functions
    'sweep()', 'sweep(address)', 'sweep(address,address)',
    'forward()', 'forward(address)', 'forwardAll()',
    'execute()', 'executeDeposit()', 'flush()', 'drain()',
    'sendToEscrow()', 'depositToEscrow()',
    // Auth/config
    'MERCHANT()', 'merchant()', 'ESCROW()', 'escrow()',
    'FACTORY()', 'factory()', 'TOKEN()', 'token()',
    'merchantPayout()', 'payoutAddress()',
    // ERC-20 relay
    'onTokenTransfer(address,uint256,bytes)',
    'tokensReceived(address,address,address,uint256,bytes,bytes)',
    // Deposit
    'deposit()', 'deposit(uint256)', 'deposit(address,uint256)',
    'depositFor(address)', 'createDeposit()',
    // View
    'balance()', 'getBalance()', 'pendingDeposit()',
    'initialized()', 'version()', 'VERSION()',
    'owner()', 'OWNER()', 'admin()',
    // Relay-specific
    'relay()', 'relay(address,uint256)',
    'process()', 'processDeposit()',
    'claim()', 'claimAndDeposit()',
    'settleDeposit()', 'finalizeDeposit()',
    'transferToEscrow()', 'moveToEscrow()',
    'withdraw()', 'withdrawAll()',
    'sweepToken(address)', 'sweepTokens()',
    'recoverToken(address)', 'recover(address)',
  ]

  const matched: Record<string, string> = {}
  for (const sig of candidates) {
    const sel = keccak256(toHex(sig)).slice(0, 10)
    if (unknownSelectors.includes(sel)) {
      matched[sel] = sig
      console.log('  MATCH:', sel, '->', sig)
    }
  }

  // For unmatched, try calling with wallet address as arg
  console.log('\nTrying unmatched selectors with wallet address arg:')
  const walletPadded = '000000000000000000000000' + account.address.slice(2).toLowerCase()
  for (const sel of unknownSelectors) {
    if (matched[sel]) continue
    try {
      const r = await publicClient.call({
        to: RELAY,
        data: (sel + walletPadded) as `0x${string}`,
      })
      console.log(' ', sel, '+ address -> returned:', r.data?.substring(0, 130))
    } catch {
      // Try with uint256 arg (like amount)
      try {
        const r = await publicClient.call({
          to: RELAY,
          data: (sel + '0000000000000000000000000000000000000000000000000000000000002710') as `0x${string}`,
        })
        console.log(' ', sel, '+ uint256 -> returned:', r.data?.substring(0, 130))
      } catch {
        console.log(' ', sel, '-> failed with both arg types')
      }
    }
  }

  // Also try simulating the selectors as write functions from our wallet
  console.log('\nSimulating write calls:')
  for (const sel of unknownSelectors) {
    if (matched[sel]) continue
    try {
      const r = await publicClient.call({
        to: RELAY,
        data: sel as `0x${string}`,
        account: account.address,
      })
      console.log(' ', sel, '(as write) -> returned:', r.data?.substring(0, 130))
    } catch (e: any) {
      const msg = e.shortMessage || ''
      console.log(' ', sel, '(as write) ->', msg.substring(0, 80))
    }
  }
}

main().catch(console.error)

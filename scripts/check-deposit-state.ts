import { createPublicClient, http, parseAbi, formatUnits } from 'viem'
import { base } from 'viem/chains'
import { privateKeyToAccount } from 'viem/accounts'
import * as dotenv from 'dotenv'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
dotenv.config({ path: resolve(__dirname, '../.env.local') })

const account = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY as `0x${string}`)
const rpcUrl = process.env.BASE_MAINNET_RPC_URL || 'https://mainnet.base.org'
const client = createPublicClient({ chain: base, transport: http(rpcUrl) })

const RELAY = '0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3' as const
const ESCROW = '0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC' as const
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const
const VAULT = '0x0b3fC8BA8952C6cA6807F667894b0b7c9C40FC8b' as const

type CliOptions = {
  minUsdc: number
  minEth: number
  strict: boolean
}

function parseCliArgs(): CliOptions {
  const args = process.argv.slice(2)
  const options: CliOptions = {
    minUsdc: 0.05,
    minEth: 0.0002,
    strict: false,
  }

  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    const next = args[i + 1]

    if (arg === '--strict') {
      options.strict = true
      continue
    }

    if (arg === '--min-usdc' && next) {
      const parsed = Number(next)
      if (!Number.isNaN(parsed) && parsed >= 0) {
        options.minUsdc = parsed
      }
      i++
      continue
    }

    if (arg === '--min-eth' && next) {
      const parsed = Number(next)
      if (!Number.isNaN(parsed) && parsed >= 0) {
        options.minEth = parsed
      }
      i++
    }
  }

  return options
}

async function bal(addr: `0x${string}`) {
  return client.readContract({
    address: USDC,
    abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf',
    args: [addr],
  })
}

async function main() {
  const opts = parseCliArgs()

  console.log('=== Post-Deposit State ===')
  console.log('Wallet:', account.address)

  const [walletBal, relayBal, escrowBal, vaultBal] = await Promise.all([
    bal(account.address), bal(RELAY), bal(ESCROW), bal(VAULT),
  ])

  console.log('\nUSDC Balances:')
  console.log('  Wallet:', formatUnits(walletBal, 6))
  console.log('  Relay:', formatUnits(relayBal, 6))
  console.log('  Escrow:', formatUnits(escrowBal, 6))
  console.log('  Vault:', formatUnits(vaultBal, 6))

  const tp = await client.readContract({
    address: ESCROW,
    abi: parseAbi(['function totalPrincipal() view returns (uint256)']),
    functionName: 'totalPrincipal',
  })
  console.log('  totalPrincipal:', formatUnits(tp, 6), 'USDC')

  // getUserDeposits
  const raw = await client.call({
    to: ESCROW,
    data: ('0x2a5bf6d2000000000000000000000000' + account.address.slice(2).toLowerCase()) as `0x${string}`,
  })

  if (raw.data) {
    const hex = raw.data.slice(2)
    const offset1 = parseInt(hex.slice(0, 64), 16) * 2
    const offset2 = parseInt(hex.slice(64, 128), 16) * 2
    const len1 = parseInt(hex.slice(offset1, offset1 + 64), 16)

    console.log('\nDeposits for our wallet:', len1)

    if (len1 > 0) {
      // Deposit IDs
      for (let i = 0; i < len1; i++) {
        const start = offset1 + 64 + i * 64
        const depositId = '0x' + hex.slice(start, start + 64)
        console.log(`  Deposit ${i + 1} ID: ${depositId}`)
      }
      // Amounts
      const len2 = parseInt(hex.slice(offset2, offset2 + 64), 16)
      for (let i = 0; i < len2; i++) {
        const start = offset2 + 64 + i * 64
        const amount = BigInt('0x' + hex.slice(start, start + 64))
        console.log(`  Deposit ${i + 1} Amount: ${formatUnits(amount, 6)} USDC`)
      }
    }
  }

  const eth = await client.getBalance({ address: account.address })
  const walletUsdc = Number(formatUnits(walletBal, 6))
  const walletEth = Number(formatUnits(eth, 18))

  console.log('\nETH remaining:', formatUnits(eth, 18))
  console.log('\nThreshold checks:')
  console.log(`  min USDC required: ${opts.minUsdc}`)
  console.log(`  min ETH required: ${opts.minEth}`)
  console.log(`  strict mode: ${opts.strict ? 'ON' : 'OFF'}`)

  const usdcOk = walletUsdc >= opts.minUsdc
  const ethOk = walletEth >= opts.minEth

  console.log(`  USDC check: ${usdcOk ? 'PASS' : 'FAIL'} (${walletUsdc} >= ${opts.minUsdc})`)
  console.log(`  ETH check: ${ethOk ? 'PASS' : 'FAIL'} (${walletEth} >= ${opts.minEth})`)

  if (opts.strict && (!usdcOk || !ethOk)) {
    console.error('\nInsufficient funds for strict live validation.')
    process.exitCode = 1
  }
}

main().catch(console.error)

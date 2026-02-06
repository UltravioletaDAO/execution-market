/**
 * Smoke Test — Execution Market
 *
 * Validates production APIs are live and responding correctly.
 * Designed to run nightly or as a quick health check.
 *
 * Usage:
 *   npx tsx smoke-test.ts           # Dry run (no wallet needed)
 *   npx tsx smoke-test.ts --live    # Full flow with real x402 payment
 *
 * Exit codes:
 *   0 = all checks pass
 *   1 = one or more checks failed
 */

import 'dotenv/config'

const API_BASE = process.env.EM_API_URL || 'https://api.execution.market'
const DASHBOARD_URL = process.env.EM_DASHBOARD_URL || 'https://execution.market'
const MCP_URL = process.env.EM_MCP_URL || 'https://mcp.execution.market'
const isLive = process.argv.includes('--live')

interface CheckResult {
  name: string
  pass: boolean
  ms: number
  detail?: string
}

const results: CheckResult[] = []

async function check(name: string, fn: () => Promise<string | void>): Promise<void> {
  const t0 = performance.now()
  try {
    const detail = await fn()
    const ms = performance.now() - t0
    results.push({ name, pass: true, ms, detail: detail || undefined })
    console.log(`  ✅ ${name} (${ms.toFixed(0)}ms)${detail ? ` — ${detail}` : ''}`)
  } catch (err: unknown) {
    const ms = performance.now() - t0
    const msg = err instanceof Error ? err.message : String(err)
    results.push({ name, pass: false, ms, detail: msg })
    console.log(`  ❌ ${name} (${ms.toFixed(0)}ms) — ${msg}`)
  }
}

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(message)
}

// ── Health Checks ──────────────────────────────────────────────────

console.log('\n🔍 Smoke Test — Execution Market')
console.log(`   API: ${API_BASE}`)
console.log(`   Dashboard: ${DASHBOARD_URL}`)
console.log(`   MCP: ${MCP_URL}`)
console.log(`   Mode: ${isLive ? 'LIVE (with payments)' : 'DRY RUN (read-only)'}`)
console.log('')

console.log('── Health ──')

await check('API /health', async () => {
  const res = await fetch(`${API_BASE}/health`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  return `status=${data.status}`
})

await check('API /health/sanity', async () => {
  const res = await fetch(`${API_BASE}/health/sanity`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  return `${data.checks_passed}/${data.checks_total} passed, ${data.warnings?.length || 0} warnings`
})

await check('API /health/version', async () => {
  const res = await fetch(`${API_BASE}/health/version`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  return `v=${data.version}, env=${data.environment}`
})

await check('MCP health', async () => {
  const res = await fetch(`${MCP_URL}/health`)
  assert(res.ok, `HTTP ${res.status}`)
})

await check('Dashboard reachable', async () => {
  const res = await fetch(DASHBOARD_URL, { redirect: 'follow' })
  assert(res.ok, `HTTP ${res.status}`)
  const html = await res.text()
  assert(html.includes('Execution Market') || html.includes('execution'), 'Missing expected content')
})

// ── Public Data ──────────────────────────────────────────────────

console.log('\n── Public Data ──')

await check('Public metrics', async () => {
  const res = await fetch(`${API_BASE}/api/v1/public/metrics`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  assert(typeof data.tasks?.total === 'number', 'Missing tasks.total')
  assert(typeof data.payments?.total_volume_usd === 'number', 'Missing payments.total_volume_usd')
  return `tasks=${data.tasks.total}, workers=${data.users?.registered_workers || 0}, vol=$${data.payments.total_volume_usd}`
})

await check('Available tasks', async () => {
  const res = await fetch(`${API_BASE}/api/v1/tasks/available`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  const tasks = Array.isArray(data) ? data : data.tasks || data.data || []
  return `${tasks.length} tasks available`
})

await check('Agent card (A2A)', async () => {
  const res = await fetch(`${MCP_URL}/.well-known/agent.json`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  assert(data.name === 'Execution Market', `Unexpected name: ${data.name}`)
  return `protocol=${data.protocolVersion}`
})

// ── Evidence Pipeline ──────────────────────────────────────────────

console.log('\n── Evidence Pipeline ──')

const evidenceApiUrl = process.env.VITE_EVIDENCE_API_URL || 'https://YOUR_API_GATEWAY_URL'

await check('Evidence presign Lambda', async () => {
  const qs = new URLSearchParams({
    taskId: 'smoke-test',
    actorId: 'smoke-test',
    filename: 'test.jpg',
    contentType: 'image/jpeg',
    evidenceType: 'photo',
    mode: 'put',
  })
  const res = await fetch(`${evidenceApiUrl}/upload-url?${qs}`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  assert(!!data.upload_url, 'Missing upload_url')
  assert(!!data.nonce, 'Missing nonce')
  return `nonce=${data.nonce.slice(0, 8)}...`
})

// ── Route Parity ──────────────────────────────────────────────────

console.log('\n── Route Parity ──')

await check('Route inventory', async () => {
  const res = await fetch(`${API_BASE}/health/routes`)
  assert(res.ok, `HTTP ${res.status}`)
  const data = await res.json()
  assert(data.total > 50, `Only ${data.total} routes registered`)
  return `${data.total} routes across ${Object.keys(data.by_group).length} groups`
})

// ── Live Flow (optional) ──────────────────────────────────────────

if (isLive) {
  console.log('\n── Live Payment Flow ──')

  const API_KEY = process.env.EM_API_KEY || 'em_starter_d10baa5d63f02a223494cf9a1bb0d645'

  await check('API key valid', async () => {
    const res = await fetch(`${API_BASE}/api/v1/tasks`, {
      headers: { 'X-API-Key': API_KEY },
    })
    assert(res.ok, `HTTP ${res.status}`)
    return 'authenticated'
  })

  // Additional live tests would go here (create task, submit, approve)
  // Skipped in smoke test to avoid spending USDC
  console.log('  ⏭️  Skipping payment flow (use test:x402:rapid for funded tests)')
}

// ── Summary ──────────────────────────────────────────────────────

console.log('\n── Summary ──')
const passed = results.filter(r => r.pass).length
const failed = results.filter(r => !r.pass).length
const totalMs = results.reduce((sum, r) => sum + r.ms, 0)

console.log(`   ${passed} passed, ${failed} failed (${totalMs.toFixed(0)}ms total)`)

if (failed > 0) {
  console.log('\n   Failed checks:')
  for (const r of results.filter(r => !r.pass)) {
    console.log(`     - ${r.name}: ${r.detail}`)
  }
  process.exit(1)
}

console.log('\n   🎉 All smoke tests passed!\n')

/**
 * report-sanity-warnings.ts
 *
 * Fetches /health/sanity and prints a focused report for launch tracking.
 *
 * Usage:
 *   npm exec -- tsx report-sanity-warnings.ts
 *   npm exec -- tsx report-sanity-warnings.ts --json
 *   npm exec -- tsx report-sanity-warnings.ts --fail-on-warning
 */

import 'dotenv/config'

type SanityWarning = {
  check: string
  message: string
  task_ids?: string[]
}

type SanityResponse = {
  status: string
  checks_passed: number
  checks_total: number
  warnings?: SanityWarning[]
  summary?: {
    task_status_distribution?: Record<string, number>
    total_tasks?: number
    total_bounty_usd?: number
  }
  timestamp?: string
}

const API_BASE = (process.env.EM_API_URL || 'https://api.execution.market').replace(/\/+$/, '')
const asJson = process.argv.includes('--json')
const failOnWarning = process.argv.includes('--fail-on-warning')

function printHumanReport(data: SanityResponse): void {
  const warnings = data.warnings || []
  const completed = data.summary?.task_status_distribution?.completed ?? 0
  const total = data.summary?.total_tasks ?? 0

  console.log('Execution Market - Sanity Report')
  console.log(`API: ${API_BASE}`)
  console.log(`Status: ${data.status}`)
  console.log(`Checks: ${data.checks_passed}/${data.checks_total}`)
  console.log(`Warnings: ${warnings.length}`)
  console.log(`Tasks: total=${total}, completed=${completed}`)
  if (data.timestamp) {
    console.log(`Timestamp: ${data.timestamp}`)
  }

  if (warnings.length === 0) {
    console.log('No warnings reported.')
    return
  }

  console.log('')
  console.log('Warnings detail:')
  for (const warning of warnings) {
    const sampleTaskIds = (warning.task_ids || []).slice(0, 10)
    console.log(`- ${warning.check}: ${warning.message}`)
    if (sampleTaskIds.length > 0) {
      console.log(`  task_ids(sample=${sampleTaskIds.length}): ${sampleTaskIds.join(', ')}`)
    }
  }
}

async function run(): Promise<void> {
  const response = await fetch(`${API_BASE}/health/sanity`)
  if (!response.ok) {
    throw new Error(`Failed to fetch /health/sanity: HTTP ${response.status}`)
  }

  const data = await response.json() as SanityResponse

  if (asJson) {
    console.log(JSON.stringify(data, null, 2))
  } else {
    printHumanReport(data)
  }

  if (data.status === 'error') {
    process.exit(2)
  }

  if (failOnWarning && (data.warnings?.length || 0) > 0) {
    process.exit(3)
  }
}

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`Sanity report failed: ${message}`)
  process.exit(1)
})


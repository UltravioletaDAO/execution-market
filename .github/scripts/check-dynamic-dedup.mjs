#!/usr/bin/env node
/**
 * Fail the CI job if any of the guarded @dynamic-labs packages resolve to
 * more than one version in the dashboard's dependency tree.
 *
 * BUG CONTEXT (INC-2026-04-20): a transitive hoist resolved
 * @dynamic-labs/wallet-connector-core to 4.71.0 while @dynamic-labs/ethereum
 * was 4.77.x. At runtime this threw `registerEvmProviders is not a function`
 * and silently broke login. The only signal before rollback was a user
 * report. This check shifts detection left to CI.
 *
 * Implementation notes:
 *   - `npm ls --json` reports the full dep tree.
 *   - We walk it recursively and collect every instance of each guarded name.
 *   - If any name has >1 distinct version, we exit non-zero with a clear
 *     remediation message.
 *   - Uses `execFileSync` (no shell) with a fixed argv — no user input is
 *     passed to the shell, so there is no injection surface.
 *
 * Usage (from dashboard/ working dir):
 *   node ../.github/scripts/check-dynamic-dedup.mjs
 */

import { execFileSync } from 'node:child_process'
import process from 'node:process'

/**
 * Packages that MUST resolve to a single version across the tree.
 * Keep in sync with the overrides block in dashboard/package.json.
 */
const GUARDED_PACKAGES = [
  '@dynamic-labs/wallet-connector-core',
  '@dynamic-labs/sdk-react-core',
  '@dynamic-labs/ethereum',
  '@dynamic-labs/ethereum-core',
  '@dynamic-labs/multi-wallet',
  '@dynamic-labs/rpc-providers',
]

/** Max depth we ask npm to walk. 20 is overkill for even deep Dynamic trees. */
const DEPTH = 20

function npmLsJson() {
  // Fixed argv, no shell interpolation. `npm` is resolved from PATH by the
  // child_process utility; `execFile` does NOT spawn a shell.
  const npmArgs = ['ls', '--json', '--all', `--depth=${DEPTH}`]
  const npmBin = process.platform === 'win32' ? 'npm.cmd' : 'npm'
  try {
    const stdout = execFileSync(npmBin, npmArgs, {
      encoding: 'utf8',
      maxBuffer: 256 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    return JSON.parse(stdout)
  } catch (err) {
    // `npm ls` exits non-zero when peer deps / missing / extraneous are
    // reported, but it still prints valid JSON on stdout. Parse anyway.
    const raw = err.stdout?.toString() ?? ''
    if (!raw) {
      console.error('[dedup] `npm ls` failed with no JSON output:')
      console.error(err.message)
      process.exit(2)
    }
    try {
      return JSON.parse(raw)
    } catch (parseErr) {
      console.error('[dedup] Could not parse `npm ls` output:', parseErr.message)
      process.exit(2)
    }
  }
}

/**
 * Walk the dep tree and collect every (name, version) pair for guarded pkgs.
 * Node's npm-ls schema uses `dependencies` keyed by package name with
 * `{ version, dependencies: {...} }` values.
 */
function collectVersions(tree, guarded) {
  const found = new Map() // name -> Set<version>
  for (const name of guarded) {
    found.set(name, new Set())
  }

  const visit = (node) => {
    if (!node || typeof node !== 'object') return
    const deps = node.dependencies
    if (!deps) return
    for (const [name, child] of Object.entries(deps)) {
      if (found.has(name) && child && typeof child.version === 'string') {
        found.get(name).add(child.version)
      }
      visit(child)
    }
  }

  visit(tree)
  return found
}

function main() {
  const tree = npmLsJson()
  const versions = collectVersions(tree, GUARDED_PACKAGES)

  const violations = []
  for (const [name, vset] of versions.entries()) {
    if (vset.size > 1) {
      violations.push({ name, versions: [...vset].sort() })
    }
  }

  if (violations.length > 0) {
    console.error('\n::error::Multiple versions detected in @dynamic-labs/* install tree.')
    console.error(
      '\nThis is the exact shape of INC-2026-04-20: a transitive mismatch between\n' +
        '@dynamic-labs/wallet-connector-core and @dynamic-labs/ethereum caused\n' +
        '`registerEvmProviders is not a function` at runtime and silently broke login.\n',
    )
    for (const { name, versions } of violations) {
      console.error(
        `  - ${name}: found [${versions.join(', ')}] — expected a single pinned version`,
      )
    }
    console.error(
      '\nFix:\n' +
        '  1. Add (or update) an `overrides` entry in dashboard/package.json pinning\n' +
        '     each listed package to the same minor version as @dynamic-labs/ethereum.\n' +
        '  2. Delete node_modules + package-lock.json and re-run `npm install`.\n' +
        '  3. Verify with `npm ls @dynamic-labs/wallet-connector-core` — should\n' +
        '     print exactly one version.\n',
    )
    process.exit(1)
  }

  // Report success + the actual resolved versions so we have a paper trail
  // in CI logs for future debugging.
  console.log('[dedup] All guarded @dynamic-labs/* packages resolve to a single version:')
  for (const [name, vset] of versions.entries()) {
    const only = [...vset][0] ?? '(not installed)'
    console.log(`  - ${name}: ${only}`)
  }
}

main()

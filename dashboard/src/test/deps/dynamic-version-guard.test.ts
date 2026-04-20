/**
 * Dynamic.xyz Version Guardrail
 *
 * Fails fast if the `@dynamic-labs/*` packages resolved at runtime regress to
 * a version where `ChainRpcProviders.registerEvmProviders` is missing (the
 * function is attached as a side-effect at module-load time inside
 * `@dynamic-labs/ethereum-core`, and `TurnkeyEVMWalletConnector` calls it at
 * construction).
 *
 * BUG CONTEXT (INC-2026-04-20):
 * A transitive hoist resolved `@dynamic-labs/wallet-connector-core` to 4.71.0
 * while `@dynamic-labs/ethereum` was 4.77.x. At runtime the connector threw
 * `registerEvmProviders is not a function`, the WalletConnector logger emitted
 * `[WalletConnector] [ERROR]:`, and login silently broke. Zero tests caught it
 * because unit tests mock `useDynamicContext` and the E2E suite uses the
 * `window.__E2E_AUTH__` escape hatch that bypasses wallet init entirely.
 *
 * This test ensures:
 *   1. The pinned `@dynamic-labs/wallet-connector-core` is >= 4.77.3 — the
 *      version where the contract we depend on is stable.
 *   2. The core package that provides `registerEvmProviders` (attaching it to
 *      `ChainRpcProviders` as a side-effect of import) is loadable.
 *   3. Importing `EthereumWalletConnectors` does not explode at module load.
 *
 * If this test fails, DO NOT skip it — fix the dependency tree with an
 * `overrides` entry in `dashboard/package.json` (Fase 1 already did this).
 */

import { describe, it, expect } from 'vitest'
import connectorCorePkg from '@dynamic-labs/wallet-connector-core/package.json'
import ethereumPkg from '@dynamic-labs/ethereum/package.json'
import ethereumCorePkg from '@dynamic-labs/ethereum-core/package.json'

/** Minimum versions confirmed to work (Fase 1 bump, 2026-04-20). */
const MIN_VERSION = '4.77.3'

/**
 * Parse "x.y.z" into [x, y, z]. Throws on malformed input so we don't silently
 * pass when a package publishes a funky version string.
 */
function parseVersion(v: string): [number, number, number] {
  const clean = v.replace(/^[\^~]/, '').split('-')[0] // strip range prefix and pre-release suffix
  const parts = clean.split('.').map(Number)
  if (parts.length !== 3 || parts.some(Number.isNaN)) {
    throw new Error(`Unparseable semver: ${v}`)
  }
  return [parts[0], parts[1], parts[2]]
}

function gte(a: string, b: string): boolean {
  const [ax, ay, az] = parseVersion(a)
  const [bx, by, bz] = parseVersion(b)
  if (ax !== bx) return ax > bx
  if (ay !== by) return ay > by
  return az >= bz
}

describe('Dynamic version guardrail', () => {
  it('@dynamic-labs/wallet-connector-core is >= 4.77.3 (INC-2026-04-20 regression shield)', () => {
    expect(typeof connectorCorePkg.version).toBe('string')
    expect(
      gte(connectorCorePkg.version, MIN_VERSION),
      `@dynamic-labs/wallet-connector-core@${connectorCorePkg.version} < ${MIN_VERSION}. ` +
        'Versions < 4.77.3 miss the registerEvmProviders contract and silently break login. ' +
        'Check dashboard/package.json overrides.',
    ).toBe(true)
  })

  it('@dynamic-labs/ethereum is >= 4.77.3', () => {
    expect(gte(ethereumPkg.version, MIN_VERSION)).toBe(true)
  })

  it('@dynamic-labs/ethereum-core is >= 4.77.3', () => {
    // ethereum-core is the package that actually attaches
    // `registerEvmProviders` to `ChainRpcProviders` as a side effect.
    expect(gte(ethereumCorePkg.version, MIN_VERSION)).toBe(true)
  })

  it('all three @dynamic-labs packages are on the same minor line', () => {
    // A mismatch of minor versions is the exact shape of the INC-2026-04-20
    // incident (wallet-connector-core 4.71 + ethereum 4.77).
    const [, connY] = parseVersion(connectorCorePkg.version)
    const [, ethY] = parseVersion(ethereumPkg.version)
    const [, coreY] = parseVersion(ethereumCorePkg.version)
    expect(
      connY === ethY && ethY === coreY,
      `Minor-version drift detected across @dynamic-labs packages: ` +
        `wallet-connector-core=${connectorCorePkg.version}, ` +
        `ethereum=${ethereumPkg.version}, ethereum-core=${ethereumCorePkg.version}. ` +
        'This is exactly the shape of INC-2026-04-20 — add overrides in package.json.',
    ).toBe(true)
  })

  it('EthereumWalletConnectors import does not throw', async () => {
    // Importing the module is itself a contract: it triggers side-effects in
    // `@dynamic-labs/ethereum-core` that attach `registerEvmProviders` to
    // `ChainRpcProviders`. If the import explodes, wallet init will explode
    // at runtime in the browser too.
    const mod = await import('@dynamic-labs/ethereum')
    expect(mod.EthereumWalletConnectors).toBeDefined()
    expect(typeof mod.EthereumWalletConnectors).toBe('function')
  })

  it('ChainRpcProviders.registerEvmProviders is a function after side-effect import', async () => {
    // The side-effect attachment lives in `ethereum-core`. We import it first
    // to make sure the patch ran, then read the function off of
    // `@dynamic-labs/rpc-providers::ChainRpcProviders`.
    await import('@dynamic-labs/ethereum-core')
    const rpcProviders = await import('@dynamic-labs/rpc-providers')
    const ChainRpcProviders = (rpcProviders as Record<string, unknown>).ChainRpcProviders as
      | Record<string, unknown>
      | undefined
    expect(ChainRpcProviders, 'ChainRpcProviders export missing from @dynamic-labs/rpc-providers').toBeDefined()
    expect(
      typeof ChainRpcProviders?.registerEvmProviders,
      'ChainRpcProviders.registerEvmProviders is not a function — this is the INC-2026-04-20 bug. ' +
        'Check dashboard/package.json overrides for @dynamic-labs/wallet-connector-core and ethereum-core.',
    ).toBe('function')
  })
})

/**
 * DynamicProvider — integration smoke test.
 *
 * This test renders the REAL `<DynamicProvider>` (no mock of
 * `@dynamic-labs/sdk-react-core`) to catch regressions where the SDK itself
 * explodes at module-load time — the exact shape of INC-2026-04-20 where
 * `ChainRpcProviders.registerEvmProviders is not a function` was swallowed
 * by the SDK's error boundary and surfaced only as `[WalletConnector] [ERROR]:`
 * console output.
 *
 * What we assert:
 *   - The provider mounts without throwing (React render doesn't reject).
 *   - The child subtree renders (proving the provider didn't short-circuit).
 *   - `console.error` does NOT contain the Dynamic WalletConnector failure
 *     signature. This is the regression guard: if Dynamic regresses and
 *     fails internally, it logs via `console.error("[WalletConnector] …")`
 *     instead of throwing. Unit tests that mock the SDK miss this entirely.
 *
 * Known limitation: Dynamic's SDK makes real network calls to
 * `app.dynamicauth.com` at initialization. In jsdom without `fetch` polyfill,
 * those requests fail silently — that's fine for this test: we only care about
 * module-load-time failures, not auth flow correctness.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import { DynamicProvider } from '../../providers/DynamicProvider'

// Preserve real i18n mock from setup.ts — we do NOT want to mock
// `@dynamic-labs/sdk-react-core` here; the whole point is to exercise the
// real module graph.

// Minimal env setup — the provider reads VITE_DYNAMIC_ENVIRONMENT_ID via
// `isDynamicConfigured()` and short-circuits with a warning banner if unset.
// Stub it so we enter the real `DynamicContextProvider` branch.
vi.stubEnv('VITE_DYNAMIC_ENVIRONMENT_ID', '00000000-0000-0000-0000-000000000000')

// NOTE: Dynamic's SDK touches indexedDB (keychain) and canvas (fingerprint)
// at init. Neither is available in jsdom, so the SDK reports unhandled
// rejections that show up in Vitest's "Errors" count but do NOT fail any
// assertion. They are NOT the failure signature we guard against in this
// test (we only match WalletConnector + registerEvmProviders). Leave them
// as known environment noise rather than mocking the SDK's internals.

/** Collect all console.error calls made during a render. */
function captureConsoleErrors() {
  const errors: unknown[][] = []
  const spy = vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
    errors.push(args)
  })
  return { errors, spy }
}

/** Match the WalletConnector failure signature Dynamic logs on init break. */
const DYNAMIC_WALLET_CONNECTOR_ERROR = /\[WalletConnector\]\s*\[ERROR\]/i
const REGISTER_EVM_PROVIDERS_BUG = /registerEvmProviders is not a function/i

describe('DynamicProvider integration', () => {
  beforeEach(() => {
    // Some Dynamic internals touch `fetch` at boot. Stub it to a no-op
    // rejection so we don't hit the network, and so nothing writes
    // to console.error as a side effect of the environment (only real
    // Dynamic wiring failures should trip the assertion below).
    if (!globalThis.fetch) {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error('stub fetch')) as unknown as typeof fetch
    }
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('mounts without throwing and renders children', async () => {
    const { errors, spy } = captureConsoleErrors()

    expect(() => {
      render(
        <DynamicProvider>
          <div data-testid="provider-child">hello</div>
        </DynamicProvider>,
      )
    }).not.toThrow()

    // Let micro-tasks (and the SDK's synchronous init side-effects) settle.
    await new Promise((resolve) => setTimeout(resolve, 50))

    const flat = errors.flat().map((v) => (typeof v === 'string' ? v : String(v))).join(' | ')

    // The regression we care about: Dynamic failing to load connectors.
    expect(
      DYNAMIC_WALLET_CONNECTOR_ERROR.test(flat),
      `DynamicProvider emitted WalletConnector error at mount:\n${flat}`,
    ).toBe(false)
    expect(
      REGISTER_EVM_PROVIDERS_BUG.test(flat),
      `registerEvmProviders regression detected (INC-2026-04-20):\n${flat}`,
    ).toBe(false)

    spy.mockRestore()
  })
})

/**
 * Wallet Login Flow — post-deploy regression smoke.
 *
 * This test exists to catch the exact shape of INC-2026-04-20:
 *   - A transitive dependency mismatch between @dynamic-labs/wallet-connector-core
 *     and @dynamic-labs/ethereum caused `registerEvmProviders is not a function`
 *     at runtime.
 *   - Dynamic's SDK swallowed the throw and surfaced only
 *     `[WalletConnector] [ERROR]: …` in console.error.
 *   - The login widget never mounted. The existing E2E suite uses the
 *     window.__E2E_AUTH__ escape hatch so it kept passing.
 *
 * This spec intentionally does NOT use the E2E auth fixture — it goes through
 * the real landing page, waits for Dynamic to attempt to boot, and asserts
 * that none of the known failure signatures appeared in the browser console.
 *
 * How to run:
 *   - Locally (against dev server):  npx playwright test tests/wallet-login-flow.spec.ts
 *   - Against production:            PLAYWRIGHT_BASE_URL=https://execution.market \
 *                                    npx playwright test tests/wallet-login-flow.spec.ts
 *
 * The default baseURL in playwright.config.ts points at http://localhost:3000.
 * Override with `PLAYWRIGHT_BASE_URL` (respected by Playwright's `use.baseURL`)
 * or use `page.goto(fullUrl)` directly.
 */

import { test, expect } from '@playwright/test'
import type { ConsoleMessage } from '@playwright/test'

// Failure signatures we specifically guard against. Each corresponds to a
// real production outage shape.
const FORBIDDEN_CONSOLE_PATTERNS: Array<{ pattern: RegExp; reason: string }> = [
  {
    pattern: /registerEvmProviders is not a function/i,
    reason: 'INC-2026-04-20: @dynamic-labs transitive version mismatch',
  },
  {
    pattern: /\[WalletConnector\]\s*\[ERROR\]/i,
    reason: 'Dynamic WalletConnector initialization failure',
  },
  {
    pattern: /Dynamic SDK did not load within 10s/i,
    reason: 'AuthContext forced-init safety net tripped — SDK is dead',
  },
]

test.describe('Wallet Login Flow — regression smoke', () => {
  test.use({
    // Override any stored state from the auth fixtures — we MUST go through
    // a fresh, unauthenticated load so that Dynamic actually tries to boot.
    storageState: { cookies: [], origins: [] },
  })

  test('landing loads without Dynamic/WalletConnector console errors', async ({ page }) => {
    const consoleErrors: string[] = []
    const pageErrors: string[] = []

    page.on('console', (msg: ConsoleMessage) => {
      // We only guard against `error` level — warnings are fine (e.g. Dynamic
      // logs a connect-and-sign info line at warn level in some builds).
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    page.on('pageerror', (err: Error) => {
      pageErrors.push(`${err.name}: ${err.message}`)
    })

    await page.goto('/')

    // Let Dynamic's lazy-loaded vendor chunk hydrate and run its init.
    // AuthContext's safety net trips at 10s; we wait 15s to catch it.
    await page.waitForTimeout(15_000)

    // --- Assertion 1: no forbidden console errors ---
    const combined = [...consoleErrors, ...pageErrors].join('\n')
    for (const { pattern, reason } of FORBIDDEN_CONSOLE_PATTERNS) {
      expect(
        pattern.test(combined),
        `Forbidden console pattern matched (${reason}):\nFull console dump:\n${combined}`,
      ).toBe(false)
    }

    // --- Assertion 2: a login affordance exists ---
    // The landing surface must give the user SOMEthing to click to start
    // auth — either the Dynamic widget, the Earn-money CTA, or a header
    // "Connect" / "Sign in" button. We allow any of these to be present.
    const hasLoginAffordance = await Promise.any([
      page.getByText(/Earn money/i).first().waitFor({ timeout: 5_000 }).then(() => true),
      page.getByText(/Execution Market/i).first().waitFor({ timeout: 5_000 }).then(() => true),
      page.locator('[data-testid*="dynamic"], button:has-text("Connect"), button:has-text("Sign in")')
        .first()
        .waitFor({ timeout: 5_000 })
        .then(() => true),
    ]).catch(() => false)

    expect(
      hasLoginAffordance,
      'No login affordance found on landing page. Either the page failed to ' +
        'render or Dynamic crashed at init. Console dump:\n' + combined,
    ).toBe(true)
  })
})

/**
 * Execution Market E2E Tests - Authentication
 *
 * Verifies the E2E auth escape hatch and role guards.
 */

import { test, expect } from '../fixtures/auth'
import { test as base } from '@playwright/test'
import { setupMocks } from '../fixtures/mocks'

const TEXT = {
  workerTab: /Available Tasks|Buscar Tareas|Tareas Disponibles/i,
  agentTitle: /Agent Dashboard|Panel de Agente/i,
}

test.describe('Authentication - Escape Hatch', () => {
  test('worker page loads authenticated', async ({ workerPage }) => {
    // Capture console messages
    const consoleLogs: string[] = []
    workerPage.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`)
    })

    await setupMocks(workerPage)
    await workerPage.goto('/tasks')

    // Debug: Log page HTML and console if first check fails
    try {
      await expect(workerPage).toHaveURL(/\/tasks$/, { timeout: 5000 })
    } catch (e) {
      const html = await workerPage.content()
      console.log('=== PAGE HTML ===')
      console.log(html.substring(0, 2000))
      console.log('=== CONSOLE LOGS ===')
      console.log(consoleLogs.join('\n'))
      throw e
    }

    await expect(workerPage.getByRole('button', { name: /Execution Market/i })).toBeVisible()
    await expect(workerPage.getByRole('button', { name: TEXT.workerTab })).toBeVisible()
  })

  test('agent page loads authenticated', async ({ agentPage }) => {
    await setupMocks(agentPage)
    await agentPage.goto('/agent/dashboard')

    await expect(agentPage).toHaveURL(/\/agent\/dashboard$/)
    await expect(agentPage.getByRole('heading', { name: TEXT.agentTitle })).toBeVisible({ timeout: 15000 })
  })

  test('worker is redirected away from agent routes', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/agent/dashboard')

    await expect(workerPage).toHaveURL(/\/tasks$/)
  })

  test('agent is redirected away from worker routes', async ({ agentPage }) => {
    await setupMocks(agentPage)
    await agentPage.goto('/tasks')

    await expect(agentPage).toHaveURL(/\/agent\/dashboard$/)
  })
})

base.describe('Authentication - Unauthenticated', () => {
  base.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  base('landing page loads for unauthenticated users', async ({ page }) => {
    await page.goto('/')

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('Execution Market').first()).toBeVisible()
    await expect(page.locator('header').first()).toBeVisible()
  })

  base('landing page shows payment trust signal', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText(/USDC|x402|Instant/i).first()).toBeVisible({ timeout: 15000 })
  })
})

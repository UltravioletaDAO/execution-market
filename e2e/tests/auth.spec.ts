/**
 * Execution Market E2E Tests - Authentication
 *
 * Tests that the E2E escape hatch works correctly:
 * - Page loads as authenticated worker
 * - Page loads as authenticated agent
 * - Unauthenticated page shows landing
 */

import { test, expect } from '../fixtures/auth'
import { test as base } from '@playwright/test'
import { setupMocks } from '../fixtures/mocks'

test.describe('Authentication - Escape Hatch', () => {
  test('worker page loads authenticated', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/')

    // Authenticated workers should see "My Tasks" or profile nav
    await expect(workerPage.getByText('Execution Market')).toBeVisible()

    // Should NOT see the "Start Earning" CTA (that's for unauthenticated users)
    // Instead should see nav options for authenticated users
    await workerPage.goto('/tasks')
    await expect(workerPage.getByText(/Buscar Tareas|Disponibles/)).toBeVisible({ timeout: 15000 })
  })

  test('agent page loads authenticated', async ({ agentPage }) => {
    await setupMocks(agentPage)
    await agentPage.goto('/agent/dashboard')

    // Agent dashboard should show "Panel de Agente"
    await expect(agentPage.getByText('Panel de Agente')).toBeVisible({ timeout: 15000 })
  })

  test('worker can navigate to tasks page', async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/tasks')

    // Should see the task browser, not a login redirect
    await expect(workerPage.getByText(/Buscar Tareas|Disponibles/)).toBeVisible({ timeout: 15000 })
  })

  test('agent can navigate to agent dashboard', async ({ agentPage }) => {
    await setupMocks(agentPage)
    await agentPage.goto('/agent/dashboard')

    // Should see agent-specific content
    await expect(agentPage.getByText('Panel de Agente')).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByText('Crear Tarea')).toBeVisible()
  })
})

base.describe('Authentication - Unauthenticated', () => {
  base.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  base('landing page loads for unauthenticated users', async ({ page }) => {
    await page.goto('/')

    // Should see the hero section
    await expect(page.getByText('Execution Market')).toBeVisible()

    // Should see CTA for unauthenticated users
    await expect(
      page.getByText(/Earn money|Get paid instantly|Start Earning|Browse Available Jobs/)
    ).toBeVisible({ timeout: 15000 })
  })

  base('landing page shows key value proposition', async ({ page }) => {
    await page.goto('/')

    // Should show trust signals or features
    await expect(page.getByText(/USDC/)).toBeVisible({ timeout: 15000 })
  })
})

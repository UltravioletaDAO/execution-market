/**
 * Execution Market E2E Tests - Navigation
 *
 * Tests for basic navigation, routing, and public pages.
 * Uses role/text-based selectors.
 */

import { test as base, expect } from '@playwright/test'
import { test } from '../fixtures/auth'
import { setupMocks } from '../fixtures/mocks'

// ============================================================================
// Public Routes (no auth needed)
// ============================================================================

base.describe('Public Navigation', () => {
  base.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  base('home page loads', async ({ page }) => {
    await page.goto('/')

    // Should show the app name
    await expect(page.getByText('Execution Market')).toBeVisible({ timeout: 15000 })
  })

  base('about page loads', async ({ page }) => {
    await page.goto('/about')

    // Should not be a blank page — some content should be visible
    await expect(page.locator('body')).not.toBeEmpty()
  })

  base('faq page loads', async ({ page }) => {
    await page.goto('/faq')

    await expect(page.locator('body')).not.toBeEmpty()
  })

  base('logo navigates to home', async ({ page }) => {
    await page.goto('/about')

    // Click the logo/brand text
    await page.getByText('Execution Market').first().click()

    // Should be back at home
    await expect(page).toHaveURL(/^\/$|\/$/  )
  })

  base('header is visible on all pages', async ({ page }) => {
    await page.goto('/')

    // Header should be visible (contains "Execution Market" text)
    await expect(
      page.locator('header').first()
    ).toBeVisible({ timeout: 15000 })
  })
})

// ============================================================================
// Authenticated Worker Navigation
// ============================================================================

test.describe('Worker Navigation', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('can navigate to tasks page', async ({ workerPage }) => {
    await workerPage.goto('/tasks')

    await expect(
      workerPage.getByText(/Buscar Tareas|Disponibles/)
    ).toBeVisible({ timeout: 15000 })
  })

  test('can navigate to profile page', async ({ workerPage }) => {
    await workerPage.goto('/profile')

    // Profile page should show something
    await expect(workerPage.locator('body')).not.toBeEmpty()
  })

  test('can navigate to earnings page', async ({ workerPage }) => {
    await workerPage.goto('/earnings')

    // Earnings page should show heading
    await expect(
      workerPage.getByText(/Mis Ganancias|Earnings/)
    ).toBeVisible({ timeout: 15000 })
  })
})

// ============================================================================
// Authenticated Agent Navigation
// ============================================================================

test.describe('Agent Navigation', () => {
  test.beforeEach(async ({ agentPage }) => {
    await setupMocks(agentPage)
  })

  test('can navigate to agent dashboard', async ({ agentPage }) => {
    await agentPage.goto('/agent/dashboard')

    await expect(
      agentPage.getByText('Panel de Agente')
    ).toBeVisible({ timeout: 15000 })
  })

  test('can navigate to home from agent dashboard', async ({ agentPage }) => {
    await agentPage.goto('/agent/dashboard')

    // Wait for dashboard to load
    await expect(
      agentPage.getByText('Panel de Agente')
    ).toBeVisible({ timeout: 15000 })

    // Click logo to go home
    await agentPage.getByText('Execution Market').first().click()

    await expect(agentPage).toHaveURL(/^\/$/)
  })
})

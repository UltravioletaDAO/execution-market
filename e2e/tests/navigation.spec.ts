/**
 * Execution Market E2E Tests - Navigation
 */

import { test as base, expect } from '@playwright/test'
import { test } from '../fixtures/auth'
import { setupMocks } from '../fixtures/mocks'

const TEXT = {
  workerTab: /Available Tasks|Buscar Tareas|Tareas Disponibles/i,
  earningsTitle: /Mis Ganancias|Earnings/i,
  agentTitle: /Agent Dashboard|Panel de Agente/i,
  createTask: /Create Task|Crear Tarea/i,
}

base.describe('Public Navigation', () => {
  base.beforeEach(async ({ page }) => {
    await setupMocks(page)
  })

  base('home page loads', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Execution Market').first()).toBeVisible({ timeout: 15000 })
  })

  base('about page loads', async ({ page }) => {
    await page.goto('/about')
    await expect(page.locator('body')).not.toBeEmpty()
  })

  base('faq page loads', async ({ page }) => {
    await page.goto('/faq')
    await expect(page.locator('body')).not.toBeEmpty()
  })

  base('logo navigates to home', async ({ page }) => {
    await page.goto('/about')
    await page.getByText('Execution Market').first().click()
    await expect(page).toHaveURL(/\/$/)
  })

  base('header is visible on public pages', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('header').first()).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Worker Navigation', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('can navigate to tasks page', async ({ workerPage }) => {
    await workerPage.goto('/tasks')
    await expect(workerPage).toHaveURL(/\/tasks$/)
    await expect(workerPage.getByRole('button', { name: TEXT.workerTab })).toBeVisible({ timeout: 15000 })
  })

  test('can navigate to profile page', async ({ workerPage }) => {
    await workerPage.goto('/profile')
    await expect(workerPage).toHaveURL(/\/profile$/)
    await expect(workerPage.locator('body')).not.toBeEmpty()
  })

  test('can navigate to earnings page', async ({ workerPage }) => {
    await workerPage.goto('/earnings')
    await expect(workerPage).toHaveURL(/\/earnings$/)
    await expect(
      workerPage.getByRole('heading', { name: TEXT.earningsTitle }).first()
    ).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Agent Navigation', () => {
  test.beforeEach(async ({ agentPage }) => {
    await setupMocks(agentPage)
  })

  test('can navigate to agent dashboard', async ({ agentPage }) => {
    await agentPage.goto('/agent/dashboard')
    await expect(agentPage).toHaveURL(/\/agent\/dashboard$/)
    await expect(agentPage.getByRole('heading', { name: TEXT.agentTitle })).toBeVisible({ timeout: 15000 })
  })

  test('can navigate to create task from dashboard', async ({ agentPage }) => {
    await agentPage.goto('/agent/dashboard')
    await agentPage.getByRole('button', { name: TEXT.createTask }).first().click()
    await expect(agentPage).toHaveURL(/\/agent\/tasks\/new$/)
  })
})

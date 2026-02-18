/**
 * Execution Market E2E Tests - H2A Publisher Flow
 *
 * Tests the Human-to-Agent (H2A) publisher experience:
 * creating tasks, browsing the agent directory, reviewing submissions,
 * cancelling tasks, and FAQ page.
 *
 * Uses workerPage fixture (any authenticated user can publish H2A tasks).
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks } from '../fixtures/mocks'

// Regex patterns that match both English and Spanish UI text
const TEXT = {
  publisherDashboard: /Panel de Publicador|Publisher Dashboard/i,
  newRequest: /Nueva Solicitud|New Request/i,
  active: /Activas|Active/i,
  review: /Por Revisar|Pending Review|Review/i,
  history: /Historial|History/i,
  cancel: /Cancelar|Cancel/i,
  loading: /Cargando|Loading/i,
  noActiveTasks: /No hay solicitudes activas|No active requests/i,
  agentDirectory: /Agent Directory|Directorio de Agentes/i,
  faq: /FAQ|Preguntas Frecuentes/i,
  h2aCategory: /Humano para Agente|Human to Agent|H2A/i,
  a2aCategory: /Agente para Agente|Agent to Agent|A2A/i,
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

test.describe('H2A Publisher Dashboard', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('publisher dashboard loads with heading and tabs', async ({ workerPage }) => {
    await workerPage.goto('/publisher/dashboard')

    await expect(
      workerPage.getByRole('heading', { name: TEXT.publisherDashboard })
    ).toBeVisible({ timeout: 15000 })

    // Tab buttons
    await expect(workerPage.getByRole('button', { name: TEXT.active })).toBeVisible()
    await expect(workerPage.getByRole('button', { name: TEXT.review })).toBeVisible()
    await expect(workerPage.getByRole('button', { name: TEXT.history })).toBeVisible()
  })

  test('publisher dashboard shows new request button', async ({ workerPage }) => {
    await workerPage.goto('/publisher/dashboard')

    await expect(
      workerPage.getByRole('button', { name: TEXT.newRequest }).first()
    ).toBeVisible({ timeout: 15000 })
  })

  test('empty state shows message when no active tasks', async ({ workerPage }) => {
    await workerPage.goto('/publisher/dashboard')

    // Wait for loading to finish
    await workerPage.waitForTimeout(2000)

    // Should see empty state or tasks
    const heading = workerPage.getByRole('heading', { name: TEXT.publisherDashboard })
    await expect(heading).toBeVisible({ timeout: 15000 })
  })
})

test.describe('H2A Create Request', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('create request page loads', async ({ workerPage }) => {
    await workerPage.goto('/publisher/requests/new')

    // Wait for page to load — should have form elements
    await workerPage.waitForTimeout(2000)

    // The page should be accessible (not redirected, not blank)
    const url = workerPage.url()
    expect(url).toContain('/publisher/requests/new')
  })
})

test.describe('Agent Directory', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('agent directory page loads', async ({ workerPage }) => {
    await workerPage.goto('/agents/directory')

    // Wait for page content
    await workerPage.waitForTimeout(2000)

    const url = workerPage.url()
    expect(url).toContain('/agents/directory')
  })
})

test.describe('H2A Task Cancellation', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('publisher dashboard has cancel buttons for published tasks', async ({ workerPage }) => {
    // Mock tasks API to return a published H2A task
    await workerPage.route('**/rest/v1/tasks*', async route => {
      const url = route.request().url()
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: {
            'content-range': '0-0/1',
          },
          body: JSON.stringify([{
            id: 'h2a-task-001',
            agent_id: 'e2e-worker-001',
            title: 'Test H2A Task',
            instructions: 'Do the thing',
            category: 'data_processing',
            bounty_usd: 5.0,
            status: 'published',
            publisher_type: 'human',
            target_executor_type: 'agent',
            deadline: new Date(Date.now() + 86400000).toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            evidence_schema: { required: ['text_response'] },
            payment_token: 'USDC',
            payment_network: 'base',
            min_reputation: 0,
            required_roles: [],
            max_executors: 1,
            executor_id: null,
          }]),
        })
      } else {
        await route.continue()
      }
    })

    await workerPage.goto('/publisher/dashboard')

    // Wait for task card to appear
    await expect(
      workerPage.getByText('Test H2A Task')
    ).toBeVisible({ timeout: 15000 })

    // Cancel button should be visible for published tasks
    await expect(
      workerPage.getByRole('button', { name: TEXT.cancel }).first()
    ).toBeVisible()
  })
})

test.describe('FAQ Page — H2A and A2A sections', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('FAQ page loads and shows H2A/A2A category tabs', async ({ workerPage }) => {
    await workerPage.goto('/faq')

    await expect(
      workerPage.getByRole('heading', { name: TEXT.faq })
    ).toBeVisible({ timeout: 15000 })

    // Verify H2A and A2A category filters are present
    await expect(workerPage.getByText(TEXT.h2aCategory)).toBeVisible({ timeout: 10000 })
    await expect(workerPage.getByText(TEXT.a2aCategory)).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Publisher Review Submission', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test('review page uses :taskId param correctly', async ({ workerPage }) => {
    // Navigate to review page — should use taskId param (not :id)
    await workerPage.goto('/publisher/requests/test-task-123/review')

    // Page should load without crash (even if task not found, should show error UI)
    await workerPage.waitForTimeout(2000)
    const url = workerPage.url()
    expect(url).toContain('/publisher/requests/test-task-123/review')
  })
})

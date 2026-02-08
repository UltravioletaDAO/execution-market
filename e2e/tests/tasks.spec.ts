/**
 * Execution Market E2E Tests - Tasks (Worker View)
 *
 * Tests for task browsing and interaction from the worker perspective.
 * Uses role/text-based selectors.
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks, mockTasks } from '../fixtures/mocks'

test.describe('Tasks - Worker View', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
  })

  test.describe('Task List', () => {
    test('task list loads with available tasks', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Should see "Buscar Tareas" heading or "Disponibles" tab
      await expect(
        workerPage.getByText(/Buscar Tareas|Disponibles/)
      ).toBeVisible({ timeout: 15000 })

      // Should display at least one mock task title
      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })
    })

    test('displays task bounty amounts', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Wait for tasks to load
      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })

      // Should show bounty amounts (e.g., "$15.00")
      await expect(
        workerPage.getByText(`$${mockTasks[0].bounty_usd.toFixed(2)}`)
      ).toBeVisible()
    })

    test('displays multiple tasks', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Should show titles from multiple mock tasks
      for (const task of mockTasks) {
        await expect(
          workerPage.getByText(task.title)
        ).toBeVisible({ timeout: 10000 })
      }
    })

    test('shows USDC payment token', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Wait for tasks to load
      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })

      // Should show USDC somewhere
      await expect(
        workerPage.getByText(/USDC/).first()
      ).toBeVisible()
    })
  })

  test.describe('Task Tabs', () => {
    test('shows available tasks tab', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Should see the "Disponibles" tab
      await expect(
        workerPage.getByText('Disponibles')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows near me tab', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Should see "Cerca de mi" tab
      await expect(
        workerPage.getByText('Cerca de mi')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows my applications tab', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Should see "Mis Solicitudes" tab
      await expect(
        workerPage.getByText('Mis Solicitudes')
      ).toBeVisible({ timeout: 15000 })
    })
  })

  test.describe('Task Filtering', () => {
    test('shows filter controls', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Wait for page to load
      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })

      // Should show filter label
      await expect(
        workerPage.getByText('Filtros')
      ).toBeVisible()
    })

    test('shows category filter options', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })

      // Should show category names
      await expect(
        workerPage.getByText('Presencia Fisica')
      ).toBeVisible()
    })

    test('shows bounty filter', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })

      // Should show bounty filter label
      await expect(
        workerPage.getByText(/Recompensa/)
      ).toBeVisible()
    })

    test('has clear filters button', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      await expect(
        workerPage.getByText(mockTasks[0].title)
      ).toBeVisible({ timeout: 10000 })

      // Should show clear filters button
      await expect(
        workerPage.getByText('Limpiar filtros')
      ).toBeVisible()
    })
  })

  test.describe('Task Search', () => {
    test('shows search input', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      // Should have a search input
      await expect(
        workerPage.getByPlaceholder(/Buscar tareas/)
      ).toBeVisible({ timeout: 15000 })
    })

    test('can type in search input', async ({ workerPage }) => {
      await workerPage.goto('/tasks')

      const searchInput = workerPage.getByPlaceholder(/Buscar tareas/)
      await expect(searchInput).toBeVisible({ timeout: 15000 })

      await searchInput.fill('tienda')

      // Verify the input has the value
      await expect(searchInput).toHaveValue('tienda')
    })
  })
})

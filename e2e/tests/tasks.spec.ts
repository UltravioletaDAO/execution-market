/**
 * Execution Market E2E Tests - Tasks (Worker View)
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks, mockTasks } from '../fixtures/mocks'

const TEXT = {
  availableTab: /Available Tasks|Buscar Tareas|Tareas Disponibles|Disponibles/i,
  myTasksTab: /My Tasks|Mis Tareas|Mis Solicitudes/i,
  allCategory: /(^|\s)All($|\s)|Todos/i,
  physicalPresence: /Physical Presence|Presencia Fisica|Presencia Física/i,
}

test.describe('Tasks - Worker View', () => {
  test.beforeEach(async ({ workerPage }) => {
    await setupMocks(workerPage)
    await workerPage.goto('/tasks')
  })

  test('task list loads with available tasks', async ({ workerPage }) => {
    await expect(
      workerPage.getByRole('button', { name: TEXT.availableTab })
    ).toBeVisible({ timeout: 15000 })

    await expect(
      workerPage.getByText(mockTasks[0].title)
    ).toBeVisible({ timeout: 15000 })
  })

  test('displays task bounty amounts', async ({ workerPage }) => {
    await expect(workerPage.getByText(mockTasks[0].title)).toBeVisible({ timeout: 15000 })

    await expect(
      workerPage.getByText(`$${mockTasks[0].bounty_usd.toFixed(2)}`)
    ).toBeVisible()
  })

  test('displays multiple tasks', async ({ workerPage }) => {
    for (const task of mockTasks) {
      await expect(workerPage.getByText(task.title)).toBeVisible({ timeout: 15000 })
    }
  })

  test('shows USDC payment token on task cards', async ({ workerPage }) => {
    await expect(workerPage.getByText(mockTasks[0].title)).toBeVisible({ timeout: 15000 })
    await expect(workerPage.getByText(/USDC/).first()).toBeVisible()
  })

  test('shows available and my tasks tabs', async ({ workerPage }) => {
    await expect(workerPage.getByRole('button', { name: TEXT.availableTab })).toBeVisible({ timeout: 15000 })
    await expect(workerPage.getByRole('button', { name: TEXT.myTasksTab })).toBeVisible({ timeout: 15000 })
  })

  test('shows category filters', async ({ workerPage }) => {
    await expect(workerPage.getByRole('button', { name: TEXT.allCategory })).toBeVisible({ timeout: 15000 })
    await expect(
      workerPage.getByRole('button', { name: TEXT.physicalPresence }).first()
    ).toBeVisible({ timeout: 15000 })
  })
})

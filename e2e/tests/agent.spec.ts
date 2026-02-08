/**
 * Execution Market E2E Tests - Agent Dashboard
 *
 * Tests for the agent dashboard view.
 * Uses role/text-based selectors.
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks } from '../fixtures/mocks'

test.describe('Agent Dashboard', () => {
  test.beforeEach(async ({ agentPage }) => {
    await setupMocks(agentPage)
  })

  test.describe('Dashboard Overview', () => {
    test('dashboard loads with correct heading', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      // Should show "Panel de Agente"
      await expect(
        agentPage.getByText('Panel de Agente')
      ).toBeVisible({ timeout: 15000 })
    })

    test('dashboard shows subtitle', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Gestiona tus tareas y revisa entregas')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows create task button', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Crear Tarea')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows platform pulse section', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      // Should show Platform Pulse heading
      await expect(
        agentPage.getByText('Platform Pulse')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows activity summary section', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Resumen de Actividad')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows stat cards', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      // Should show various stat labels
      await expect(
        agentPage.getByText('Tareas Creadas')
      ).toBeVisible({ timeout: 15000 })

      await expect(
        agentPage.getByText('Tasa de Completado')
      ).toBeVisible()
    })
  })

  test.describe('Active Tasks Section', () => {
    test('shows active tasks section', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Tareas Activas')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows task filter buttons', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      // Task filter buttons
      await expect(
        agentPage.getByText('Todas')
      ).toBeVisible({ timeout: 15000 })

      await expect(
        agentPage.getByText('Pendientes')
      ).toBeVisible()
    })
  })

  test.describe('Submissions Section', () => {
    test('shows pending submissions section', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Entregas por Revisar')
      ).toBeVisible({ timeout: 15000 })
    })
  })

  test.describe('Quick Actions', () => {
    test('shows quick actions section', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Acciones Rapidas')
      ).toBeVisible({ timeout: 15000 })
    })

    test('shows quick action buttons', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Nueva Tarea')
      ).toBeVisible({ timeout: 15000 })

      await expect(
        agentPage.getByText('Revisar Siguiente')
      ).toBeVisible()
    })
  })

  test.describe('Recent Activity', () => {
    test('shows recent activity section', async ({ agentPage }) => {
      await agentPage.goto('/agent/dashboard')

      await expect(
        agentPage.getByText('Actividad Reciente')
      ).toBeVisible({ timeout: 15000 })
    })
  })
})

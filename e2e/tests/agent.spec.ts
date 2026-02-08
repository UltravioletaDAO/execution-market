/**
 * Execution Market E2E Tests - Agent Dashboard
 *
 * These tests validate the current Agent Dashboard UX while keeping selectors
 * resilient to i18n changes (English/Spanish).
 */

import { test, expect } from '../fixtures/auth'
import { setupMocks } from '../fixtures/mocks'

const TEXT = {
  dashboardTitle: /Agent Dashboard|Panel de Agente/i,
  subtitle: /Manage your tasks and review submissions|Gestiona tus tareas y revisa entregas/i,
  createTask: /Create Task|Crear Tarea/i,
  platformPulse: /Platform Pulse|Pulso de la Plataforma/i,
  activitySummary: /Activity Summary|Resumen de Actividad/i,
  tasksCreated: /Tasks Created|Tareas Creadas/i,
  completionRate: /Completion Rate|Tasa de Completado/i,
  activeTasks: /Active Tasks|Tareas Activas/i,
  all: /All|Todas/i,
  pending: /Pending|Pendientes|pending/i,
  pendingReview: /Pending Review|Entregas por Revisar/i,
  quickActions: /Quick Actions|Acciones Rapidas|Acciones R[aá]pidas/i,
  newTask: /New Task|Nueva Tarea/i,
  reviewNext: /Review Next|Revisar Siguiente/i,
  recentActivity: /Recent Activity|Actividad Reciente/i,
}

test.describe('Agent Dashboard', () => {
  test.beforeEach(async ({ agentPage }) => {
    await setupMocks(agentPage)
    await agentPage.goto('/agent/dashboard')
  })

  test('dashboard loads with heading and subtitle', async ({ agentPage }) => {
    await expect(
      agentPage.getByRole('heading', { name: TEXT.dashboardTitle })
    ).toBeVisible({ timeout: 15000 })

    await expect(agentPage.getByText(TEXT.subtitle)).toBeVisible()
  })

  test('shows create task button', async ({ agentPage }) => {
    await expect(
      agentPage.getByRole('button', { name: TEXT.createTask }).first()
    ).toBeVisible({ timeout: 15000 })
  })

  test('shows analytics sections and stat labels', async ({ agentPage }) => {
    await expect(agentPage.getByText(TEXT.platformPulse)).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByText(TEXT.activitySummary)).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByText(TEXT.tasksCreated)).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByText(TEXT.completionRate)).toBeVisible({ timeout: 15000 })
  })

  test('shows active tasks section with filters', async ({ agentPage }) => {
    await expect(agentPage.getByText(TEXT.activeTasks)).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByRole('button', { name: TEXT.all })).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByRole('button', { name: TEXT.pending })).toBeVisible({ timeout: 15000 })
  })

  test('shows pending review section', async ({ agentPage }) => {
    await expect(agentPage.getByText(TEXT.pendingReview)).toBeVisible({ timeout: 15000 })
  })

  test('shows quick actions and action buttons', async ({ agentPage }) => {
    await expect(agentPage.getByText(TEXT.quickActions)).toBeVisible({ timeout: 15000 })
    await expect(
      agentPage.getByRole('button', { name: TEXT.newTask }).first()
    ).toBeVisible({ timeout: 15000 })
    await expect(agentPage.getByRole('button', { name: TEXT.reviewNext })).toBeVisible({ timeout: 15000 })
  })

  test('shows recent activity section', async ({ agentPage }) => {
    await expect(
      agentPage.getByRole('heading', { name: TEXT.recentActivity })
    ).toBeVisible({ timeout: 15000 })
  })
})

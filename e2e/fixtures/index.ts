/**
 * Execution Market E2E Test Fixtures - Index
 *
 * Central export for all test fixtures and helpers.
 */

// Auth
export {
  test,
  expect,
  injectAuth,
  MOCK_WORKER,
  MOCK_AGENT,
  type MockUser,
  type AuthFixtures,
} from './auth'

// Mocks
export {
  setupMocks,
  mockGeolocation,
  mockCamera,
  mockTasks,
  mockSubmissions,
  mockExecutor,
  mockAgent,
  type Task,
  type TaskCategory,
  type TaskStatus,
  type Executor,
  type Submission,
  type MockOptions,
} from './mocks'

// Tasks
export {
  getTaskById,
  getTasksByStatus,
  getTasksByCategory,
  waitForTasks,
  getVisibleTaskCount,
} from './tasks'

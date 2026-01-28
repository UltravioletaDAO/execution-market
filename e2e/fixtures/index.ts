/**
 * Chamba E2E Test Fixtures - Index
 *
 * Central export for all test fixtures and helpers.
 */

// Mocks
export {
  setupMocks,
  mockWalletConnection,
  mockGeolocation,
  mockCamera,
  mockFileUpload,
  mockTasks,
  mockSubmissions,
  mockApplications,
  mockExecutor,
  mockAgent,
  type Task,
  type TaskCategory,
  type TaskStatus,
  type Executor,
  type Submission,
  type TaskApplication,
  type Location,
  type MockOptions,
} from './mocks'

// Auth
export {
  test,
  expect,
  loginWithEmail,
  loginWithWallet,
  logout,
  isLoggedIn,
  getCurrentUser,
  saveAuthState,
  TEST_EXECUTOR,
  TEST_AGENT,
  type TestUser,
  type AuthFixtures,
} from './auth'

// Tasks
export {
  createTaskViaUI,
  getTaskById,
  getTasksByStatus,
  getTasksByCategory,
  applyToTask,
  acceptTaskApplication,
  rejectTaskApplication,
  approveSubmission,
  rejectSubmission,
  filterByCategory,
  filterByStatus,
  searchTasks,
  assertTaskCardVisible,
  assertTaskCount,
  type CreateTaskInput,
} from './tasks'

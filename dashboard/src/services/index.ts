/**
 * Execution Market API Services
 *
 * Barrel export for all API services.
 */

// Base API client
export {
  api,
  get,
  post,
  put,
  patch,
  del,
  setAuthToken,
  clearAuthToken,
  buildUrl,
  toCamelCase,
  toSnakeCase,
} from './api'

// Task services
export {
  getTasks,
  getTask,
  getAvailableTasks,
  createTask,
  applyToTask,
  cancelApplication,
  cancelTask,
  assignTask,
  getMyTasks,
  getAgentTasks,
  getTaskAnalytics,
} from './tasks'

// Submission services
export {
  submitWork,
  getSubmissions,
  getSubmission,
  getMySubmissions,
  getPendingSubmissions,
  approveSubmission,
  rejectSubmission,
  requestMoreInfo,
  uploadEvidenceFile,
} from './submissions'

// Payment services
export {
  getEarnings,
  getPaymentHistory,
  getRecentPayments,
  getEscrowStatus,
  requestWithdrawal,
  getWithdrawalHistory,
  getAgentPaymentStats,
  getFeeStructure,
  calculateFee,
} from './payments'

// Types
export type {
  // Database types (re-exported)
  TaskCategory,
  TaskStatus,
  EvidenceType,
  DisputeStatus,
  EvidenceSchema,
  Location,
  Executor,
  Task,
  Submission,
  Dispute,
  ReputationLog,
  TaskApplication,
  // API request types
  TaskFilters,
  CreateTaskData,
  ApplyToTaskData,
  Evidence,
  SubmitWorkData,
  SubmissionVerdict,
  ApproveSubmissionData,
  RejectSubmissionData,
  CancelTaskData,
  AssignTaskData,
  // API response types
  PaginatedResponse,
  TaskWithExecutor,
  SubmissionWithDetails,
  ApplicationWithTask,
  WorkerTasksResponse,
  AgentAnalytics,
  // Payment types
  Payment,
  EarningsSummary,
  EscrowStatus,
  PaymentHistoryResponse,
  FeeStructure,
  FeeCalculation,
  // Error type
  ApiError,
} from './types'

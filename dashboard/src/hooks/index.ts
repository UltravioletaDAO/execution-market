// Hooks barrel export — only re-export hooks used by live code

export { useTasks, useTask, useAvailableTasks, useMyTasks } from './useTasks'
export {
  useEarnings,
  useReputation,
  useTaskHistory,
  useWithdrawal,
  type EarningsData,
  type ReputationData,
  type TaskHistoryItem,
} from './useProfile'

export {
  useTaskPayment,
  type UseTaskPaymentReturn,
} from './useTaskPayment'

export {
  usePublicMetrics,
  type PublicPlatformMetrics,
} from './usePublicMetrics'

export { usePlatformConfig, getRequireApiKey, ensurePlatformConfig } from './usePlatformConfig'

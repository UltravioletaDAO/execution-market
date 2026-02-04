// Hooks barrel export
export { useTasks, useTask, useAvailableTasks, useMyTasks } from './useTasks'
export { useAuth, useExecutor } from './useAuth'
export {
  useEarnings,
  useReputation,
  useTaskHistory,
  useWithdrawal,
  type EarningsData,
  type ReputationData,
  type TaskHistoryItem,
} from './useProfile'
export { useWalletAuth, type WalletAuthState } from './useWalletAuth'
export {
  useWallet,
  isCrossmintAvailable,
  isMagicAvailable,
  getAvailableWalletTypes,
  type WalletType,
  type WalletState,
  type WalletError,
  type ConnectionStatus,
  type ConnectOptions,
} from './useWallet'
export {
  useDisputes,
  useDispute,
  useCreateDispute,
  type Dispute,
  type DisputeEvidence,
} from './useDisputes'
export { usePWA, usePushNotifications } from './usePWA'
export {
  usePayments,
  usePaymentStats,
  useWithdraw,
  type Payment,
  type PaymentStats,
} from './usePayments'
export {
  useGeolocation,
  calculateDistance,
  isWithinRadius,
} from './useGeolocation'
export {
  useTheme,
  usePrefersDarkMode,
  getThemeScript,
  type ThemeMode,
  type UseThemeOptions,
  type UseThemeReturn,
} from './useTheme'

// x402 Payment Hooks
export {
  usePayment,
  MERCHANT_ROUTER,
  TOKEN_ADDRESSES,
  TOKEN_DECIMALS,
  formatTokenAmount,
  parseTokenAmount,
  type PaymentToken,
  type PaymentResult,
  type PaymentHistoryItem,
  type UsePaymentOptions,
  type UsePaymentReturn,
} from './usePayment'

export {
  useEscrow,
  useEscrowInfo,
  DEPOSIT_RELAY_FACTORY,
  type EscrowStatus,
  type EscrowInfo,
  type EscrowCreateParams,
  type EscrowReleaseParams,
  type EscrowResult,
  type EscrowEvent,
  type UseEscrowOptions,
  type UseEscrowReturn,
} from './useEscrow'

export {
  useX402Wallet,
  SUPPORTED_CHAINS,
  CHAIN_IDS,
  CHAIN_NAMES,
  getChainConfig,
  isChainSupported,
  getChainNameFromId,
  getExplorerTxUrl,
  getExplorerAddressUrl,
  formatAddress,
  type SupportedChainName,
  type SupportedChainId,
  type ConnectionStatus as X402ConnectionStatus,
  type WalletInfo,
  type X402WalletError,
  type UseX402WalletReturn,
} from './useX402Wallet'

export {
  useTokenBalance,
  useSingleTokenBalance,
  formatTokenDisplay,
  formatUsdValue,
  hasEnoughBalance,
  getTokenSymbol,
  type TokenBalance,
  type NativeBalance,
  type UseTokenBalanceOptions,
  type UseTokenBalanceReturn,
  type UseSingleTokenBalanceReturn,
} from './useTokenBalance'

export {
  useTransaction,
  useTransactionHistory,
  getTransactionTypeLabel,
  getStatusColor,
  formatTxHash,
  getTimeSince,
  type TransactionStatus,
  type Transaction,
  type TransactionNotification,
  type UseTransactionOptions,
  type UseTransactionReturn,
  type AddTransactionParams,
  type UseTransactionHistoryOptions,
  type UseTransactionHistoryReturn,
} from './useTransaction'

// Notification Hook
export {
  useNotifications,
  type UseNotificationsReturn,
} from './useNotifications'

// Task Payment Hook
export {
  useTaskPayment,
  type UseTaskPaymentReturn,
} from './useTaskPayment'

// Components barrel export
export { TaskCard } from './TaskCard'
export { TaskList, CategoryFilter } from './TaskList'
export { TaskDetail } from './TaskDetail'
export { SubmissionForm } from './SubmissionForm'
export { AuthModal } from './AuthModal'
export { WalletSelector } from './WalletSelector'
export { LanguageSwitcher, LanguageSwitcherDropdown } from './LanguageSwitcher'
export { EvidenceUpload } from './EvidenceUpload'
export type {
  EvidenceMetadata,
  UploadedEvidence,
  EvidenceUploadProps,
  GPSCoordinates as EvidenceGPSCoordinates,
} from './EvidenceUpload'
export { DisputesPage } from './DisputesPage'
// Legacy NotificationBell - use notifications/NotificationBell instead
export { NotificationBell as NotificationBellLegacy, type Notification as LegacyNotification } from './NotificationBell'
export { LocationFilter, type GPSCoordinates } from './LocationFilter'
export { PWAPrompt } from './PWAPrompt'
export { InstallPrompt, IOSInstallPrompt } from './InstallPrompt'
export { MobileNav } from './MobileNav'
export { TaskBrowser } from './TaskBrowser'
export { SkillSelector, type Skill } from './SkillSelector'
export { OnboardingFlow, type OnboardingData } from './OnboardingFlow'
export { PaymentHistory, type Payment } from './PaymentHistory'
export {
  PaymentStatus,
  PaymentTimeline,
  PaymentStatusBadge,
  PaymentProgress,
  type PaymentStatusType,
  type PaymentEvent,
  type PaymentData,
} from './PaymentStatus'
export { SettingsPage } from './SettingsPage'
export { HelpPage } from './HelpPage'

// Profile components
export {
  ProfilePage,
  EarningsCard,
  ReputationCard,
  TaskHistory,
  WithdrawalForm,
} from './profile'

// Camera/Evidence capture (legacy)
export { CameraCapture } from './CameraCapture'
export type { CaptureResult } from './CameraCapture'

// Evidence module (new structured components)
export * from './evidence'
export {
  EvidenceUpload as EvidenceUploadNew,
  CameraCapture as CameraCaptureNew,
  GPSCapture,
  EvidencePreview,
  EvidenceVerification,
} from './evidence'

// Map components
export {
  TaskMap,
  LocationPicker,
  TaskMarker,
  TaskCluster,
  NearbyTasks,
  useLocation,
  calculateDistance,
  isWithinRadius,
  getDistanceToTask,
  sortTasksByDistance,
  filterTasksByRadius,
  formatDistance,
  positionToLocation,
  locationToPosition,
  geocodeAddress,
  reverseGeocode,
} from './map'
export type {
  Position,
  LocationState,
  UseLocationOptions,
  TaskWithDistance,
} from './map'

// Notifications module
export {
  NotificationProvider,
  NotificationContext,
  useNotificationContext,
  NotificationBell,
  NotificationList,
  NotificationItem,
  Toast,
  ToastContainer,
} from './notifications'
export type {
  Notification,
  NotificationType,
  NotificationInsert,
  NotificationRow,
  NotificationFilter,
  NotificationPriority,
  NotificationContextValue,
  ToastType,
  ToastSeverity,
  ToastOptions,
  ToastAction,
  OnNotificationClick,
  NotificationComponentProps,
  NotificationPaginationParams,
  WebSocketStatus,
} from './notifications'

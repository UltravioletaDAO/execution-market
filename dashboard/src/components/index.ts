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
// Note: Legacy NotificationBell removed - use './notifications' directly
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
export { TxHashLink, type TxHashLinkProps } from './TxHashLink'
export {
  PaymentStatusBadge as PaymentStatusBadgeNew,
  type PaymentStatusBadgeProps as PaymentStatusBadgeNewProps,
} from './PaymentStatusBadge'

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

// Evidence module (import directly from './evidence' for full API)
export {
  EvidenceUpload as EvidenceUploadNew,
  CameraCapture as CameraCaptureNew,
  GPSCapture,
  EvidencePreview,
  EvidenceVerification,
} from './evidence'

// Map components - for better tree-shaking, import directly from './map'
export {
  TaskMap,
  LocationPicker,
  NearbyTasks,
  useLocation,
} from './map'
export type {
  Position,
  LocationState,
} from './map'

// Notifications - for full API, import directly from './notifications'
export {
  NotificationProvider,
  useNotificationContext,
  NotificationBell,
  Toast,
  ToastContainer,
} from './notifications'
export type {
  Notification,
  NotificationType,
} from './notifications'

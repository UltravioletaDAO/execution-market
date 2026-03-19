// Components barrel export — only re-export actively used components

export { TaskCard } from './TaskCard'
export { TaskList, CategoryFilter } from './TaskList'
export { TaskDetail } from './TaskDetail'
export { SubmissionForm } from './SubmissionForm'
export { GeofenceAlert, type GeofenceAlertProps } from './GeofenceAlert'
export { SkillSelector, type Skill } from './SkillSelector'
export { LanguageSwitcher, LanguageSwitcherDropdown } from './LanguageSwitcher'
export {
  PaymentStatus,
  PaymentTimeline,
  PaymentStatusBadge,
  PaymentProgress,
  type PaymentStatusType,
  type PaymentEvent,
  type PaymentData,
} from './PaymentStatus'
export { TxLink, TxHashLink, type TxLinkProps, type TxHashLinkProps } from './TxLink'

// Profile components
export {
  ProfilePage,
  EarningsCard,
  ReputationCard,
  TaskHistory,
  WithdrawalForm,
} from './profile'

// Evidence module
export {
  EvidenceUpload as EvidenceUploadNew,
  CameraCapture as CameraCaptureNew,
  GPSCapture,
  EvidencePreview,
  EvidenceVerification,
} from './evidence'

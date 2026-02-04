/**
 * Evidence Components
 *
 * Complete evidence upload system for Execution Market task verification.
 * Includes camera capture, GPS verification, and upload management.
 */

// Main upload component
export { EvidenceUpload, type EvidenceUploadProps, type UploadedEvidence, type EvidenceMetadata } from './EvidenceUpload'
export { default } from './EvidenceUpload'

// Camera capture component
export { CameraCapture, type CameraCaptureProps, type CapturedPhoto } from './CameraCapture'

// GPS capture component
export { GPSCapture, type GPSCaptureProps, type GPSPosition } from './GPSCapture'

// Evidence preview component
export { EvidencePreview, type EvidencePreviewProps, type EvidenceItem, type UploadStatus } from './EvidencePreview'

// Verification badges component
export { EvidenceVerification, type EvidenceVerificationProps, type EvidenceVerificationData } from './EvidenceVerification'

/**
 * EvidenceUpload Component
 *
 * Main upload component that orchestrates camera capture, GPS, and file management.
 * Features:
 * - Camera capture for photos (using device camera)
 * - File picker for existing photos
 * - GPS capture with accuracy indicator
 * - Timestamp display
 * - Preview of captured evidence
 * - Upload progress indicator
 * - Support multiple evidence items
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import exifr from 'exifr'
import { supabase } from '../../lib/supabase'
import type { EvidenceType } from '../../types/database'
import { CameraCapture, type CapturedPhoto } from './CameraCapture'
import { GPSCapture, type GPSPosition } from './GPSCapture'
import { EvidencePreview, type EvidenceItem, type UploadStatus } from './EvidencePreview'
import { EvidenceVerification, type EvidenceVerificationData } from './EvidenceVerification'
import { safeSrc } from '../../lib/safeHref'

// ============================================================================
// Types
// ============================================================================

export interface EvidenceMetadata {
  filename: string
  mimeType: string
  size: number
  timestamp: string
  captureTimestamp: string
  gps?: GPSPosition
  source: 'camera' | 'gallery' | 'unknown'
  deviceInfo: {
    userAgent: string
    platform: string
    vendor?: string
    model?: string
  }
  imageWidth?: number
  imageHeight?: number
}

export interface UploadedEvidence {
  id: string
  url: string
  path: string
  metadata: EvidenceMetadata
  evidenceType: EvidenceType
  verification?: EvidenceVerificationData
}

export interface EvidenceUploadProps {
  /** Task ID for organizing uploads */
  taskId: string
  /** Executor ID */
  executorId: string
  /** Required evidence types */
  requiredTypes: EvidenceType[]
  /** Optional evidence types */
  optionalTypes?: EvidenceType[]
  /** Callback when all required evidence is uploaded */
  onComplete: (evidence: UploadedEvidence[]) => void
  /** Callback when evidence is added */
  onEvidenceAdded?: (evidence: UploadedEvidence) => void
  /** Callback on error */
  onError?: (error: string) => void
  /** Maximum files allowed */
  maxFiles?: number
  /** Maximum file size in MB */
  maxSizeMB?: number
  /** Require camera-only (no gallery) */
  requireCamera?: boolean
  /** Require GPS for all evidence */
  requireGps?: boolean
  /** Task location for distance verification */
  taskLocation?: { lat: number; lng: number; radiusKm?: number }
  /** Additional CSS classes */
  className?: string
}

type ViewMode = 'capture' | 'camera' | 'preview' | 'list'

// ============================================================================
// Utilities
// ============================================================================

function generateId(): string {
  return `ev_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
}

function getDeviceInfo(): EvidenceMetadata['deviceInfo'] {
  const nav = navigator as Navigator & {
    userAgentData?: { platform?: string; brands?: Array<{ brand: string }> }
  }

  return {
    userAgent: navigator.userAgent,
    platform: nav.userAgentData?.platform || navigator.platform,
    vendor: navigator.vendor || undefined,
    model: nav.userAgentData?.brands?.[0]?.brand,
  }
}

async function blobToFile(blob: Blob, filename: string): Promise<File> {
  return new File([blob], filename, {
    type: blob.type,
    lastModified: Date.now(),
  })
}

/**
 * Extract GPS coordinates from image EXIF data.
 * Returns a GPSPosition if EXIF GPS is present, null otherwise.
 * Never throws — silently returns null on any failure (stripped metadata,
 * non-JPEG, permission issues, etc.).
 */
async function extractExifGps(file: File | Blob): Promise<GPSPosition | null> {
  try {
    const gps = await exifr.gps(file)
    if (gps?.latitude != null && gps?.longitude != null) {
      return {
        latitude: gps.latitude,
        longitude: gps.longitude,
        accuracy: 0, // EXIF does not carry accuracy — mark as unknown
        timestamp: Date.now(),
      }
    }
    return null
  } catch {
    // EXIF extraction can fail for many valid reasons (no EXIF, HEIC without
    // parser, corrupted metadata). This is a bonus feature — never crash.
    return null
  }
}

// ============================================================================
// Component
// ============================================================================

export function EvidenceUpload({
  taskId,
  executorId,
  requiredTypes,
  optionalTypes = [],
  onComplete,
  onEvidenceAdded,
  onError,
  maxFiles = 10,
  maxSizeMB = 50,
  requireCamera = true,
  requireGps = false,
  taskLocation,
  className = '',
}: EvidenceUploadProps) {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  // State
  const [viewMode, setViewMode] = useState<ViewMode>('capture')
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([])
  const [uploadedEvidence, setUploadedEvidence] = useState<UploadedEvidence[]>([])
  const [currentGps, setCurrentGps] = useState<GPSPosition | null>(null)
  const [currentEvidenceType, setCurrentEvidenceType] = useState<EvidenceType>(
    requiredTypes[0] || optionalTypes[0] || 'photo'
  )
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Get completed types
  const completedTypes = new Set(uploadedEvidence.map(e => e.evidenceType))
  const pendingRequired = requiredTypes.filter(t => !completedTypes.has(t))
  const allRequiredComplete = pendingRequired.length === 0

  // Calculate distance from task location
  const calculateDistance = useCallback((pos: GPSPosition): number | undefined => {
    if (!taskLocation) return undefined

    const R = 6371 // Earth radius in km
    const dLat = (taskLocation.lat - pos.latitude) * Math.PI / 180
    const dLon = (taskLocation.lng - pos.longitude) * Math.PI / 180
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(pos.latitude * Math.PI / 180) *
      Math.cos(taskLocation.lat * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return R * c * 1000 // Return meters
  }, [taskLocation])

  // Handle GPS position update
  const handleGpsUpdate = useCallback((position: GPSPosition | null) => {
    setCurrentGps(position)
  }, [])

  // Handle camera capture
  const handleCameraCapture = useCallback(async (photo: CapturedPhoto) => {
    const id = generateId()
    const timestamp = new Date()
    const filename = `evidence_${timestamp.toISOString().replace(/[:.]/g, '-')}.jpg`
    // Use original file when available (native camera capture preserves EXIF metadata).
    // Fall back to creating a File from the canvas blob (desktop getUserMedia — no EXIF).
    const file = photo.originalFile ?? await blobToFile(photo.blob, filename)

    // Extract EXIF GPS from the captured photo. Native camera captures on
    // mobile typically embed GPS in EXIF. Prefer it over browser geolocation.
    const exifGps = await extractExifGps(file)
    const resolvedGps = exifGps ?? currentGps ?? undefined

    if (exifGps && !currentGps) {
      setCurrentGps(exifGps)
    }

    // Calculate distance if task location provided (used later during verification)
    void (resolvedGps ? calculateDistance(resolvedGps) : undefined)

    // Map EvidenceType to EvidenceItem.type (limited set)
    const mapToPreviewType = (et: EvidenceType): EvidenceItem['type'] => {
      if (et === 'photo' || et === 'photo_geo' || et === 'video' || et === 'document') return et
      // Map other types to photo for preview purposes
      return 'photo'
    }

    const item: EvidenceItem = {
      id,
      type: mapToPreviewType(currentEvidenceType),
      file,
      dataUrl: photo.dataUrl,
      timestamp,
      gps: resolvedGps,
      uploadStatus: 'pending',
      metadata: {
        width: photo.width,
        height: photo.height,
        size: file.size,
        mimeType: file.type,
        captureSource: 'camera',
      },
    }

    setEvidenceItems(prev => [...prev, item])
    setViewMode('preview')
  }, [currentGps, currentEvidenceType, calculateDistance])

  // Handle camera cancel
  const handleCameraCancel = useCallback(() => {
    setViewMode('capture')
  }, [])

  // Handle file select (for gallery/existing photos)
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const newItems: EvidenceItem[] = []

    for (const file of Array.from(files)) {
      // Validate size
      if (file.size > maxSizeMB * 1024 * 1024) {
        setError(t('evidence.fileTooLarge', 'Archivo demasiado grande (max: {{max}}MB)', { max: maxSizeMB }))
        continue
      }

      // Validate type
      if (!file.type.startsWith('image/')) {
        setError(t('evidence.invalidType', 'Solo se permiten imagenes'))
        continue
      }

      const id = generateId()
      const dataUrl = await new Promise<string>((resolve) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result as string)
        reader.readAsDataURL(file)
      })

      // Get image dimensions
      const img = new Image()
      await new Promise<void>((resolve) => {
        img.onload = () => resolve()
        img.src = dataUrl
      })

      // Extract EXIF GPS from the image file (gallery photos often have it).
      // Prefer EXIF GPS over currentGps — it comes from the actual photo and
      // is more accurate than a separately-captured browser geolocation.
      const exifGps = await extractExifGps(file)

      // Fallback: if EXIF GPS is absent (iOS Safari strips it from gallery picks)
      // and GPSCapture hasn't resolved yet, try browser Geolocation API directly.
      let browserGpsFallback: GPSPosition | undefined
      if (!exifGps && !currentGps && 'geolocation' in navigator) {
        try {
          const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              enableHighAccuracy: true,
              timeout: 8000,
              maximumAge: 30000,
            })
          })
          browserGpsFallback = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            altitude: pos.coords.altitude,
            timestamp: pos.timestamp,
            source: 'browser_fallback' as const,
          }
          setCurrentGps(browserGpsFallback)
        } catch {
          // GPS fallback failed — continue without GPS
        }
      }

      const resolvedGps = exifGps ?? currentGps ?? browserGpsFallback ?? undefined

      // If EXIF gave us GPS that the GPSCapture component doesn't have yet,
      // propagate it so the UI shows the position badge immediately.
      if (exifGps && !currentGps) {
        setCurrentGps(exifGps)
      }

      // Map EvidenceType to EvidenceItem.type (limited set)
      const previewType: EvidenceItem['type'] =
        currentEvidenceType === 'photo' || currentEvidenceType === 'photo_geo' ||
        currentEvidenceType === 'video' || currentEvidenceType === 'document'
          ? currentEvidenceType : 'photo'

      newItems.push({
        id,
        type: previewType,
        file,
        dataUrl,
        timestamp: new Date(file.lastModified),
        gps: resolvedGps,
        uploadStatus: 'pending',
        metadata: {
          width: img.width,
          height: img.height,
          size: file.size,
          mimeType: file.type,
          captureSource: 'gallery',
        },
      })
    }

    if (newItems.length > 0) {
      setEvidenceItems(prev => [...prev, ...newItems])
      setViewMode('preview')
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [maxSizeMB, currentEvidenceType, currentGps, t])

  // Handle delete evidence
  const handleDelete = useCallback((id: string) => {
    setEvidenceItems(prev => prev.filter(item => item.id !== id))

    // Return to capture mode if no items left
    if (evidenceItems.length <= 1) {
      setViewMode('capture')
    }
  }, [evidenceItems.length])

  // Handle retake — use native file input (not getUserMedia camera)
  const handleRetake = useCallback((id: string) => {
    setEvidenceItems(prev => prev.filter(item => item.id !== id))
    setViewMode('capture')
  }, [])

  // Upload single evidence item
  const uploadItem = useCallback(async (item: EvidenceItem): Promise<UploadedEvidence | null> => {
    if (!item.file) return null

    try {
      // Update status
      setEvidenceItems(prev =>
        prev.map(i => i.id === item.id ? { ...i, uploadStatus: 'uploading' as UploadStatus, uploadProgress: 0 } : i)
      )

      // Generate unique path
      const timestamp = Date.now()
      const ext = item.file.name.split('.').pop() || 'jpg'
      const path = `${taskId}/${executorId}/${item.type}_${timestamp}.${ext}`

      // Upload to Supabase Storage
      const { error: uploadError } = await supabase.storage
        .from('evidence')
        .upload(path, item.file, {
          cacheControl: '31536000',
          upsert: false,
          contentType: item.file.type,
        })

      if (uploadError) throw uploadError

      // Update progress
      setEvidenceItems(prev =>
        prev.map(i => i.id === item.id ? { ...i, uploadProgress: 75 } : i)
      )

      // Get public URL
      const { data: urlData } = supabase.storage
        .from('evidence')
        .getPublicUrl(path)

      // Build metadata
      const metadata: EvidenceMetadata = {
        filename: item.file.name,
        mimeType: item.file.type,
        size: item.file.size,
        timestamp: new Date().toISOString(),
        captureTimestamp: item.timestamp.toISOString(),
        gps: item.gps,
        source: item.metadata?.captureSource || 'unknown',
        deviceInfo: getDeviceInfo(),
        imageWidth: item.metadata?.width,
        imageHeight: item.metadata?.height,
      }

      // Calculate verification data
      const distance = item.gps ? calculateDistance(item.gps) : undefined
      const verification: EvidenceVerificationData = {
        gps: item.gps ? {
          verified: true,
          position: item.gps,
          matchesTaskLocation: distance !== undefined && taskLocation?.radiusKm
            ? distance / 1000 <= taskLocation.radiusKm
            : undefined,
          distance,
          maxDistance: taskLocation?.radiusKm ? taskLocation.radiusKm * 1000 : undefined,
        } : undefined,
        timestamp: {
          verified: true,
          capturedAt: item.timestamp,
          withinDeadline: true,
          suspicious: false,
        },
        integrity: {
          verified: true,
          metadataIntact: true,
          suspiciousEdits: false,
        },
      }

      // Update status to success
      setEvidenceItems(prev =>
        prev.map(i => i.id === item.id ? { ...i, uploadStatus: 'success' as UploadStatus, uploadProgress: 100 } : i)
      )

      const uploaded: UploadedEvidence = {
        id: item.id,
        url: urlData.publicUrl,
        path,
        metadata,
        evidenceType: item.type,
        verification,
      }

      return uploaded
    } catch (err) {
      const message = err instanceof Error ? err.message : t('evidence.uploadError', 'Error al subir')

      setEvidenceItems(prev =>
        prev.map(i => i.id === item.id
          ? { ...i, uploadStatus: 'error' as UploadStatus, error: message }
          : i
        )
      )

      return null
    }
  }, [taskId, executorId, calculateDistance, taskLocation, t])

  // Upload all pending evidence
  const uploadAllEvidence = useCallback(async () => {
    const pendingItems = evidenceItems.filter(item => item.uploadStatus === 'pending')
    if (pendingItems.length === 0) return

    setIsUploading(true)
    setError(null)

    const newUploaded: UploadedEvidence[] = []

    for (const item of pendingItems) {
      const result = await uploadItem(item)
      if (result) {
        newUploaded.push(result)
        onEvidenceAdded?.(result)
      }
    }

    setUploadedEvidence(prev => [...prev, ...newUploaded])
    setIsUploading(false)

    // Check if all required types are now complete
    const allUploaded = [...uploadedEvidence, ...newUploaded]
    const completedTypes = new Set(allUploaded.map(e => e.evidenceType))
    const stillPending = requiredTypes.filter(t => !completedTypes.has(t))

    if (stillPending.length === 0) {
      onComplete(allUploaded)
    } else {
      // Switch to next required type
      setCurrentEvidenceType(stillPending[0])
      setViewMode('capture')
    }
  }, [evidenceItems, uploadItem, uploadedEvidence, requiredTypes, onComplete, onEvidenceAdded])

  // Auto-upload: trigger upload as soon as pending items exist (no manual click needed)
  useEffect(() => {
    const hasPending = evidenceItems.some(item => item.uploadStatus === 'pending')
    if (hasPending && !isUploading && viewMode === 'preview') {
      uploadAllEvidence()
    }
  }, [evidenceItems, isUploading, viewMode, uploadAllEvidence])

  // Handle retry
  const handleRetry = useCallback(async (id: string) => {
    const item = evidenceItems.find(i => i.id === id)
    if (!item) return

    const result = await uploadItem(item)
    if (result) {
      setUploadedEvidence(prev => [...prev, result])
      onEvidenceAdded?.(result)
    }
  }, [evidenceItems, uploadItem, onEvidenceAdded])

  // Render capture mode
  const renderCaptureMode = () => (
    <div className="space-y-4">
      {/* GPS Status — errors stay inside GPSCapture's own UI (has retry button).
           Only propagate upload errors to the parent form, not GPS permission errors. */}
      <GPSCapture
        onPositionChange={handleGpsUpdate}
        highAccuracy
        watchMode={requireGps || currentEvidenceType === 'photo_geo'}
        minAccuracy={taskLocation?.radiusKm ? taskLocation.radiusKm * 500 : undefined}
        showMap
        compact={false}
      />

      {/* Evidence type selector */}
      <div className="flex flex-wrap gap-2">
        {[...requiredTypes, ...optionalTypes].map((type) => {
          const isComplete = completedTypes.has(type)
          const isRequired = requiredTypes.includes(type)
          const isSelected = type === currentEvidenceType

          return (
            <button
              key={type}
              onClick={() => setCurrentEvidenceType(type)}
              disabled={isComplete}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isSelected
                  ? 'bg-blue-600 text-white'
                  : isComplete
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <span className="flex items-center gap-2">
                {isComplete && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
                {type.replace('_', ' ')}
                {isRequired && !isComplete && (
                  <span className="text-red-500">*</span>
                )}
              </span>
            </button>
          )
        })}
      </div>

      {/* Capture prompt */}
      <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-6">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {t('evidence.captureTitle', 'Capturar Evidencia')}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {currentEvidenceType === 'photo_geo'
              ? t('evidence.captureWithGps', 'Toma una foto con tu ubicacion GPS')
              : t('evidence.capturePhoto', 'Toma una foto como evidencia')
            }
          </p>

          {/* GPS status indicator */}
          {(requireGps || currentEvidenceType === 'photo_geo') && (
            <div className="mb-4">
              {currentGps ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-full text-sm">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                  </svg>
                  <span>{t('evidence.gpsReady', 'GPS listo')}</span>
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              ) : (
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-full text-sm animate-pulse">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  </svg>
                  <span>{t('evidence.gpsWaiting', 'Esperando GPS...')}</span>
                </div>
              )}
            </div>
          )}

          {/* Action buttons — native inputs for mobile compatibility */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {/* Take Photo: opens native camera on iOS/Android */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              </svg>
              {t('evidence.openCamera', 'Tomar Foto')}
            </button>

            {/* Select File: opens gallery picker (no capture attr) */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple={maxFiles > 1}
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              {t('evidence.selectFile', 'Elegir Archivo')}
            </button>
          </div>

          {/* Camera-only notice */}
          {requireCamera && (
            <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
              {t('evidence.cameraOnlyNotice', 'Solo se aceptan fotos tomadas en el momento')}
            </p>
          )}
        </div>
      </div>

      {/* Uploaded evidence list */}
      {uploadedEvidence.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('evidence.uploaded', 'Evidencia subida')} ({uploadedEvidence.length})
          </h4>
          <div className="space-y-2">
            {uploadedEvidence.map((ev) => (
              <div
                key={ev.id}
                className="flex items-center gap-3 p-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg"
              >
                <img
                  src={safeSrc(ev.url)}
                  alt=""
                  className="w-10 h-10 rounded object-cover"
                />
                <div className="flex-1">
                  <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
                    {ev.evidenceType.replace('_', ' ')}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {new Date(ev.metadata.captureTimestamp).toLocaleTimeString('es', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
                <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress indicator */}
      {!allRequiredComplete && (
        <div className="text-center text-sm text-gray-600 dark:text-gray-400">
          <span>
            {t('evidence.progress', '{{done}} de {{total}} requeridas', {
              done: uploadedEvidence.filter(e => requiredTypes.includes(e.evidenceType)).length,
              total: requiredTypes.length,
            })}
          </span>
        </div>
      )}

      {/* Complete button */}
      {allRequiredComplete && uploadedEvidence.length > 0 && (
        <button
          onClick={() => onComplete(uploadedEvidence)}
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-xl transition-colors"
        >
          {t('evidence.complete', 'Completar Envio')}
        </button>
      )}
    </div>
  )

  // Render camera mode
  const renderCameraMode = () => (
    <CameraCapture
      onCapture={handleCameraCapture}
      onCancel={handleCameraCancel}
      onError={(err) => {
        setError(err)
        onError?.(err)
      }}
      preferredCamera="environment"
      allowSwitch
      enableFlash={false}
      quality={0.92}
      aspectRatio="4:3"
    />
  )

  // Render preview mode — show ALL items (including uploaded ones)
  const renderPreviewMode = () => {
    return (
      <div className="space-y-4">
        {/* Preview list */}
        <div className="space-y-3">
          {evidenceItems.map((item) => (
            <EvidencePreview
              key={item.id}
              evidence={item}
              onDelete={handleDelete}
              onRetake={handleRetake}
              onRetry={handleRetry}
              showDetails
              disabled={isUploading}
            />
          ))}
        </div>

        {/* Verification preview */}
        {evidenceItems[0]?.gps && (
          <EvidenceVerification
            verification={{
              gps: {
                verified: true,
                position: evidenceItems[0].gps,
                matchesTaskLocation: taskLocation
                  ? calculateDistance(evidenceItems[0].gps)! / 1000 <= (taskLocation.radiusKm || 1)
                  : undefined,
                distance: calculateDistance(evidenceItems[0].gps),
                maxDistance: taskLocation?.radiusKm ? taskLocation.radiusKm * 1000 : undefined,
              },
              timestamp: {
                verified: true,
                capturedAt: evidenceItems[0].timestamp,
                withinDeadline: true,
              },
            }}
            mode="badges"
          />
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => setViewMode('capture')}
            disabled={isUploading}
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {t('evidence.addMore', 'Agregar mas')}
          </button>
          <button
            onClick={uploadAllEvidence}
            disabled={isUploading || evidenceItems.filter(i => i.uploadStatus === 'pending').length === 0}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('evidence.uploading', 'Subiendo...')}
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                {t('evidence.uploadAll', 'Subir Evidencia')}
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  // Main render
  return (
    <div className={className}>
      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700 dark:hover:text-red-300"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* View modes */}
      {viewMode === 'capture' && renderCaptureMode()}
      {viewMode === 'camera' && renderCameraMode()}
      {viewMode === 'preview' && renderPreviewMode()}
    </div>
  )
}

// Export types
export type { GPSPosition } from './GPSCapture'
export type { CapturedPhoto } from './CameraCapture'
export type { EvidenceItem, UploadStatus } from './EvidencePreview'
export type { EvidenceVerificationData } from './EvidenceVerification'

export default EvidenceUpload

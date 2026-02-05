/**
 * EvidenceUpload - Evidence capture and upload component (NOW-046 to NOW-048)
 *
 * Features:
 * - Camera capture (photo/video) - enforces camera-only, no gallery
 * - EXIF extraction (GPS, timestamp, device info)
 * - Upload to Supabase Storage with progress tracking
 * - Mobile-responsive with PWA support
 * - Geolocation verification for physical presence tasks
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import type { EvidenceType } from '../types/database'

// Types
interface GPSCoordinates {
  latitude: number
  longitude: number
  accuracy?: number
  altitude?: number
  altitudeAccuracy?: number
  heading?: number
  speed?: number
}

interface EvidenceMetadata {
  filename: string
  mimeType: string
  size: number
  timestamp: string
  captureTimestamp: string // When photo was actually taken (from EXIF or capture time)
  gps?: GPSCoordinates
  exifGps?: GPSCoordinates // GPS from EXIF (if different from live GPS)
  source: 'camera' | 'gallery' | 'unknown'
  deviceInfo: {
    userAgent: string
    platform: string
    vendor?: string
    model?: string
  }
  imageWidth?: number
  imageHeight?: number
  orientation?: number
  make?: string  // Camera manufacturer
  model?: string // Camera model
}

interface UploadedEvidence {
  url: string
  path: string
  metadata: EvidenceMetadata
  evidenceType: EvidenceType
}

interface EvidenceUploadProps {
  taskId: string
  executorId: string
  evidenceType: EvidenceType
  onUpload: (evidence: UploadedEvidence) => void
  onError?: (error: string) => void
  required?: boolean
  label?: string
  acceptTypes?: string[]
  maxSizeMB?: number
  requireCamera?: boolean
  requireGps?: boolean // For photo_geo evidence type
  maxGpsAge?: number   // Max age of GPS reading in ms (default 30s)
}

// EXIF tag constants
const EXIF_TAGS = {
  GPS_LATITUDE: 0x0002,
  GPS_LATITUDE_REF: 0x0001,
  GPS_LONGITUDE: 0x0004,
  GPS_LONGITUDE_REF: 0x0003,
  GPS_ALTITUDE: 0x0006,
  GPS_ALTITUDE_REF: 0x0005,
  DATE_TIME_ORIGINAL: 0x9003,
  MAKE: 0x010f,
  MODEL: 0x0110,
  ORIENTATION: 0x0112,
  IMAGE_WIDTH: 0xa002,
  IMAGE_HEIGHT: 0xa003,
} as const

// Parse EXIF data from JPEG buffer
function parseExifFromBuffer(buffer: ArrayBuffer): {
  gps?: GPSCoordinates
  timestamp?: string
  make?: string
  model?: string
  orientation?: number
  imageWidth?: number
  imageHeight?: number
} {
  const view = new DataView(buffer)
  const result: ReturnType<typeof parseExifFromBuffer> = {}

  // Check for JPEG magic bytes
  if (view.getUint16(0) !== 0xFFD8) {
    return result
  }

  let offset = 2
  while (offset < buffer.byteLength) {
    if (view.getUint8(offset) !== 0xFF) break

    const marker = view.getUint8(offset + 1)

    // APP1 marker (EXIF)
    if (marker === 0xE1) {
      const exifOffset = offset + 4

      // Check for "Exif\0\0" header
      if (view.getUint32(exifOffset) === 0x45786966 && view.getUint16(exifOffset + 4) === 0x0000) {
        const tiffOffset = exifOffset + 6
        const isLittleEndian = view.getUint16(tiffOffset) === 0x4949 // "II"

        // Parse IFD0
        const ifd0Offset = tiffOffset + view.getUint32(tiffOffset + 4, isLittleEndian)
        const ifd0Entries = view.getUint16(ifd0Offset, isLittleEndian)

        for (let i = 0; i < ifd0Entries; i++) {
          const entryOffset = ifd0Offset + 2 + i * 12
          const tag = view.getUint16(entryOffset, isLittleEndian)
          const type = view.getUint16(entryOffset + 2, isLittleEndian)
          const count = view.getUint32(entryOffset + 4, isLittleEndian)

          if (tag === EXIF_TAGS.MAKE && type === 2) {
            const valueOffset = tiffOffset + view.getUint32(entryOffset + 8, isLittleEndian)
            result.make = readString(view, valueOffset, count)
          } else if (tag === EXIF_TAGS.MODEL && type === 2) {
            const valueOffset = tiffOffset + view.getUint32(entryOffset + 8, isLittleEndian)
            result.model = readString(view, valueOffset, count)
          } else if (tag === EXIF_TAGS.ORIENTATION && type === 3) {
            result.orientation = view.getUint16(entryOffset + 8, isLittleEndian)
          }
        }

        // Note: Full GPS parsing would require finding GPS IFD pointer and parsing it
        // For MVP, we rely on live GPS which is more reliable on mobile
      }

      break
    }

    // Skip to next segment
    const segmentLength = view.getUint16(offset + 2)
    offset += 2 + segmentLength
  }

  return result
}

function readString(view: DataView, offset: number, length: number): string {
  let result = ''
  for (let i = 0; i < length - 1; i++) {
    const char = view.getUint8(offset + i)
    if (char === 0) break
    result += String.fromCharCode(char)
  }
  return result.trim()
}

// Extract EXIF data with enhanced detection
async function extractExifData(file: File): Promise<{
  gps?: GPSCoordinates
  timestamp?: string
  source: 'camera' | 'gallery' | 'unknown'
  make?: string
  model?: string
  orientation?: number
  imageWidth?: number
  imageHeight?: number
}> {
  return new Promise((resolve) => {
    const reader = new FileReader()

    reader.onload = () => {
      const buffer = reader.result as ArrayBuffer
      const exifData = parseExifFromBuffer(buffer)

      // Determine if this is likely a fresh camera capture
      const timeSinceModified = Date.now() - file.lastModified
      const isRecentFile = timeSinceModified < 120000 // 2 minutes

      // Camera photos typically have standard naming patterns
      const cameraPatterns = [
        /^IMG_\d+/i,           // iOS, Samsung
        /^DCIM/i,              // Standard camera folder
        /^DSC_\d+/i,           // Nikon
        /^P\d{7}/i,            // Canon PowerShot
        /^DSCN\d+/i,           // Nikon Coolpix
        /^\d{8}_\d{6}/,        // Android timestamp format
        /^PXL_\d+/i,           // Google Pixel
        /^Screenshot/i,        // Screenshots (reject)
      ]

      const isScreenshot = /^Screenshot/i.test(file.name)
      const hasCameraPattern = cameraPatterns.some(p => p.test(file.name)) && !isScreenshot
      const hasExifMake = !!exifData.make

      // Source determination logic
      let source: 'camera' | 'gallery' | 'unknown' = 'unknown'

      if (isRecentFile && (hasCameraPattern || hasExifMake)) {
        source = 'camera'
      } else if (isScreenshot || (!isRecentFile && !hasCameraPattern)) {
        source = 'gallery'
      }

      resolve({
        ...exifData,
        source,
        timestamp: new Date(file.lastModified).toISOString(),
      })
    }

    reader.onerror = () => {
      resolve({ source: 'unknown' })
    }

    // Read first 64KB for EXIF header
    reader.readAsArrayBuffer(file.slice(0, 65536))
  })
}

// Get current GPS position with enhanced accuracy
function getCurrentPosition(highAccuracy = true, maxAge = 30000): Promise<GPSCoordinates | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      console.warn('[EvidenceUpload] Geolocation not supported')
      resolve(null)
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          altitude: position.coords.altitude ?? undefined,
          altitudeAccuracy: position.coords.altitudeAccuracy ?? undefined,
          heading: position.coords.heading ?? undefined,
          speed: position.coords.speed ?? undefined,
        })
      },
      (error) => {
        console.warn('[EvidenceUpload] GPS error:', error.message)
        resolve(null)
      },
      {
        enableHighAccuracy: highAccuracy,
        timeout: highAccuracy ? 15000 : 10000,
        maximumAge: maxAge,
      }
    )
  })
}

// Watch GPS position for continuous updates
function watchPosition(
  onUpdate: (coords: GPSCoordinates) => void,
  onError?: (error: GeolocationPositionError) => void
): number | null {
  if (!navigator.geolocation) return null

  return navigator.geolocation.watchPosition(
    (position) => {
      onUpdate({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        altitude: position.coords.altitude ?? undefined,
        altitudeAccuracy: position.coords.altitudeAccuracy ?? undefined,
        heading: position.coords.heading ?? undefined,
        speed: position.coords.speed ?? undefined,
      })
    },
    onError,
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 5000, // More frequent updates while camera is active
    }
  )
}

// Get device info
function getDeviceInfo(): EvidenceMetadata['deviceInfo'] {
  const nav = navigator as Navigator & { userAgentData?: { platform?: string; brands?: Array<{ brand: string }> } }

  return {
    userAgent: navigator.userAgent,
    platform: nav.userAgentData?.platform || navigator.platform,
    vendor: navigator.vendor || undefined,
    model: nav.userAgentData?.brands?.[0]?.brand,
  }
}

// Progress stages for upload
type UploadStage = 'preparing' | 'validating' | 'uploading' | 'finalizing' | 'complete'

const PROGRESS_STAGES = ['preparing', 'validating', 'uploading', 'finalizing'] as const
type ProgressStage = (typeof PROGRESS_STAGES)[number]

function getProgressStageIndex(stage: UploadStage): number {
  if (stage === 'complete') return PROGRESS_STAGES.length
  return PROGRESS_STAGES.indexOf(stage as ProgressStage)
}

const UPLOAD_STAGE_LABELS: Record<UploadStage, string> = {
  preparing: 'Preparando...',
  validating: 'Validando evidencia...',
  uploading: 'Subiendo archivo...',
  finalizing: 'Finalizando...',
  complete: 'Completado',
}

export function EvidenceUpload({
  taskId,
  executorId,
  evidenceType,
  onUpload,
  onError,
  required = false,
  label,
  acceptTypes = ['image/jpeg', 'image/png', 'video/mp4'],
  maxSizeMB = 50,
  requireCamera = true,
  requireGps = false,
  maxGpsAge = 30000,
}: EvidenceUploadProps) {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const nativeInputRef = useRef<HTMLInputElement>(null) // Native capture input for mobile
  const videoRef = useRef<HTMLVideoElement>(null)
  const gpsWatchRef = useRef<number | null>(null)
  const captureTimeRef = useRef<string | null>(null)

  const [mode, setMode] = useState<'idle' | 'camera' | 'preview' | 'uploading'>('idle')
  const [capturedFile, setCapturedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadStage, setUploadStage] = useState<UploadStage>('preparing')
  const [error, setError] = useState<string | null>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [gpsPosition, setGpsPosition] = useState<GPSCoordinates | null>(null)
  const [gpsTimestamp, setGpsTimestamp] = useState<number | null>(null)
  const [gpsError, setGpsError] = useState<string | null>(null)
  const [isMobile, setIsMobile] = useState(false)
  const currentStageIndex = getProgressStageIndex(uploadStage)

  // Detect mobile device
  useEffect(() => {
    const checkMobile = () => {
      const mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
      setIsMobile(mobile)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
      if (gpsWatchRef.current !== null) {
        navigator.geolocation.clearWatch(gpsWatchRef.current)
      }
    }
  }, [stream, previewUrl])

  // Get GPS on mount and watch for updates if required
  useEffect(() => {
    const initGps = async () => {
      const position = await getCurrentPosition(true, maxGpsAge)
      if (position) {
        setGpsPosition(position)
        setGpsTimestamp(Date.now())
      } else if (requireGps) {
        setGpsError(t('evidence.gpsRequired', 'GPS requerido para esta tarea'))
      }
    }

    initGps()

    // If GPS is required, watch position
    if (requireGps || evidenceType === 'photo_geo') {
      gpsWatchRef.current = watchPosition(
        (coords) => {
          setGpsPosition(coords)
          setGpsTimestamp(Date.now())
          setGpsError(null)
        },
        (error) => {
          console.warn('[EvidenceUpload] GPS watch error:', error.message)
          setGpsError(t('evidence.gpsError', 'No se pudo obtener ubicacion'))
        }
      )
    }

    return () => {
      if (gpsWatchRef.current !== null) {
        navigator.geolocation.clearWatch(gpsWatchRef.current)
        gpsWatchRef.current = null
      }
    }
  }, [requireGps, evidenceType, maxGpsAge, t])

  // Start camera - with fallback to native input on mobile
  const startCamera = useCallback(async () => {
    try {
      setError(null)

      // On mobile, prefer native camera input for better UX
      if (isMobile && nativeInputRef.current) {
        nativeInputRef.current.click()
        return
      }

      // MediaDevices camera for desktop
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' }, // Back camera preferred
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
        },
      })

      setStream(mediaStream)
      setMode('camera')

      // Refresh GPS when opening camera
      getCurrentPosition(true, maxGpsAge).then((pos) => {
        if (pos) {
          setGpsPosition(pos)
          setGpsTimestamp(Date.now())
        }
      })

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
        // Wait for video to be ready
        await new Promise<void>((resolve) => {
          if (videoRef.current) {
            videoRef.current.onloadedmetadata = () => resolve()
          }
        })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('evidence.cameraError')
      console.error('[EvidenceUpload] Camera error:', err)

      // Fallback to native input
      if (nativeInputRef.current) {
        setError(t('evidence.cameraFallback', 'Usando camara nativa...'))
        nativeInputRef.current.click()
      } else {
        setError(message)
        onError?.(message)
      }
    }
  }, [t, onError, isMobile, maxGpsAge])

  // Stop camera
  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setMode('idle')
  }, [stream])

  // Capture photo from camera
  const capturePhoto = useCallback(async () => {
    if (!videoRef.current || !stream) return

    // Check GPS requirement before capture
    if (requireGps && !gpsPosition) {
      setError(t('evidence.waitingForGps', 'Esperando senal GPS...'))
      onError?.(t('evidence.gpsRequired'))
      return
    }

    // Check GPS age
    if (requireGps && gpsTimestamp && (Date.now() - gpsTimestamp) > maxGpsAge) {
      setError(t('evidence.gpsStale', 'GPS desactualizado, esperando...'))
      // Try to get fresh GPS
      const freshPos = await getCurrentPosition(true, 5000)
      if (freshPos) {
        setGpsPosition(freshPos)
        setGpsTimestamp(Date.now())
      } else {
        onError?.(t('evidence.gpsStale'))
        return
      }
    }

    const video = videoRef.current
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.drawImage(video, 0, 0)

    // Record capture time
    captureTimeRef.current = new Date().toISOString()

    // Convert to blob with high quality
    canvas.toBlob((blob) => {
      if (!blob) return

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      const file = new File([blob], `evidence_${timestamp}.jpg`, {
        type: 'image/jpeg',
        lastModified: Date.now(),
      })

      setCapturedFile(file)
      setPreviewUrl(URL.createObjectURL(blob))
      setMode('preview')
      stopCamera()
    }, 'image/jpeg', 0.92) // High quality JPEG
  }, [stream, stopCamera, requireGps, gpsPosition, gpsTimestamp, maxGpsAge, t, onError])

  // Handle file selection (for native camera input and fallback)
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Record capture time for native input
    captureTimeRef.current = new Date().toISOString()

    // Validate size
    if (file.size > maxSizeMB * 1024 * 1024) {
      const message = t('evidence.fileTooLarge', { max: maxSizeMB })
      setError(message)
      onError?.(message)
      return
    }

    // Validate type
    if (!acceptTypes.some(type => file.type.startsWith(type.replace('/*', '')))) {
      const message = t('evidence.invalidFileType')
      setError(message)
      onError?.(message)
      return
    }

    // Check GPS requirement
    if (requireGps && !gpsPosition) {
      // Try one more time to get GPS
      const freshPos = await getCurrentPosition(true, 5000)
      if (freshPos) {
        setGpsPosition(freshPos)
        setGpsTimestamp(Date.now())
      } else {
        const message = t('evidence.gpsRequired', 'GPS requerido para esta tarea')
        setError(message)
        onError?.(message)
        return
      }
    }

    // Check if from camera (if required)
    if (requireCamera) {
      const exif = await extractExifData(file)

      // For native camera input (capture="environment"), source should be recent
      // Allow 'unknown' if file was just created (native camera)
      const timeSinceModified = Date.now() - file.lastModified
      const isRecentCapture = timeSinceModified < 30000 // 30 seconds

      if (exif.source === 'gallery' && !isRecentCapture) {
        const message = t('evidence.cameraOnly', 'Solo se permiten fotos de la camara')
        setError(message)
        onError?.(message)
        // Reset the input
        e.target.value = ''
        return
      }
    }

    setCapturedFile(file)
    setPreviewUrl(URL.createObjectURL(file))
    setMode('preview')
    setError(null)
  }, [maxSizeMB, acceptTypes, requireCamera, requireGps, gpsPosition, t, onError])

  // Upload evidence with progress tracking
  const uploadEvidence = useCallback(async () => {
    if (!capturedFile) return

    setMode('uploading')
    setUploadProgress(0)
    setUploadStage('preparing')
    setError(null)

    try {
      // Stage 1: Preparing
      setUploadStage('preparing')
      setUploadProgress(5)

      // Get EXIF data
      const exif = await extractExifData(capturedFile)

      // Stage 2: Validating
      setUploadStage('validating')
      setUploadProgress(15)

      // Build comprehensive metadata
      const metadata: EvidenceMetadata = {
        filename: capturedFile.name,
        mimeType: capturedFile.type,
        size: capturedFile.size,
        timestamp: new Date().toISOString(),
        captureTimestamp: captureTimeRef.current || exif.timestamp || new Date().toISOString(),
        gps: gpsPosition || undefined,
        exifGps: exif.gps,
        source: exif.source,
        deviceInfo: getDeviceInfo(),
        imageWidth: exif.imageWidth,
        imageHeight: exif.imageHeight,
        orientation: exif.orientation,
        make: exif.make,
        model: exif.model,
      }

      // Validate GPS for geo evidence types
      if ((requireGps || evidenceType === 'photo_geo') && !metadata.gps) {
        throw new Error(t('evidence.gpsRequired', 'GPS requerido para esta tarea'))
      }

      // Generate unique path with evidence type
      const timestamp = Date.now()
      const ext = capturedFile.name.split('.').pop() || 'jpg'
      const path = `${taskId}/${executorId}/${evidenceType}_${timestamp}.${ext}`

      // Stage 3: Uploading
      setUploadStage('uploading')
      setUploadProgress(25)

      const { error: uploadError } = await supabase.storage
        .from('evidence')
        .upload(path, capturedFile, {
          cacheControl: '31536000', // 1 year cache
          upsert: false,
          contentType: capturedFile.type,
        })

      if (uploadError) throw uploadError

      setUploadProgress(75)

      // Stage 4: Finalizing
      setUploadStage('finalizing')

      // Get public URL
      const { data: urlData } = supabase.storage
        .from('evidence')
        .getPublicUrl(path)

      setUploadProgress(90)

      // Store metadata in database (if you have a separate evidence_metadata table)
      // For MVP, metadata is embedded in the uploaded evidence object

      setUploadProgress(100)
      setUploadStage('complete')

      const uploadedEvidence: UploadedEvidence = {
        url: urlData.publicUrl,
        path,
        metadata,
        evidenceType,
      }

      // Brief delay to show completion
      await new Promise(resolve => setTimeout(resolve, 300))

      onUpload(uploadedEvidence)

      // Reset state
      setCapturedFile(null)
      captureTimeRef.current = null
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
      setMode('idle')
    } catch (err) {
      const message = err instanceof Error ? err.message : t('evidence.uploadError')
      console.error('[EvidenceUpload] Upload error:', err)
      setError(message)
      onError?.(message)
      setMode('preview')
    }
  }, [capturedFile, taskId, executorId, evidenceType, gpsPosition, requireGps, previewUrl, onUpload, onError, t])

  // Discard captured evidence
  const discardEvidence = useCallback(() => {
    setCapturedFile(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setMode('idle')
    setError(null)
  }, [previewUrl])

  // Render based on mode
  return (
    <div className="space-y-4">
      {/* Hidden native camera input for mobile */}
      <input
        ref={nativeInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileSelect}
        className="hidden"
        aria-hidden="true"
      />

      {/* Label */}
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label} {required && <span className="text-red-500">*</span>}
          {(requireGps || evidenceType === 'photo_geo') && (
            <span className="ml-2 text-xs text-blue-600">
              ({t('evidence.requiresLocation', 'requiere ubicacion')})
            </span>
          )}
        </label>
      )}

      {/* GPS Error */}
      {gpsError && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{gpsError}</span>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Idle state - show capture options */}
      {mode === 'idle' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 touch-manipulation">
          <div className="text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p className="mt-2 text-sm text-gray-600">
              {t('evidence.capturePrompt', 'Captura evidencia con la camara')}
            </p>

            {/* GPS Status indicator */}
            <div className="mt-2 flex items-center justify-center gap-2">
              {gpsPosition ? (
                <div className="flex items-center gap-1 text-xs text-green-600">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                  </svg>
                  <span>
                    {gpsPosition.latitude.toFixed(4)}, {gpsPosition.longitude.toFixed(4)}
                  </span>
                  {gpsPosition.accuracy && (
                    <span className="text-gray-400">
                      (+/- {gpsPosition.accuracy.toFixed(0)}m)
                    </span>
                  )}
                </div>
              ) : (requireGps || evidenceType === 'photo_geo') ? (
                <div className="flex items-center gap-1 text-xs text-amber-600">
                  <svg className="w-4 h-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  </svg>
                  <span>{t('evidence.acquiringGps', 'Obteniendo ubicacion...')}</span>
                </div>
              ) : null}
            </div>
          </div>

          <div className="mt-4 flex flex-col sm:flex-row gap-2 justify-center">
            {/* Camera button - main action */}
            <button
              type="button"
              onClick={startCamera}
              disabled={requireGps && !gpsPosition}
              className={`inline-flex items-center justify-center px-6 py-3 text-sm font-medium rounded-lg transition-colors touch-manipulation ${
                requireGps && !gpsPosition
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
              }`}
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              </svg>
              {t('evidence.openCamera', 'Tomar Foto')}
            </button>

            {/* File input fallback (hidden if camera-only) */}
            {!requireCamera && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={acceptTypes.join(',')}
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors touch-manipulation"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {t('evidence.selectFile', 'Seleccionar Archivo')}
                </button>
              </>
            )}
          </div>

          {/* Camera-only notice */}
          {requireCamera && (
            <p className="mt-3 text-xs text-center text-gray-400">
              {t('evidence.cameraOnlyNotice', 'Solo se aceptan fotos tomadas en el momento')}
            </p>
          )}
        </div>
      )}

      {/* Camera mode */}
      {mode === 'camera' && (
        <div className="relative rounded-lg overflow-hidden bg-black touch-manipulation">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full aspect-[4/3] sm:aspect-video object-cover"
          />

          {/* Camera controls */}
          <div className="absolute bottom-0 inset-x-0 p-4 pb-6 bg-gradient-to-t from-black/80 to-transparent">
            <div className="flex items-center justify-center gap-6">
              {/* Cancel */}
              <button
                type="button"
                onClick={stopCamera}
                className="p-3 bg-white/20 text-white rounded-full hover:bg-white/30 active:bg-white/40 transition-colors touch-manipulation"
                aria-label={t('common.cancel', 'Cancelar')}
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              {/* Capture button - larger for mobile */}
              <button
                type="button"
                onClick={capturePhoto}
                disabled={requireGps && !gpsPosition}
                className={`p-5 rounded-full transition-all touch-manipulation active:scale-95 ${
                  requireGps && !gpsPosition
                    ? 'bg-gray-400'
                    : 'bg-white hover:bg-gray-100 active:bg-gray-200'
                }`}
                aria-label={t('evidence.capture', 'Capturar')}
              >
                <div className={`w-10 h-10 rounded-full border-4 ${
                  requireGps && !gpsPosition ? 'border-gray-500' : 'border-blue-600'
                }`} />
              </button>

              {/* Placeholder for symmetry */}
              <div className="w-12 h-12" />
            </div>
          </div>

          {/* Top bar with GPS indicator */}
          <div className="absolute top-0 inset-x-0 p-3 bg-gradient-to-b from-black/60 to-transparent">
            <div className="flex items-center justify-between">
              {/* GPS status */}
              {gpsPosition ? (
                <div className="px-2 py-1 bg-green-500/80 text-white text-xs rounded-full flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                  </svg>
                  <span>GPS OK</span>
                  {gpsPosition.accuracy && gpsPosition.accuracy < 50 && (
                    <svg className="w-3 h-3 ml-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              ) : (requireGps || evidenceType === 'photo_geo') ? (
                <div className="px-2 py-1 bg-amber-500/80 text-white text-xs rounded-full flex items-center gap-1 animate-pulse">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  </svg>
                  <span>{t('evidence.gpsLoading', 'GPS...')}</span>
                </div>
              ) : (
                <div />
              )}

              {/* Evidence type badge */}
              <div className="px-2 py-1 bg-black/60 text-white text-xs rounded-full">
                {evidenceType === 'photo_geo' ? 'Foto + GPS' : evidenceType}
              </div>
            </div>
          </div>

          {/* GPS warning if required but not available */}
          {requireGps && !gpsPosition && (
            <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 text-center p-4">
              <div className="inline-block bg-amber-500/90 text-white px-4 py-2 rounded-lg text-sm">
                {t('evidence.waitingForGps', 'Esperando senal GPS...')}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Preview mode */}
      {mode === 'preview' && previewUrl && (
        <div className="space-y-4">
          {/* Preview image with metadata overlay */}
          <div className="relative rounded-lg overflow-hidden bg-gray-100">
            <img
              src={previewUrl}
              alt={t('evidence.preview', 'Vista previa')}
              className="w-full max-h-[60vh] object-contain"
            />

            {/* Metadata overlay */}
            <div className="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/70 to-transparent">
              <div className="flex flex-wrap items-center gap-2 text-xs text-white">
                {/* GPS badge */}
                {gpsPosition && (
                  <div className="flex items-center gap-1 bg-green-500/80 px-2 py-1 rounded-full">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                    </svg>
                    <span>{gpsPosition.latitude.toFixed(4)}, {gpsPosition.longitude.toFixed(4)}</span>
                  </div>
                )}

                {/* Timestamp badge */}
                {captureTimeRef.current && (
                  <div className="flex items-center gap-1 bg-black/50 px-2 py-1 rounded-full">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>
                      {new Date(captureTimeRef.current).toLocaleTimeString('es', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}

                {/* File size badge */}
                {capturedFile && (
                  <div className="bg-black/50 px-2 py-1 rounded-full">
                    {(capturedFile.size / 1024 / 1024).toFixed(1)} MB
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Detailed metadata (collapsible on mobile) */}
          {capturedFile && (
            <details className="text-xs text-gray-500 bg-gray-50 rounded-lg p-3">
              <summary className="cursor-pointer font-medium text-gray-700">
                {t('evidence.viewDetails', 'Ver detalles')}
              </summary>
              <div className="mt-2 space-y-1 pl-2 border-l-2 border-gray-200">
                <p><span className="font-medium">{t('evidence.filename', 'Archivo')}:</span> {capturedFile.name}</p>
                <p><span className="font-medium">{t('evidence.size', 'Tamano')}:</span> {(capturedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                <p><span className="font-medium">{t('evidence.type', 'Tipo')}:</span> {capturedFile.type}</p>
                {gpsPosition && (
                  <>
                    <p><span className="font-medium">Latitud:</span> {gpsPosition.latitude.toFixed(6)}</p>
                    <p><span className="font-medium">Longitud:</span> {gpsPosition.longitude.toFixed(6)}</p>
                    {gpsPosition.accuracy && (
                      <p><span className="font-medium">{t('evidence.gpsAccuracy', 'Precision')}:</span> +/- {gpsPosition.accuracy.toFixed(0)} m</p>
                    )}
                    {gpsPosition.altitude && (
                      <p><span className="font-medium">{t('evidence.altitude', 'Altitud')}:</span> {gpsPosition.altitude.toFixed(0)} m</p>
                    )}
                  </>
                )}
                {captureTimeRef.current && (
                  <p><span className="font-medium">{t('evidence.capturedAt', 'Capturado')}:</span> {new Date(captureTimeRef.current).toLocaleString('es')}</p>
                )}
              </div>
            </details>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={discardEvidence}
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 active:bg-gray-100 transition-colors touch-manipulation"
            >
              {t('evidence.retake', 'Volver a tomar')}
            </button>
            <button
              type="button"
              onClick={uploadEvidence}
              className="flex-1 px-4 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors touch-manipulation flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {t('evidence.upload', 'Subir Evidencia')}
            </button>
          </div>
        </div>
      )}

      {/* Uploading mode - Enhanced progress with stages */}
      {mode === 'uploading' && (
        <div className="border border-gray-200 rounded-lg p-6 bg-white">
          <div className="text-center">
            {/* Progress circle */}
            <div className="w-20 h-20 mx-auto mb-4 relative">
              {uploadStage === 'complete' ? (
                // Success checkmark
                <div className="w-full h-full rounded-full bg-green-100 flex items-center justify-center">
                  <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              ) : (
                // Spinning loader with progress ring
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  {/* Background circle */}
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="#E5E7EB"
                    strokeWidth="8"
                  />
                  {/* Progress circle */}
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="#2563EB"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={`${uploadProgress * 2.83} 283`}
                    className="transition-all duration-300"
                  />
                </svg>
              )}

              {/* Percentage in center */}
              {uploadStage !== 'complete' && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-semibold text-blue-600">{uploadProgress}%</span>
                </div>
              )}
            </div>

            {/* Stage label */}
            <p className="text-sm font-medium text-gray-900">
              {t(`evidence.stage.${uploadStage}`, UPLOAD_STAGE_LABELS[uploadStage])}
            </p>

            {/* Progress bar */}
            <div className="mt-4 w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  uploadStage === 'complete' ? 'bg-green-500' : 'bg-blue-600'
                }`}
                style={{ width: `${uploadProgress}%` }}
              />
            </div>

            {/* Stage indicators */}
            <div className="mt-4 flex justify-between text-xs text-gray-400">
              {PROGRESS_STAGES.map((stage, index) => (
                <div
                  key={stage}
                  className={`flex flex-col items-center ${
                    uploadStage === stage
                      ? 'text-blue-600 font-medium'
                      : currentStageIndex > index
                      ? 'text-green-600'
                      : ''
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full mb-1 ${
                      uploadStage === stage
                        ? 'bg-blue-600'
                        : currentStageIndex > index
                        ? 'bg-green-500'
                        : 'bg-gray-300'
                    }`}
                  />
                  <span className="hidden sm:block">{t(`evidence.stageShort.${stage}`, stage)}</span>
                </div>
              ))}
            </div>

            {/* Upload details */}
            {capturedFile && uploadStage === 'uploading' && (
              <p className="mt-3 text-xs text-gray-400">
                {capturedFile.name} ({(capturedFile.size / 1024 / 1024).toFixed(1)} MB)
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Export types for use in other components
export type { EvidenceMetadata, UploadedEvidence, EvidenceUploadProps, GPSCoordinates }

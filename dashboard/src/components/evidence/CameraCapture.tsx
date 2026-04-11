/**
 * CameraCapture Component
 *
 * Camera integration component using navigator.mediaDevices.getUserMedia().
 * Features:
 * - Photo capture with flash option
 * - Front/back camera switching
 * - Preview captured photo
 * - Retake option
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export interface CapturedPhoto {
  blob: Blob
  dataUrl: string
  width: number
  height: number
  timestamp: Date
  facingMode: 'user' | 'environment'
  /** True when captured via native camera input (EXIF preserved) */
  hasExif: boolean
  /** Original file from native camera input — use this for uploads to preserve EXIF */
  originalFile?: File
}

export interface CameraCaptureProps {
  /** Callback when photo is captured */
  onCapture: (photo: CapturedPhoto) => void
  /** Callback when capture is cancelled */
  onCancel?: () => void
  /** Callback on error */
  onError?: (error: string) => void
  /** Preferred camera (default: environment/back) */
  preferredCamera?: 'user' | 'environment'
  /** Allow camera switching */
  allowSwitch?: boolean
  /** Enable flash (if supported) */
  enableFlash?: boolean
  /** Image quality (0-1) */
  quality?: number
  /** Aspect ratio constraint */
  aspectRatio?: '4:3' | '16:9' | '1:1'
  /** Additional CSS classes */
  className?: string
}

type CameraState = 'idle' | 'initializing' | 'ready' | 'captured' | 'error'

export function CameraCapture({
  onCapture,
  onCancel,
  onError,
  preferredCamera = 'environment',
  allowSwitch = true,
  enableFlash = false,
  quality = 0.92,
  aspectRatio = '4:3',
  className = '',
}: CameraCaptureProps) {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const nativeInputRef = useRef<HTMLInputElement>(null)

  const [state, setState] = useState<CameraState>('idle')
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>(preferredCamera)
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false)
  const [capturedPhoto, setCapturedPhoto] = useState<CapturedPhoto | null>(null)
  const [flashActive, setFlashActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isMobile] = useState(() => /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent))

  // Get aspect ratio values
  const getAspectRatioClass = useCallback(() => {
    switch (aspectRatio) {
      case '16:9':
        return 'aspect-video'
      case '1:1':
        return 'aspect-square'
      case '4:3':
      default:
        return 'aspect-[4/3]'
    }
  }, [aspectRatio])

  // Handle native camera capture (mobile) — file returned with full EXIF metadata
  const handleNativeCapture = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const objectUrl = URL.createObjectURL(file)

    const img = new Image()
    img.onload = () => {
      const photo: CapturedPhoto = {
        blob: file,
        dataUrl: objectUrl,
        width: img.naturalWidth,
        height: img.naturalHeight,
        timestamp: new Date(),
        facingMode: preferredCamera,
        hasExif: true,
        originalFile: file,
      }
      setCapturedPhoto(photo)
      setState('captured')
    }
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      const message = t('camera.captureError', 'Error al capturar foto')
      setError(message)
      setState('error')
      onError?.(message)
    }
    img.src = objectUrl

    // Reset the input so the same file can be re-selected
    if (nativeInputRef.current) {
      nativeInputRef.current.value = ''
    }
  }, [preferredCamera, t, onError])

  // Check for multiple cameras
  useEffect(() => {
    navigator.mediaDevices?.enumerateDevices()
      .then((devices) => {
        const videoInputs = devices.filter(d => d.kind === 'videoinput')
        setHasMultipleCameras(videoInputs.length > 1)
      })
      .catch(() => {
        setHasMultipleCameras(false)
      })
  }, [])

  // Initialize camera stream
  const initCamera = useCallback(async () => {
    setState('initializing')
    setError(null)

    try {
      // Stop any existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }

      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
        },
        audio: false,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream

        // Wait for video to be ready
        await new Promise<void>((resolve, reject) => {
          if (videoRef.current) {
            videoRef.current.onloadedmetadata = () => resolve()
            videoRef.current.onerror = () => reject(new Error('Video load error'))
          } else {
            reject(new Error('Video ref not available'))
          }
        })

        await videoRef.current.play()
        setState('ready')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('camera.error', 'Error al acceder a la camara')

      // Check for specific errors
      if (message.includes('Permission') || message.includes('NotAllowed')) {
        setError(t('camera.permissionDenied', 'Permiso de camara denegado'))
      } else if (message.includes('NotFound') || message.includes('DevicesNotFound')) {
        setError(t('camera.notFound', 'No se encontro camara'))
      } else {
        setError(message)
      }

      setState('error')
      onError?.(message)
    }
  }, [facingMode, onError, t])

  // Start camera on mount (desktop only — mobile uses native <input capture>)
  useEffect(() => {
    if (!isMobile) {
      initCamera()
    }

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Switch camera
  const switchCamera = useCallback(async () => {
    const newFacing = facingMode === 'user' ? 'environment' : 'user'
    setFacingMode(newFacing)

    // Stop current stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
    }

    // Reinitialize with new facing mode
    setState('initializing')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: newFacing },
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
        },
        audio: false,
      })

      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        setState('ready')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('camera.switchError', 'Error al cambiar camara')
      setError(message)
      setState('error')
    }
  }, [facingMode, t])

  // Capture photo
  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || state !== 'ready') return

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    if (!ctx) return

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Flash effect
    if (flashActive) {
      // Create a brief white flash overlay
      const overlay = document.createElement('div')
      overlay.className = 'fixed inset-0 bg-white z-50 pointer-events-none'
      overlay.style.animation = 'flash 150ms ease-out forwards'
      document.body.appendChild(overlay)
      setTimeout(() => overlay.remove(), 150)
    }

    // Draw the video frame to canvas
    ctx.drawImage(video, 0, 0)

    // Convert to blob
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError(t('camera.captureError', 'Error al capturar foto'))
          return
        }

        const dataUrl = canvas.toDataURL('image/jpeg', quality)

        const photo: CapturedPhoto = {
          blob,
          dataUrl,
          width: canvas.width,
          height: canvas.height,
          timestamp: new Date(),
          facingMode,
          hasExif: false,
        }

        setCapturedPhoto(photo)
        setState('captured')
      },
      'image/jpeg',
      quality
    )
  }, [state, flashActive, quality, facingMode, t])

  // Retake photo
  const retakePhoto = useCallback(() => {
    setCapturedPhoto(null)
    // On mobile, go back to idle (native input). On desktop, resume video feed.
    setState(isMobile ? 'idle' : 'ready')
  }, [isMobile])

  // Confirm photo
  const confirmPhoto = useCallback(() => {
    if (capturedPhoto) {
      // Stop the camera stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
      onCapture(capturedPhoto)
    }
  }, [capturedPhoto, onCapture])

  // Handle cancel
  const handleCancel = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    onCancel?.()
  }, [onCancel])

  // Render mobile native capture UI (uses <input capture> to preserve EXIF)
  if (isMobile && state !== 'captured' && state !== 'error') {
    return (
      <div className={`bg-gray-900 rounded-lg overflow-hidden ${className}`}>
        {/* Hidden native file input — opens device camera directly */}
        <input
          ref={nativeInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleNativeCapture}
          className="hidden"
        />

        <div className={`${getAspectRatioClass()} flex items-center justify-center bg-gray-800`}>
          <div className="text-center p-6">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-blue-500/20 flex items-center justify-center">
              <svg className="w-10 h-10 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <p className="text-white text-sm font-medium mb-4">
              {t('camera.takePhotoNative', 'Toma una foto con la camara de tu dispositivo')}
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => nativeInputRef.current?.click()}
                className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors touch-manipulation"
              >
                {t('camera.takePhoto', 'Tomar Foto')}
              </button>
              {onCancel && (
                <button
                  onClick={handleCancel}
                  className="w-full px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors touch-manipulation"
                >
                  {t('common.cancel', 'Cancelar')}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Render error state
  if (state === 'error') {
    return (
      <div className={`bg-gray-900 rounded-lg overflow-hidden ${className}`}>
        <div className={`${getAspectRatioClass()} flex items-center justify-center bg-gray-800`}>
          <div className="text-center p-6">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <p className="text-white text-sm font-medium mb-2">{error}</p>
            <p className="text-gray-400 text-xs mb-4">
              {t('camera.checkSettings', 'Verifica los permisos de camara en tu navegador')}
            </p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={initCamera}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {t('camera.retry', 'Reintentar')}
              </button>
              {onCancel && (
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {t('common.cancel', 'Cancelar')}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Render preview state
  if (state === 'captured' && capturedPhoto) {
    return (
      <div className={`bg-gray-900 rounded-lg overflow-hidden ${className}`}>
        <div className={`relative ${getAspectRatioClass()}`}>
          <img
            src={capturedPhoto.dataUrl}
            alt={t('camera.preview', 'Vista previa')}
            className="w-full h-full object-cover"
          />

          {/* Preview badge */}
          <div className="absolute top-3 left-3 px-2 py-1 bg-black/50 rounded text-white text-xs">
            {t('camera.preview', 'Vista previa')}
          </div>

          {/* Timestamp badge */}
          <div className="absolute top-3 right-3 px-2 py-1 bg-black/50 rounded text-white text-xs">
            {capturedPhoto.timestamp.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>

        {/* Action buttons */}
        <div className="p-4 bg-black/80">
          <div className="flex gap-3">
            <button
              onClick={retakePhoto}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors touch-manipulation"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {t('camera.retake', 'Volver a tomar')}
            </button>
            <button
              onClick={confirmPhoto}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors touch-manipulation"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {t('camera.usePhoto', 'Usar foto')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Render camera view
  return (
    <div className={`bg-gray-900 rounded-lg overflow-hidden ${className}`}>
      {/* Hidden canvas for capture */}
      <canvas ref={canvasRef} className="hidden" />

      <div className={`relative ${getAspectRatioClass()}`}>
        {/* Video feed */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
          style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'none' }}
        />

        {/* Loading overlay */}
        {(state === 'idle' || state === 'initializing') && (
          <div className="absolute inset-0 bg-gray-900 flex items-center justify-center">
            <div className="text-center">
              <svg className="w-10 h-10 mx-auto text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <p className="mt-3 text-white text-sm">{t('camera.initializing', 'Iniciando camara...')}</p>
            </div>
          </div>
        )}

        {/* Top controls */}
        <div className="absolute top-0 inset-x-0 p-3 bg-gradient-to-b from-black/60 to-transparent">
          <div className="flex items-center justify-between">
            {/* Cancel button */}
            {onCancel && (
              <button
                onClick={handleCancel}
                className="p-2 bg-black/30 hover:bg-black/50 rounded-full text-white transition-colors touch-manipulation"
                aria-label={t('common.cancel', 'Cancelar')}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}

            <div className="flex items-center gap-2">
              {/* Flash toggle */}
              {enableFlash && (
                <button
                  onClick={() => setFlashActive(!flashActive)}
                  className={`p-2 rounded-full transition-colors touch-manipulation ${
                    flashActive
                      ? 'bg-yellow-500 text-black'
                      : 'bg-black/30 hover:bg-black/50 text-white'
                  }`}
                  aria-label={flashActive ? t('camera.flashOff', 'Desactivar flash') : t('camera.flashOn', 'Activar flash')}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </button>
              )}

              {/* Camera switch button */}
              {allowSwitch && hasMultipleCameras && (
                <button
                  onClick={switchCamera}
                  disabled={state !== 'ready'}
                  className="p-2 bg-black/30 hover:bg-black/50 rounded-full text-white transition-colors disabled:opacity-50 touch-manipulation"
                  aria-label={t('camera.switch', 'Cambiar camara')}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Facing mode indicator */}
        <div className="absolute bottom-24 left-3 px-2 py-1 bg-black/50 rounded text-white text-xs">
          {facingMode === 'user' ? t('camera.front', 'Frontal') : t('camera.back', 'Trasera')}
        </div>
      </div>

      {/* Bottom controls */}
      <div className="p-4 pb-6 bg-gradient-to-t from-black/80 to-transparent">
        <div className="flex items-center justify-center gap-6">
          {/* Cancel button (mobile) */}
          {onCancel && isMobile && (
            <button
              onClick={handleCancel}
              className="p-3 bg-white/20 hover:bg-white/30 rounded-full text-white transition-colors touch-manipulation"
              aria-label={t('common.cancel', 'Cancelar')}
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          {/* Capture button */}
          <button
            onClick={capturePhoto}
            disabled={state !== 'ready'}
            className="p-5 bg-white hover:bg-gray-100 active:bg-gray-200 rounded-full transition-all touch-manipulation active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={t('camera.capture', 'Tomar foto')}
          >
            <div className="w-10 h-10 rounded-full border-4 border-blue-600" />
          </button>

          {/* Placeholder for symmetry */}
          {isMobile && <div className="w-12 h-12" />}
        </div>
      </div>

      {/* Flash animation style */}
      <style>{`
        @keyframes flash {
          0% { opacity: 0.8; }
          100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}

export default CameraCapture

/**
 * Camera Capture Component
 *
 * Native camera integration for evidence capture.
 * Extracts EXIF data for verification.
 */

import React, { useRef, useState, useCallback } from 'react';

export interface CaptureResult {
  blob: Blob;
  dataUrl: string;
  metadata: {
    timestamp: Date;
    hasGps: boolean;
    latitude?: number;
    longitude?: number;
    deviceModel?: string;
    captureSource: 'camera' | 'gallery' | 'unknown';
  };
}

interface CameraCaptureProps {
  onCapture: (result: CaptureResult) => void;
  onError?: (error: string) => void;
  allowGallery?: boolean;
  requireGps?: boolean;
  maxSizeMB?: number;
  quality?: number;
}

export function CameraCapture({
  onCapture,
  onError,
  allowGallery = false,
  requireGps = false,
  maxSizeMB = 5,
  quality = 0.85,
}: CameraCaptureProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleCapture = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);

    try {
      // Check file size
      if (file.size > maxSizeMB * 1024 * 1024) {
        throw new Error(`File too large. Maximum size is ${maxSizeMB}MB`);
      }

      // Read EXIF data
      const metadata = await extractExifData(file);

      // Check GPS requirement
      if (requireGps && !metadata.hasGps) {
        throw new Error('GPS location is required. Please enable location access.');
      }

      // Check capture source (camera vs gallery)
      if (!allowGallery && metadata.captureSource === 'gallery') {
        throw new Error('Only photos taken directly from camera are allowed.');
      }

      // Compress if needed
      const processedBlob = await processImage(file, quality);
      const dataUrl = await blobToDataUrl(processedBlob);

      setPreview(dataUrl);

      onCapture({
        blob: processedBlob,
        dataUrl,
        metadata,
      });
    } catch (error) {
      onError?.(error instanceof Error ? error.message : 'Failed to process image');
    } finally {
      setIsProcessing(false);
      // Reset input
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    }
  }, [onCapture, onError, allowGallery, requireGps, maxSizeMB, quality]);

  const openCamera = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const clearPreview = useCallback(() => {
    setPreview(null);
  }, []);

  return (
    <div className="camera-capture">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleCapture}
        className="hidden"
      />

      {preview ? (
        <div className="relative">
          <img
            src={preview}
            alt="Captured"
            className="w-full h-64 object-cover rounded-lg"
          />
          <button
            onClick={clearPreview}
            className="absolute top-2 right-2 p-2 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors"
          >
            ✕
          </button>
        </div>
      ) : (
        <button
          onClick={openCamera}
          disabled={isProcessing}
          className="w-full h-64 border-2 border-dashed border-slate-600 rounded-lg flex flex-col items-center justify-center gap-3 hover:border-blue-500 hover:bg-slate-800/50 transition-all disabled:opacity-50"
        >
          {isProcessing ? (
            <>
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-slate-400">Processing...</span>
            </>
          ) : (
            <>
              <span className="text-4xl">📷</span>
              <span className="text-slate-400">Tap to take photo</span>
              {requireGps && (
                <span className="text-xs text-amber-500">📍 Location required</span>
              )}
            </>
          )}
        </button>
      )}
    </div>
  );
}

/**
 * Extract EXIF metadata from image file
 */
async function extractExifData(file: File): Promise<CaptureResult['metadata']> {
  return new Promise((resolve) => {
    const reader = new FileReader();

    reader.onload = function(e) {
      const view = new DataView(e.target?.result as ArrayBuffer);

      // Check for JPEG
      if (view.getUint16(0, false) !== 0xFFD8) {
        resolve({
          timestamp: new Date(file.lastModified),
          hasGps: false,
          captureSource: 'unknown',
        });
        return;
      }

      const exif = parseExif(view);

      // Determine capture source
      let captureSource: 'camera' | 'gallery' | 'unknown' = 'unknown';

      // Check creation time vs file modified time
      const timeDiff = Math.abs(
        (exif.dateTime?.getTime() || 0) - file.lastModified
      );

      // If EXIF timestamp is very recent (< 5 minutes), likely from camera
      if (exif.dateTime && timeDiff < 5 * 60 * 1000) {
        captureSource = 'camera';
      } else if (exif.dateTime) {
        captureSource = 'gallery';
      }

      resolve({
        timestamp: exif.dateTime || new Date(file.lastModified),
        hasGps: exif.hasGps,
        latitude: exif.latitude,
        longitude: exif.longitude,
        deviceModel: exif.model,
        captureSource,
      });
    };

    reader.readAsArrayBuffer(file.slice(0, 128 * 1024)); // Read first 128KB for EXIF
  });
}

interface ExifData {
  dateTime?: Date;
  hasGps: boolean;
  latitude?: number;
  longitude?: number;
  model?: string;
}

function parseExif(view: DataView): ExifData {
  const result: ExifData = { hasGps: false };

  try {
    let offset = 2;

    while (offset < view.byteLength) {
      if (view.getUint16(offset, false) === 0xFFE1) {
        // Found APP1 (EXIF)
        const length = view.getUint16(offset + 2, false);
        const exifData = parseExifSegment(view, offset + 4, length - 2);
        Object.assign(result, exifData);
        break;
      }

      offset += 2 + view.getUint16(offset + 2, false);
    }
  } catch (e) {
    // EXIF parsing failed, return defaults
  }

  return result;
}

function parseExifSegment(view: DataView, start: number, _length: number): Partial<ExifData> {
  const result: Partial<ExifData> = {};

  // Check "Exif\0\0" header
  const header = String.fromCharCode(
    view.getUint8(start),
    view.getUint8(start + 1),
    view.getUint8(start + 2),
    view.getUint8(start + 3)
  );

  if (header !== 'Exif') return result;

  const tiffStart = start + 6;
  const littleEndian = view.getUint16(tiffStart, false) === 0x4949;

  // Parse IFD0
  const ifd0Offset = view.getUint32(tiffStart + 4, littleEndian);
  const ifd0 = parseIFD(view, tiffStart + ifd0Offset, littleEndian, tiffStart);

  // Extract model
  if (ifd0[0x0110]) {
    result.model = ifd0[0x0110];
  }

  // Extract DateTime
  if (ifd0[0x0132]) {
    const dateStr = ifd0[0x0132];
    // Format: "YYYY:MM:DD HH:MM:SS"
    const [date, time] = dateStr.split(' ');
    const [year, month, day] = date.split(':');
    const [hour, min, sec] = time.split(':');
    result.dateTime = new Date(
      parseInt(year), parseInt(month) - 1, parseInt(day),
      parseInt(hour), parseInt(min), parseInt(sec)
    );
  }

  // Check for GPS IFD
  if (ifd0[0x8825]) {
    const gpsOffset = ifd0[0x8825];
    const gps = parseIFD(view, tiffStart + gpsOffset, littleEndian, tiffStart);

    if (gps[0x0002] && gps[0x0004]) {
      result.hasGps = true;
      result.latitude = gps[0x0002] * (gps[0x0001] === 'S' ? -1 : 1);
      result.longitude = gps[0x0004] * (gps[0x0003] === 'W' ? -1 : 1);
    }
  }

  return result;
}

function parseIFD(
  view: DataView,
  offset: number,
  littleEndian: boolean,
  tiffStart: number
): Record<number, any> {
  const result: Record<number, any> = {};

  try {
    const entryCount = view.getUint16(offset, littleEndian);

    for (let i = 0; i < entryCount; i++) {
      const entryOffset = offset + 2 + i * 12;
      const tag = view.getUint16(entryOffset, littleEndian);
      const type = view.getUint16(entryOffset + 2, littleEndian);
      const count = view.getUint32(entryOffset + 4, littleEndian);

      let value: number | string;

      // Handle different types
      switch (type) {
        case 2: { // ASCII
          const strOffset = view.getUint32(entryOffset + 8, littleEndian);
          value = '';
          for (let j = 0; j < count - 1; j++) {
            value += String.fromCharCode(view.getUint8(tiffStart + strOffset + j));
          }
          break;
        }
        case 3: // SHORT
          value = view.getUint16(entryOffset + 8, littleEndian);
          break;
        case 4: // LONG
          value = view.getUint32(entryOffset + 8, littleEndian);
          break;
        case 5: { // RATIONAL
          const ratOffset = view.getUint32(entryOffset + 8, littleEndian);
          const num = view.getUint32(tiffStart + ratOffset, littleEndian);
          const den = view.getUint32(tiffStart + ratOffset + 4, littleEndian);
          value = num / den;
          break;
        }
        default:
          continue;
      }

      result[tag] = value;
    }
  } catch (e) {
    // IFD parsing failed
  }

  return result;
}

/**
 * Process and compress image
 */
async function processImage(file: File, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');

      // Limit max dimension to 2048
      const maxDim = 2048;
      let width = img.width;
      let height = img.height;

      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = Math.round((height / width) * maxDim);
          width = maxDim;
        } else {
          width = Math.round((width / height) * maxDim);
          height = maxDim;
        }
      }

      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Canvas not supported'));
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to compress image'));
          }
        },
        'image/jpeg',
        quality
      );
    };

    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = URL.createObjectURL(file);
  });
}

/**
 * Convert blob to data URL
 */
function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read blob'));
    reader.readAsDataURL(blob);
  });
}

export default CameraCapture;

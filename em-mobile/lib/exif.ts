import type { ExifData } from "../components/CameraCapture";

/**
 * Extract EXIF metadata from a file URI using exifr library.
 * Used as fallback when expo-camera/expo-image-picker don't return EXIF.
 */
export async function extractExifFromFile(fileUri: string): Promise<ExifData | null> {
  try {
    const exifr = await import("exifr");
    const data = await exifr.default.parse(fileUri, {
      pick: [
        "Make", "Model", "DateTimeOriginal", "DateTime", "DateTimeDigitized",
        "Software", "GPSLatitude", "GPSLongitude", "ImageWidth", "ImageHeight",
        "ExifImageWidth", "ExifImageHeight", "ProcessingSoftware", "UserComment",
        "CreateDate", "ModifyDate",
      ],
    });
    if (!data) return null;
    console.log("[EXIF] Extracted via exifr:", Object.keys(data).join(", "));
    return data as ExifData;
  } catch (err) {
    console.warn("[EXIF] exifr extraction failed:", (err as Error).message);
    return null;
  }
}

/**
 * Build a clean EXIF summary for the evidence payload.
 * Normalizes fields from both expo SDK and exifr formats.
 */
export function buildExifPayload(exif: ExifData): Record<string, unknown> {
  const payload: Record<string, unknown> = {};

  // Camera info
  if (exif.Make) payload.camera_make = exif.Make;
  if (exif.Model) payload.camera_model = exif.Model;
  if (exif.Software) payload.software = exif.Software;

  // Timestamp (prefer DateTimeOriginal)
  const timestamp = exif.DateTimeOriginal || exif.DateTime || exif.DateTimeDigitized;
  if (timestamp) {
    // EXIF format: "2026:03:16 12:30:00" → ISO format
    if (typeof timestamp === "string" && timestamp.includes(":")) {
      const isoStr = timestamp.replace(/^(\d{4}):(\d{2}):(\d{2})/, "$1-$2-$3");
      payload.timestamp = isoStr;
    } else if (timestamp instanceof Date) {
      payload.timestamp = timestamp.toISOString();
    } else {
      payload.timestamp = String(timestamp);
    }
  }

  // GPS from EXIF
  if (typeof exif.GPSLatitude === "number" && typeof exif.GPSLongitude === "number") {
    payload.gps_exif = {
      lat: exif.GPSLatitude,
      lng: exif.GPSLongitude,
    };
  }

  // Image dimensions
  const width = exif.ImageWidth || exif.ExifImageWidth;
  const height = exif.ImageHeight || exif.ExifImageHeight;
  if (width && height) {
    payload.dimensions = { width, height };
  }

  return payload;
}

/**
 * Check if EXIF data indicates a real camera photo (not screenshot/gallery edit).
 */
export function isLikelyCameraPhoto(exif: ExifData): {
  isCamera: boolean;
  source: "camera" | "screenshot" | "gallery" | "unknown";
  reason: string;
} {
  const software = (exif.Software || "").toLowerCase();
  const make = exif.Make || "";
  const model = exif.Model || "";

  // Screenshot indicators
  const screenshotKeywords = ["screenshot", "snipping", "grab", "capture", "screen"];
  if (screenshotKeywords.some((kw) => software.includes(kw))) {
    return { isCamera: false, source: "screenshot", reason: "Screenshot software detected" };
  }

  // Editing software indicators
  const editingKeywords = ["photoshop", "lightroom", "snapseed", "vsco", "instagram", "facetune"];
  if (editingKeywords.some((kw) => software.includes(kw))) {
    return { isCamera: false, source: "gallery", reason: "Editing software detected" };
  }

  // Camera indicators
  const knownMakes = ["apple", "samsung", "google", "huawei", "xiaomi", "oneplus", "sony", "motorola", "oppo", "vivo"];
  if (knownMakes.some((m) => make.toLowerCase().includes(m))) {
    return { isCamera: true, source: "camera", reason: `Camera detected: ${make} ${model}` };
  }

  // Has Make/Model = likely camera
  if (make && model) {
    return { isCamera: true, source: "camera", reason: `Camera: ${make} ${model}` };
  }

  // Has timestamp but no make = unknown
  if (exif.DateTimeOriginal) {
    return { isCamera: false, source: "unknown", reason: "Has timestamp but no camera info" };
  }

  return { isCamera: false, source: "unknown", reason: "No camera metadata found" };
}

/**
 * Chamba SDK Utility Functions
 *
 * Helper functions for working with bounties, locations, and evidence.
 */

import type { Evidence, EvidenceType, PaymentToken } from './types';

// =============================================================================
// Bounty Formatting
// =============================================================================

/**
 * Format a bounty amount for display.
 *
 * @param amount - Amount in USD
 * @param token - Payment token (default: USDC)
 * @returns Formatted string like "$2.50 USDC"
 *
 * @example
 * ```typescript
 * formatBounty(2.5);        // "$2.50 USDC"
 * formatBounty(100, 'DAI'); // "$100.00 DAI"
 * formatBounty(0.5);        // "$0.50 USDC"
 * ```
 */
export function formatBounty(amount: number, token: PaymentToken = 'USDC'): string {
  const formatted = amount.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${formatted} ${token}`;
}

/**
 * Parse a bounty string back to a number.
 *
 * @param bountyString - String like "$2.50 USDC"
 * @returns Numeric amount
 *
 * @example
 * ```typescript
 * parseBounty("$2.50 USDC"); // 2.5
 * parseBounty("100.00");     // 100
 * ```
 */
export function parseBounty(bountyString: string): number {
  const cleaned = bountyString.replace(/[^0-9.]/g, '');
  return parseFloat(cleaned) || 0;
}

/**
 * Check if a bounty amount is within valid range.
 *
 * @param amount - Amount in USD
 * @returns True if valid ($0.50 - $10,000)
 */
export function isValidBounty(amount: number): boolean {
  return amount >= 0.5 && amount <= 10000;
}

// =============================================================================
// Location Utilities
// =============================================================================

/**
 * Geographic coordinates.
 */
export interface Coordinates {
  latitude: number;
  longitude: number;
}

/**
 * Calculate the distance between two geographic coordinates.
 * Uses the Haversine formula for great-circle distance.
 *
 * @param loc1 - First location
 * @param loc2 - Second location
 * @returns Distance in kilometers
 *
 * @example
 * ```typescript
 * const miami = { latitude: 25.7617, longitude: -80.1918 };
 * const nyc = { latitude: 40.7128, longitude: -74.0060 };
 * calculateDistance(miami, nyc); // ~1757.67 km
 * ```
 */
export function calculateDistance(loc1: Coordinates, loc2: Coordinates): number {
  const R = 6371; // Earth's radius in kilometers

  const lat1Rad = toRadians(loc1.latitude);
  const lat2Rad = toRadians(loc2.latitude);
  const deltaLat = toRadians(loc2.latitude - loc1.latitude);
  const deltaLon = toRadians(loc2.longitude - loc1.longitude);

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) *
    Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

/**
 * Calculate distance in miles.
 *
 * @param loc1 - First location
 * @param loc2 - Second location
 * @returns Distance in miles
 */
export function calculateDistanceMiles(loc1: Coordinates, loc2: Coordinates): number {
  return calculateDistance(loc1, loc2) * 0.621371;
}

/**
 * Check if a location is within a specified radius of a target.
 *
 * @param location - Location to check
 * @param target - Target center point
 * @param radiusKm - Radius in kilometers
 * @returns True if within radius
 */
export function isWithinRadius(
  location: Coordinates,
  target: Coordinates,
  radiusKm: number
): boolean {
  return calculateDistance(location, target) <= radiusKm;
}

/**
 * Convert degrees to radians.
 */
function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

// =============================================================================
// Evidence Validation
// =============================================================================

/**
 * Evidence validation result.
 */
export interface EvidenceValidationResult {
  /** Whether all required evidence is valid */
  valid: boolean;
  /** List of missing required evidence types */
  missing: EvidenceType[];
  /** List of invalid evidence types with reasons */
  invalid: Array<{ type: EvidenceType; reason: string }>;
  /** List of provided evidence types */
  provided: EvidenceType[];
}

/**
 * Validate evidence against required and optional types.
 *
 * @param evidence - Evidence to validate
 * @param required - Required evidence types
 * @param optional - Optional evidence types
 * @returns Validation result
 *
 * @example
 * ```typescript
 * const evidence = {
 *   photo: 'https://example.com/photo.jpg',
 *   textResponse: 'Store is open'
 * };
 *
 * const result = validateEvidence(evidence, ['photo', 'photo_geo'], ['text_response']);
 * // { valid: false, missing: ['photo_geo'], invalid: [], provided: ['photo', 'text_response'] }
 * ```
 */
export function validateEvidence(
  evidence: Evidence,
  required: EvidenceType[] = [],
  optional: EvidenceType[] = []
): EvidenceValidationResult {
  const result: EvidenceValidationResult = {
    valid: true,
    missing: [],
    invalid: [],
    provided: [],
  };

  // Check required evidence
  for (const type of required) {
    const value = getEvidenceValue(evidence, type);

    if (value === undefined || value === null) {
      result.missing.push(type);
      result.valid = false;
    } else {
      const validation = validateEvidenceType(type, value);
      if (!validation.valid) {
        result.invalid.push({ type, reason: validation.reason! });
        result.valid = false;
      } else {
        result.provided.push(type);
      }
    }
  }

  // Check optional evidence (only validate if provided)
  for (const type of optional) {
    const value = getEvidenceValue(evidence, type);

    if (value !== undefined && value !== null) {
      const validation = validateEvidenceType(type, value);
      if (!validation.valid) {
        result.invalid.push({ type, reason: validation.reason! });
      } else {
        result.provided.push(type);
      }
    }
  }

  return result;
}

/**
 * Get evidence value by type.
 */
function getEvidenceValue(evidence: Evidence, type: EvidenceType): unknown {
  switch (type) {
    case 'photo':
      return evidence.photo;
    case 'photo_geo':
      return evidence.photoGeo;
    case 'video':
      return evidence.video;
    case 'document':
      return evidence.document;
    case 'signature':
      return evidence.signature;
    case 'text_response':
      return evidence.textResponse;
    default:
      return undefined;
  }
}

/**
 * Validate a single evidence type.
 */
function validateEvidenceType(
  type: EvidenceType,
  value: unknown
): { valid: boolean; reason?: string } {
  switch (type) {
    case 'photo':
      return validatePhoto(value);
    case 'photo_geo':
      return validatePhotoGeo(value);
    case 'video':
      return validateVideo(value);
    case 'document':
      return validateDocument(value);
    case 'signature':
      return validateSignature(value);
    case 'text_response':
      return validateTextResponse(value);
    default:
      return { valid: true };
  }
}

function validatePhoto(value: unknown): { valid: boolean; reason?: string } {
  if (typeof value === 'string') {
    if (!isValidUrl(value)) {
      return { valid: false, reason: 'Invalid photo URL' };
    }
    return { valid: true };
  }

  if (Array.isArray(value)) {
    const invalidUrls = value.filter(v => typeof v !== 'string' || !isValidUrl(v));
    if (invalidUrls.length > 0) {
      return { valid: false, reason: 'One or more invalid photo URLs' };
    }
    return { valid: true };
  }

  return { valid: false, reason: 'Photo must be a URL or array of URLs' };
}

function validatePhotoGeo(value: unknown): { valid: boolean; reason?: string } {
  if (typeof value !== 'object' || value === null) {
    return { valid: false, reason: 'Photo geo must be an object with url, latitude, longitude' };
  }

  const geo = value as Record<string, unknown>;

  if (typeof geo.url !== 'string' || !isValidUrl(geo.url)) {
    return { valid: false, reason: 'Invalid photo URL' };
  }

  if (typeof geo.latitude !== 'number' || geo.latitude < -90 || geo.latitude > 90) {
    return { valid: false, reason: 'Invalid latitude (must be -90 to 90)' };
  }

  if (typeof geo.longitude !== 'number' || geo.longitude < -180 || geo.longitude > 180) {
    return { valid: false, reason: 'Invalid longitude (must be -180 to 180)' };
  }

  return { valid: true };
}

function validateVideo(value: unknown): { valid: boolean; reason?: string } {
  if (typeof value !== 'string' || !isValidUrl(value)) {
    return { valid: false, reason: 'Video must be a valid URL' };
  }
  return { valid: true };
}

function validateDocument(value: unknown): { valid: boolean; reason?: string } {
  if (typeof value !== 'string' || !isValidUrl(value)) {
    return { valid: false, reason: 'Document must be a valid URL' };
  }
  return { valid: true };
}

function validateSignature(value: unknown): { valid: boolean; reason?: string } {
  if (typeof value !== 'string') {
    return { valid: false, reason: 'Signature must be a string (data URL or base64)' };
  }

  // Check for data URL or base64
  if (!value.startsWith('data:') && !isBase64(value)) {
    return { valid: false, reason: 'Signature must be a data URL or base64 encoded' };
  }

  return { valid: true };
}

function validateTextResponse(value: unknown): { valid: boolean; reason?: string } {
  if (typeof value !== 'string') {
    return { valid: false, reason: 'Text response must be a string' };
  }

  if (value.trim().length < 10) {
    return { valid: false, reason: 'Text response must be at least 10 characters' };
  }

  return { valid: true };
}

/**
 * Check if string is a valid URL.
 */
function isValidUrl(str: string): boolean {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if string is base64 encoded.
 */
function isBase64(str: string): boolean {
  if (str.length === 0) return false;
  const base64Regex = /^[A-Za-z0-9+/]+=*$/;
  return base64Regex.test(str);
}

// =============================================================================
// Task Utilities
// =============================================================================

/**
 * Calculate deadline date from hours.
 *
 * @param hours - Hours from now
 * @returns Deadline Date object
 */
export function calculateDeadline(hours: number): Date {
  return new Date(Date.now() + hours * 60 * 60 * 1000);
}

/**
 * Check if a deadline has passed.
 *
 * @param deadline - Deadline date
 * @returns True if deadline has passed
 */
export function isExpired(deadline: Date): boolean {
  return new Date() > deadline;
}

/**
 * Calculate time remaining until deadline.
 *
 * @param deadline - Deadline date
 * @returns Object with hours, minutes, seconds remaining (negative if expired)
 */
export function timeRemaining(deadline: Date): {
  hours: number;
  minutes: number;
  seconds: number;
  expired: boolean;
} {
  const diffMs = deadline.getTime() - Date.now();
  const expired = diffMs < 0;
  const absDiff = Math.abs(diffMs);

  const hours = Math.floor(absDiff / (1000 * 60 * 60));
  const minutes = Math.floor((absDiff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((absDiff % (1000 * 60)) / 1000);

  return { hours, minutes, seconds, expired };
}

/**
 * Format time remaining as human-readable string.
 *
 * @param deadline - Deadline date
 * @returns String like "2h 30m remaining" or "Expired 1h ago"
 */
export function formatTimeRemaining(deadline: Date): string {
  const remaining = timeRemaining(deadline);

  const parts: string[] = [];
  if (remaining.hours > 0) parts.push(`${remaining.hours}h`);
  if (remaining.minutes > 0) parts.push(`${remaining.minutes}m`);
  if (parts.length === 0) parts.push(`${remaining.seconds}s`);

  const timeStr = parts.join(' ');
  return remaining.expired ? `Expired ${timeStr} ago` : `${timeStr} remaining`;
}

// =============================================================================
// Retry Utilities
// =============================================================================

/**
 * Options for retry with backoff.
 */
export interface RetryOptions {
  /** Maximum number of retries (default: 3) */
  maxRetries?: number;
  /** Initial delay in milliseconds (default: 1000) */
  initialDelayMs?: number;
  /** Maximum delay in milliseconds (default: 30000) */
  maxDelayMs?: number;
  /** Backoff multiplier (default: 2) */
  backoffMultiplier?: number;
  /** Function to determine if error is retryable */
  shouldRetry?: (error: Error) => boolean;
}

/**
 * Retry a function with exponential backoff.
 *
 * @param fn - Async function to retry
 * @param options - Retry options
 * @returns Result of the function
 *
 * @example
 * ```typescript
 * const result = await retryWithBackoff(
 *   () => api.createTask(taskData),
 *   { maxRetries: 3, initialDelayMs: 1000 }
 * );
 * ```
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelayMs = 1000,
    maxDelayMs = 30000,
    backoffMultiplier = 2,
    shouldRetry = () => true,
  } = options;

  let lastError: Error | null = null;
  let delay = initialDelayMs;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt === maxRetries || !shouldRetry(lastError)) {
        throw lastError;
      }

      await sleep(delay);
      delay = Math.min(delay * backoffMultiplier, maxDelayMs);
    }
  }

  throw lastError;
}

/**
 * Sleep for specified milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

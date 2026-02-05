/**
 * Execution Market: Task Category Constants
 * Shared definitions for category icons and labels across the dashboard.
 */

import type { TaskCategory } from '../types/database'

// Category icons (emoji-based, universal)
export const CATEGORY_ICONS: Record<TaskCategory, string> = {
  physical_presence: '📍',
  knowledge_access: '📚',
  human_authority: '📋',
  simple_action: '✋',
  digital_physical: '🔗',
}

// Category labels for fallback (i18n keys should be used instead where possible)
export const CATEGORY_LABELS: Record<TaskCategory, string> = {
  physical_presence: 'Physical Presence',
  knowledge_access: 'Knowledge Access',
  human_authority: 'Human Authority',
  simple_action: 'Simple Action',
  digital_physical: 'Digital-Physical',
}

// Evidence type labels
export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  photo: 'Photo',
  photo_geo: 'Photo with location',
  video: 'Video',
  document: 'Document',
  receipt: 'Receipt',
  signature: 'Signature',
  notarized: 'Notarized',
  timestamp_proof: 'Timestamp proof',
  text_response: 'Text response',
  measurement: 'Measurement',
  screenshot: 'Screenshot',
}

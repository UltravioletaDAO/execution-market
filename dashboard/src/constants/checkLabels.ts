import type { TFunction } from 'i18next'

const CHECK_LABEL_KEYS: Record<string, string> = {
  schema: 'autoCheck.checks.schema',
  gps: 'autoCheck.checks.gps',
  timestamp: 'autoCheck.checks.timestamp',
  evidence_hash: 'autoCheck.checks.evidence_hash',
  metadata: 'autoCheck.checks.metadata',
  ai_semantic: 'autoCheck.checks.ai_semantic',
  tampering: 'autoCheck.checks.tampering',
  genai_detection: 'autoCheck.checks.genai_detection',
  photo_source: 'autoCheck.checks.photo_source',
  duplicate: 'autoCheck.checks.duplicate',
}

export function getCheckLabel(name: string, t: TFunction): string {
  const key = CHECK_LABEL_KEYS[name]
  return key ? t(key, name) : name
}

// Execution Market: human-readable evidence renderer.
//
// Publishers were shown the raw evidence JSON ("estructura que no me sirve").
// This renders it the way a reviewer actually reads it: images inline, text
// responses as text, key metadata formatted, GPS redacted by default, with the
// raw JSON tucked behind a toggle for debugging.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { safeHref, safeSrc } from '../lib/safeHref'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

const GPS_KEYS = new Set(['latitude', 'longitude', 'lat', 'lng', 'lon'])
const IMAGE_KEYS = new Set(['photo', 'photo_geo', 'screenshot', 'receipt', 'signature'])
const IMAGE_EXT = /\.(jpg|jpeg|png|gif|webp)$/i

function resolveEvidenceUrl(fileUrl: string): string {
  if (!fileUrl) return ''
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) return fileUrl
  return `${SUPABASE_URL}/storage/v1/object/public/evidence/${fileUrl}`
}

function redactGps(obj: unknown): unknown {
  if (typeof obj !== 'object' || obj === null) return obj
  if (Array.isArray(obj)) return obj.map(redactGps)
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    out[k] = GPS_KEYS.has(k.toLowerCase()) && typeof v === 'number' ? '[hidden]' : redactGps(v)
  }
  return out
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** Format a metadata leaf for display. */
function fmt(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

interface EvidenceEntryProps {
  name: string
  value: unknown
}

function EvidenceEntry({ name, value }: EvidenceEntryProps) {
  const { t } = useTranslation()
  const label = name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

  // text-style responses: { type, value } or a bare string
  if (typeof value === 'string') {
    return (
      <div className="mb-3">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-1">{label}</p>
        <p className="text-sm text-zinc-800 whitespace-pre-wrap break-words">{value}</p>
      </div>
    )
  }

  if (!isRecord(value)) {
    return (
      <div className="mb-3">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-1">{label}</p>
        <p className="text-sm text-zinc-800">{fmt(value)}</p>
      </div>
    )
  }

  const rec = value
  const textVal = rec.value ?? rec.text ?? rec.response
  const rawUrl = String(rec.fileUrl || rec.url || '')
  const metadata = isRecord(rec.metadata) ? rec.metadata : undefined
  const storagePath = String(
    (metadata?.storagePath || metadata?.storage_path || metadata?.path || rec.storagePath || '') as string,
  )
  const fileUrl = rawUrl
    ? resolveEvidenceUrl(rawUrl)
    : storagePath
      ? resolveEvidenceUrl(storagePath)
      : ''
  const isImage =
    (fileUrl && IMAGE_EXT.test(fileUrl)) || IMAGE_KEYS.has(name.toLowerCase())

  // Metadata worth surfacing (skip internal/storage noise + GPS handled below)
  const metaEntries = metadata
    ? Object.entries(metadata).filter(
        ([k]) => !['storagePath', 'storage_path', 'path', 'backend', 'nonce', 'gps'].includes(k),
      )
    : []

  return (
    <div className="mb-3">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-1">{label}</p>

      {typeof textVal === 'string' && (
        <p className="text-sm text-zinc-800 whitespace-pre-wrap break-words mb-2">{textVal}</p>
      )}

      {isImage && fileUrl && (
        <a href={safeHref(fileUrl)} target="_blank" rel="noopener noreferrer" className="block">
          <img
            src={safeSrc(fileUrl)}
            alt={label}
            className="max-h-72 rounded-lg border border-zinc-200 object-contain"
          />
        </a>
      )}
      {!isImage && fileUrl && (
        <a href={safeHref(fileUrl)} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
          📁 {t('review.openFile', 'Abrir archivo')}
        </a>
      )}

      {metaEntries.length > 0 && (
        <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-xs">
          {metaEntries.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-zinc-500">{k.replace(/_/g, ' ')}</dt>
              <dd className="text-zinc-800 break-words">{fmt(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      {metadata?.gps != null && (
        <p className="mt-1 text-xs text-zinc-400">{t('review.gpsCaptured', 'GPS capturado (oculto)')}</p>
      )}
    </div>
  )
}

export function EvidenceView({ evidence }: { evidence: Record<string, unknown> | null | undefined }) {
  const { t } = useTranslation()
  const [showRaw, setShowRaw] = useState(false)

  if (!evidence || Object.keys(evidence).length === 0) {
    return <p className="text-sm text-zinc-500">{t('review.noEvidence', 'Sin evidencia.')}</p>
  }

  return (
    <div>
      <div className="space-y-1">
        {Object.entries(evidence).map(([name, value]) => (
          <EvidenceEntry key={name} name={name} value={value} />
        ))}
      </div>

      <button
        type="button"
        onClick={() => setShowRaw((p) => !p)}
        className="mt-2 text-xs text-zinc-400 hover:text-zinc-600 underline"
      >
        {showRaw ? t('review.hideRaw', 'Ocultar datos técnicos') : t('review.showRaw', 'Ver datos técnicos (JSON)')}
      </button>
      {showRaw && (
        <pre className="mt-2 bg-gray-900 text-green-400 p-3 rounded-lg text-xs overflow-auto max-h-80">
          {JSON.stringify(redactGps(evidence), null, 2)}
        </pre>
      )}
    </div>
  )
}

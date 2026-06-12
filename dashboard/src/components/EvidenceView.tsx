// Execution Market: human-readable evidence renderer.
//
// The publisher must NEVER see raw JSON. Every value is rendered as a labelled
// field, an image, or a collapsible capsule — nested objects (forensic, gps,
// device) become expandable sections, not a JSON dump. Refined B&W styling to
// match the dashboard. GPS coordinates are redacted.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { safeHref, safeSrc } from '../lib/safeHref'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

const GPS_COORD_KEYS = new Set(['latitude', 'longitude', 'lat', 'lng', 'lon'])
const IMAGE_KEYS = new Set(['photo', 'photo_geo', 'screenshot', 'receipt', 'signature'])
const IMAGE_EXT = /\.(jpg|jpeg|png|gif|webp)$/i
// Internal/noise keys we never surface to the reviewer.
const HIDDEN_KEYS = new Set(['backend', 'nonce', 'storagepath', 'storage_path', 'path'])

function resolveEvidenceUrl(fileUrl: string): string {
  if (!fileUrl) return ''
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) return fileUrl
  return `${SUPABASE_URL}/storage/v1/object/public/evidence/${fileUrl}`
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function prettyLabel(key: string): string {
  return key
    .replace(/[_-]+/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim()
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

/** Format a leaf value for display — dates, sizes, hashes, plain text. */
function formatLeaf(key: string, value: unknown): string {
  if (value == null) return '—'
  const k = key.toLowerCase()
  if (typeof value === 'number') {
    if (k === 'size' || k.endsWith('bytes')) return formatBytes(value)
    // epoch seconds / ms → readable date
    if (k.includes('timestamp') || k.includes('_at') || k === 'ts') {
      const ms = value > 1e12 ? value : value * 1000
      const d = new Date(ms)
      if (!Number.isNaN(d.getTime())) return d.toLocaleString()
    }
    return String(value)
  }
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  if (typeof value === 'string') {
    // ISO date
    if (/^\d{4}-\d{2}-\d{2}T/.test(value)) {
      const d = new Date(value)
      if (!Number.isNaN(d.getTime())) return d.toLocaleString()
    }
    return value
  }
  return String(value)
}

// ---------------------------------------------------------------------------
// Collapsible capsule
// ---------------------------------------------------------------------------
function Capsule({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-zinc-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 bg-zinc-50 hover:bg-zinc-100 transition-colors text-left"
      >
        <span className="flex items-baseline gap-2 min-w-0">
          <span className="text-xs font-semibold text-zinc-700 uppercase tracking-wide truncate">{title}</span>
          {subtitle && <span className="text-[11px] text-zinc-400 truncate">{subtitle}</span>}
        </span>
        <svg
          className={`w-4 h-4 text-zinc-400 flex-shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
      </button>
      {open && <div className="px-3 py-2.5 bg-white">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Key/value grid for primitive fields
// ---------------------------------------------------------------------------
function FieldGrid({ entries }: { entries: [string, unknown][] }) {
  if (entries.length === 0) return null
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5">
      {entries.map(([k, v]) => {
        const isHash = typeof v === 'string' && /^(0x)?[0-9a-f]{16,}$/i.test(v)
        return (
          <div key={k} className="contents">
            <dt className="text-xs text-zinc-500">{prettyLabel(k)}</dt>
            <dd className={`text-xs text-zinc-900 break-words ${isHash ? 'font-mono' : ''}`}>
              {formatLeaf(k, v)}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}

// ---------------------------------------------------------------------------
// GPS capsule — coordinates redacted, accuracy/altitude shown
// ---------------------------------------------------------------------------
function GpsCapsule({ t, gps }: { t: ReturnType<typeof useTranslation>['t']; gps: Record<string, unknown> }) {
  const accuracy = typeof gps.accuracy === 'number' && gps.accuracy > 0 ? `±${Math.round(gps.accuracy)} m` : null
  const meta = Object.entries(gps).filter(([k]) => !GPS_COORD_KEYS.has(k.toLowerCase()))
  return (
    <Capsule title={t('evidence.gps', 'Ubicación GPS')} subtitle={t('evidence.gpsRedacted', 'coordenadas ocultas')}>
      <div className="flex items-center gap-2 mb-2 text-xs text-zinc-600">
        <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span>{t('evidence.gpsPresent', 'Ubicación capturada')}{accuracy ? ` · ${t('evidence.accuracy', 'precisión')} ${accuracy}` : ''}</span>
      </div>
      <FieldGrid entries={meta} />
    </Capsule>
  )
}

// ---------------------------------------------------------------------------
// Render one nested object as label/value grid + sub-capsules for objects
// ---------------------------------------------------------------------------
function ObjectBody({ t, obj }: { t: ReturnType<typeof useTranslation>['t']; obj: Record<string, unknown> }) {
  const primitives: [string, unknown][] = []
  const nested: [string, Record<string, unknown>][] = []
  for (const [k, v] of Object.entries(obj)) {
    if (HIDDEN_KEYS.has(k.toLowerCase())) continue
    if (isRecord(v)) nested.push([k, v])
    else primitives.push([k, v])
  }
  return (
    <div className="space-y-2">
      <FieldGrid entries={primitives} />
      {nested.map(([k, v]) =>
        k.toLowerCase() === 'gps' ? (
          <GpsCapsule key={k} t={t} gps={v} />
        ) : (
          <Capsule key={k} title={prettyLabel(k)}>
            <ObjectBody t={t} obj={v} />
          </Capsule>
        ),
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// One top-level evidence entry (image, text, or structured object)
// ---------------------------------------------------------------------------
function EvidenceEntry({ t, name, value }: { t: ReturnType<typeof useTranslation>['t']; name: string; value: unknown }) {
  const label = prettyLabel(name)

  // Plain string answer
  if (typeof value === 'string') {
    return (
      <Field label={label}>
        <p className="text-sm text-zinc-800 whitespace-pre-wrap break-words">{value}</p>
      </Field>
    )
  }

  if (!isRecord(value)) {
    return (
      <Field label={label}>
        <p className="text-sm text-zinc-800">{formatLeaf(name, value)}</p>
      </Field>
    )
  }

  const rec = value
  const textVal = rec.value ?? rec.text ?? rec.response
  const rawUrl = String(rec.fileUrl || rec.url || '')
  const metadata = isRecord(rec.metadata) ? rec.metadata : undefined
  const storagePath = String(
    (metadata?.storagePath || metadata?.storage_path || metadata?.path || rec.storagePath || '') as string,
  )
  const fileUrl = rawUrl ? resolveEvidenceUrl(rawUrl) : storagePath ? resolveEvidenceUrl(storagePath) : ''
  const isImage = (fileUrl && IMAGE_EXT.test(fileUrl)) || IMAGE_KEYS.has(name.toLowerCase())

  // Surface plain fields (size, checksum, mimeType, source, capture_timestamp…)
  // directly; nested objects (forensic, gps, device) become capsules.
  const fields: [string, unknown][] = []
  const capsules: [string, Record<string, unknown>][] = []
  for (const [k, v] of Object.entries(rec)) {
    const kl = k.toLowerCase()
    if (HIDDEN_KEYS.has(kl) || kl === 'fileurl' || kl === 'url' || kl === 'value' || kl === 'text' || kl === 'response' || kl === 'type' || kl === 'metadata') continue
    if (isRecord(v)) capsules.push([k, v])
    else fields.push([k, v])
  }
  // Pull metadata's nested objects up as capsules too (forensic/device/gps).
  if (metadata) {
    for (const [k, v] of Object.entries(metadata)) {
      const kl = k.toLowerCase()
      if (HIDDEN_KEYS.has(kl)) continue
      if (isRecord(v)) capsules.push([k, v])
      else fields.push([k, v])
    }
  }

  return (
    <Field label={label}>
      <div className="space-y-2.5">
        {typeof textVal === 'string' && (
          <p className="text-sm text-zinc-800 whitespace-pre-wrap break-words">{textVal}</p>
        )}
        {isImage && fileUrl && (
          <a href={safeHref(fileUrl)} target="_blank" rel="noopener noreferrer" className="block w-fit">
            <img src={safeSrc(fileUrl)} alt={label} className="max-h-80 rounded-lg border border-zinc-200 object-contain" />
          </a>
        )}
        {!isImage && fileUrl && (
          <a href={safeHref(fileUrl)} target="_blank" rel="noopener noreferrer" className="text-sm text-zinc-700 underline hover:text-zinc-900">
            📁 {t('review.openFile', 'Abrir archivo')}
          </a>
        )}
        {fields.length > 0 && <FieldGrid entries={fields} />}
        {capsules.map(([k, v]) =>
          k.toLowerCase() === 'gps' ? (
            <GpsCapsule key={k} t={t} gps={v} />
          ) : (
            <Capsule key={k} title={prettyLabel(k)}>
              <ObjectBody t={t} obj={v} />
            </Capsule>
          ),
        )}
      </div>
    </Field>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-1.5">{label}</p>
      {children}
    </div>
  )
}

export function EvidenceView({ evidence }: { evidence: Record<string, unknown> | null | undefined }) {
  const { t } = useTranslation()
  if (!evidence || Object.keys(evidence).length === 0) {
    return <p className="text-sm text-zinc-500">{t('review.noEvidence', 'Sin evidencia.')}</p>
  }
  return (
    <div className="space-y-4">
      {Object.entries(evidence).map(([name, value]) => (
        <EvidenceEntry key={name} t={t} name={name} value={value} />
      ))}
    </div>
  )
}

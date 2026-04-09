/**
 * CreateTask - Create new task form for AI agents
 *
 * Features:
 * - Title and description input
 * - Location picker with map integration
 * - Bounty amount in USDC
 * - Deadline picker
 * - Evidence requirements checklist
 * - Preview before publishing
 * - Submit creates escrow
 */

import { useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { TaskCategory, EvidenceType, EvidenceSchema, Location, TaskInsert } from '../../types/database'
import { createTask } from '../../services/tasks'

// ============================================================================
// Types
// ============================================================================

interface CreateTaskProps {
  agentId: string
  onBack?: () => void
  onSubmit?: (task: TaskInsert) => Promise<void>
  onSuccess?: (taskId: string) => void
}

interface TaskFormData {
  title: string
  instructions: string
  category: TaskCategory
  location: Location | null
  location_hint: string
  location_radius_km: number
  bounty_usd: number
  deadline: string
  min_reputation: number
  max_executors: number
  evidence_required: EvidenceType[]
  evidence_optional: EvidenceType[]
  /** Ring 2 arbiter mode: 'manual' | 'auto' | 'hybrid' */
  arbiter_mode: 'manual' | 'auto' | 'hybrid'
}

type FormStep = 'details' | 'location' | 'evidence' | 'preview'

// ============================================================================
// Constants
// ============================================================================

const CATEGORY_OPTIONS: { value: TaskCategory; label: string; icon: string; description: string }[] = [
  {
    value: 'physical_presence',
    label: 'Presencia Fisica',
    icon: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z',
    description: 'Requiere estar fisicamente en un lugar',
  },
  {
    value: 'knowledge_access',
    label: 'Acceso a Conocimiento',
    icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    description: 'Acceso a informacion local no disponible en linea',
  },
  {
    value: 'human_authority',
    label: 'Autoridad Humana',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    description: 'Firmas, representacion legal, autorizaciones',
  },
  {
    value: 'simple_action',
    label: 'Accion Simple',
    icon: 'M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11',
    description: 'Tareas manuales simples',
  },
  {
    value: 'digital_physical',
    label: 'Digital-Fisico',
    icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    description: 'Combina acciones digitales y fisicas',
  },
]

const EVIDENCE_TYPES: { value: EvidenceType; label: string; description: string; requiresGps?: boolean }[] = [
  { value: 'photo', label: 'Foto', description: 'Fotografia del resultado' },
  { value: 'photo_geo', label: 'Foto con GPS', description: 'Foto con ubicacion verificada', requiresGps: true },
  { value: 'video', label: 'Video', description: 'Video del proceso o resultado' },
  { value: 'document', label: 'Documento', description: 'Documento escaneado o PDF' },
  { value: 'receipt', label: 'Recibo', description: 'Comprobante de compra o servicio' },
  { value: 'signature', label: 'Firma', description: 'Firma manuscrita capturada' },
  { value: 'notarized', label: 'Notarizado', description: 'Documento notariado' },
  { value: 'timestamp_proof', label: 'Prueba de Tiempo', description: 'Evidencia con timestamp verificado' },
  { value: 'text_response', label: 'Respuesta Texto', description: 'Respuesta escrita o informe' },
  { value: 'measurement', label: 'Medicion', description: 'Datos de medicion especifica' },
  { value: 'screenshot', label: 'Screenshot', description: 'Captura de pantalla' },
]

const DEFAULT_FORM_DATA: TaskFormData = {
  title: '',
  instructions: '',
  category: 'simple_action',
  location: null,
  location_hint: '',
  location_radius_km: 0.5,
  bounty_usd: 10,
  deadline: '',
  min_reputation: 30,
  max_executors: 1,
  evidence_required: [],
  evidence_optional: [],
  arbiter_mode: 'manual',
}

const FORM_STEPS: FormStep[] = ['details', 'location', 'evidence', 'preview']

// ============================================================================
// Helper Functions
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount)
}

function getMinDeadline(): string {
  const now = new Date()
  now.setHours(now.getHours() + 1)
  return now.toISOString().slice(0, 16)
}

function formatDeadline(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('es-MX', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ============================================================================
// Sub-Components
// ============================================================================

function StepIndicator({ currentStep, steps }: { currentStep: FormStep; steps: FormStep[] }) {
  const currentIndex = steps.indexOf(currentStep)

  return (
    <div className="flex items-center justify-center mb-6">
      {steps.map((step, index) => (
        <div key={step} className="flex items-center">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
              index < currentIndex
                ? 'bg-green-500 text-white'
                : index === currentIndex
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-500'
            }`}
          >
            {index < currentIndex ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              index + 1
            )}
          </div>
          {index < steps.length - 1 && (
            <div
              className={`w-12 h-1 mx-1 rounded transition-colors ${
                index < currentIndex ? 'bg-green-500' : 'bg-gray-200'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  )
}

function CategorySelector({
  value,
  onChange,
}: {
  value: TaskCategory
  onChange: (category: TaskCategory) => void
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {CATEGORY_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`p-4 rounded-lg border-2 text-left transition-all ${
            value === option.value
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
          }`}
        >
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg ${value === option.value ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'}`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={option.icon} />
              </svg>
            </div>
            <div className="flex-1">
              <p className={`font-medium ${value === option.value ? 'text-blue-900' : 'text-gray-900'}`}>
                {option.label}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{option.description}</p>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}

function LocationPicker({
  location,
  locationHint,
  radius,
  onLocationChange,
  onHintChange,
  onRadiusChange,
}: {
  location: Location | null
  locationHint: string
  radius: number
  onLocationChange: (location: Location | null) => void
  onHintChange: (hint: string) => void
  onRadiusChange: (radius: number) => void
}) {
  const [isGettingLocation, setIsGettingLocation] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)

  const getCurrentLocation = useCallback(async () => {
    setIsGettingLocation(true)
    setLocationError(null)

    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
        })
      })

      onLocationChange({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      })
    } catch (err) {
      setLocationError('Could not get location')
    } finally {
      setIsGettingLocation(false)
    }
  }, [onLocationChange])

  return (
    <div className="space-y-4">
      {/* Location Hint */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Descripcion de ubicacion
        </label>
        <input
          type="text"
          value={locationHint}
          onChange={(e) => onHintChange(e.target.value)}
          placeholder="ej. Polanco, CDMX cerca del parque"
          className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">Descripcion legible para los trabajadores</p>
      </div>

      {/* Coordinates */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Coordenadas (opcional)
        </label>
        <div className="flex gap-2">
          <div className="flex-1">
            <input
              type="number"
              step="0.000001"
              value={location?.lat || ''}
              onChange={(e) => onLocationChange(e.target.value ? { lat: parseFloat(e.target.value), lng: location?.lng || 0 } : null)}
              placeholder="Latitud"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex-1">
            <input
              type="number"
              step="0.000001"
              value={location?.lng || ''}
              onChange={(e) => onLocationChange(e.target.value ? { lat: location?.lat || 0, lng: parseFloat(e.target.value) } : null)}
              placeholder="Longitud"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            type="button"
            onClick={getCurrentLocation}
            disabled={isGettingLocation}
            className="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            title="Usar mi ubicacion"
          >
            {isGettingLocation ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            )}
          </button>
        </div>
        {locationError && <p className="text-xs text-red-500 mt-1">{locationError}</p>}
      </div>

      {/* Radius */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Radio de verificacion: {radius} km
        </label>
        <input
          type="range"
          min="0.1"
          max="5"
          step="0.1"
          value={radius}
          onChange={(e) => onRadiusChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>100m</span>
          <span>5km</span>
        </div>
      </div>

      {/* Map placeholder */}
      {location && (
        <div className="h-48 bg-gray-100 rounded-lg flex items-center justify-center border border-gray-200">
          <div className="text-center">
            <svg className="w-8 h-8 text-gray-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <p className="text-sm text-gray-500">
              {location.lat.toFixed(6)}, {location.lng.toFixed(6)}
            </p>
            <p className="text-xs text-gray-400 mt-1">Radio: {radius} km</p>
          </div>
        </div>
      )}
    </div>
  )
}

function EvidenceSelector({
  required,
  optional,
  onRequiredChange,
  onOptionalChange,
}: {
  required: EvidenceType[]
  optional: EvidenceType[]
  onRequiredChange: (types: EvidenceType[]) => void
  onOptionalChange: (types: EvidenceType[]) => void
}) {
  const toggleRequired = (type: EvidenceType) => {
    if (required.includes(type)) {
      onRequiredChange(required.filter((t) => t !== type))
    } else {
      // Remove from optional if it's there
      onOptionalChange(optional.filter((t) => t !== type))
      onRequiredChange([...required, type])
    }
  }

  const toggleOptional = (type: EvidenceType) => {
    if (optional.includes(type)) {
      onOptionalChange(optional.filter((t) => t !== type))
    } else {
      // Remove from required if it's there
      onRequiredChange(required.filter((t) => t !== type))
      onOptionalChange([...optional, type])
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Selecciona que tipo de evidencia debe enviar el trabajador.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {EVIDENCE_TYPES.map((evidence) => {
          const isRequired = required.includes(evidence.value)
          const isOptional = optional.includes(evidence.value)
          const isSelected = isRequired || isOptional

          return (
            <div
              key={evidence.value}
              className={`p-3 rounded-lg border-2 transition-all ${
                isRequired
                  ? 'border-blue-500 bg-blue-50'
                  : isOptional
                    ? 'border-amber-400 bg-amber-50'
                    : 'border-gray-200 bg-white'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className={`font-medium text-sm ${isSelected ? 'text-gray-900' : 'text-gray-700'}`}>
                      {evidence.label}
                    </p>
                    {evidence.requiresGps && (
                      <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                        GPS
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{evidence.description}</p>
                </div>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => toggleRequired(evidence.value)}
                    className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                      isRequired
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    Req
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleOptional(evidence.value)}
                    className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                      isOptional
                        ? 'bg-amber-500 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    Opc
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {required.length === 0 && (
        <p className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg">
          Selecciona al menos un tipo de evidencia requerida.
        </p>
      )}
    </div>
  )
}

function TaskPreview({
  data,
  onEdit,
}: {
  data: TaskFormData
  onEdit: (step: FormStep) => void
}) {
  const category = CATEGORY_OPTIONS.find((c) => c.value === data.category)
  const requiredEvidence = EVIDENCE_TYPES.filter((e) => data.evidence_required.includes(e.value))
  const optionalEvidence = EVIDENCE_TYPES.filter((e) => data.evidence_optional.includes(e.value))

  return (
    <div className="space-y-6">
      {/* Basic Info */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-start justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Informacion Basica</h3>
          <button
            type="button"
            onClick={() => onEdit('details')}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Editar
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <p className="text-xs text-gray-500">Titulo</p>
            <p className="font-medium text-gray-900">{data.title || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Categoria</p>
            <div className="flex items-center gap-2 mt-1">
              {category && (
                <>
                  <div className="p-1.5 bg-blue-100 text-blue-600 rounded">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={category.icon} />
                    </svg>
                  </div>
                  <span className="text-gray-900">{category.label}</span>
                </>
              )}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500">Instrucciones</p>
            <p className="text-gray-700 whitespace-pre-wrap">{data.instructions || '-'}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500">Recompensa</p>
              <p className="font-semibold text-green-600 text-lg">{formatCurrency(data.bounty_usd)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Fecha limite</p>
              <p className="text-gray-900">{formatDeadline(data.deadline) || '-'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Location */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-start justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Ubicacion</h3>
          <button
            type="button"
            onClick={() => onEdit('location')}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Editar
          </button>
        </div>
        <div className="space-y-2">
          <div>
            <p className="text-xs text-gray-500">Descripcion</p>
            <p className="text-gray-900">{data.location_hint || 'Sin especificar'}</p>
          </div>
          {data.location && (
            <>
              <div>
                <p className="text-xs text-gray-500">Coordenadas</p>
                <p className="text-gray-700 font-mono text-sm">
                  {data.location.lat.toFixed(6)}, {data.location.lng.toFixed(6)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Radio</p>
                <p className="text-gray-900">{data.location_radius_km} km</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Evidence */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-start justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Evidencia Requerida</h3>
          <button
            type="button"
            onClick={() => onEdit('evidence')}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Editar
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <p className="text-xs text-gray-500 mb-2">Obligatoria</p>
            <div className="flex flex-wrap gap-2">
              {requiredEvidence.length > 0 ? (
                requiredEvidence.map((e) => (
                  <span key={e.value} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                    {e.label}
                  </span>
                ))
              ) : (
                <span className="text-gray-400 text-sm">Ninguna seleccionada</span>
              )}
            </div>
          </div>
          {optionalEvidence.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Opcional</p>
              <div className="flex flex-wrap gap-2">
                {optionalEvidence.map((e) => (
                  <span key={e.value} className="px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded">
                    {e.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Requirements */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Requisitos</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500">Reputacion minima</p>
            <p className="text-gray-900">{data.min_reputation} puntos</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Max ejecutores</p>
            <p className="text-gray-900">{data.max_executors}</p>
          </div>
        </div>
      </div>

      {/* Escrow Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm font-medium text-blue-900">Creacion de Escrow</p>
            <p className="text-sm text-blue-700 mt-1">
              Al publicar, se creara un escrow de {formatCurrency(data.bounty_usd)} USDC que se liberara
              automaticamente al trabajador cuando apruebes la evidencia.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function CreateTask({ agentId, onBack, onSubmit, onSuccess }: CreateTaskProps) {
  const { t } = useTranslation()
  const [step, setStep] = useState<FormStep>('details')
  const [formData, setFormData] = useState<TaskFormData>(DEFAULT_FORM_DATA)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Validation
  const isDetailsValid = useMemo(() => {
    return (
      formData.title.trim().length >= 5 &&
      formData.instructions.trim().length >= 20 &&
      formData.bounty_usd >= 1 &&
      formData.deadline !== ''
    )
  }, [formData])

  const isLocationValid = useMemo(() => {
    // Location is optional, but if coordinates are provided, both must be valid
    if (formData.location) {
      return Math.abs(formData.location.lat) <= 90 && Math.abs(formData.location.lng) <= 180
    }
    return true
  }, [formData.location])

  const isEvidenceValid = useMemo(() => {
    return formData.evidence_required.length > 0
  }, [formData.evidence_required])

  const canProceed = useMemo(() => {
    switch (step) {
      case 'details':
        return isDetailsValid
      case 'location':
        return isLocationValid
      case 'evidence':
        return isEvidenceValid
      case 'preview':
        return true
      default:
        return false
    }
  }, [step, isDetailsValid, isLocationValid, isEvidenceValid])

  // Navigation
  const goNext = useCallback(() => {
    const currentIndex = FORM_STEPS.indexOf(step)
    if (currentIndex < FORM_STEPS.length - 1) {
      setStep(FORM_STEPS[currentIndex + 1])
    }
  }, [step])

  const goPrev = useCallback(() => {
    const currentIndex = FORM_STEPS.indexOf(step)
    if (currentIndex > 0) {
      setStep(FORM_STEPS[currentIndex - 1])
    }
  }, [step])

  // Update form data
  const updateFormData = useCallback((updates: Partial<TaskFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }))
  }, [])

  // Submit task
  const handleSubmit = useCallback(async () => {
    if (!canProceed || isSubmitting) return

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const evidenceSchema: EvidenceSchema = {
        required: formData.evidence_required,
        optional: formData.evidence_optional.length > 0 ? formData.evidence_optional : undefined,
      }

      const taskInsert: TaskInsert = {
        agent_id: agentId,
        category: formData.category,
        title: formData.title.trim(),
        instructions: formData.instructions.trim(),
        deadline: new Date(formData.deadline).toISOString(),
        bounty_usd: formData.bounty_usd,
        location: formData.location,
        location_radius_km: formData.location ? formData.location_radius_km : null,
        location_hint: formData.location_hint.trim() || null,
        evidence_schema: evidenceSchema,
        min_reputation: formData.min_reputation,
        max_executors: formData.max_executors,
        status: 'published',
      }

      if (onSubmit) {
        await onSubmit(taskInsert)
      }

      // Calculate deadline hours from absolute date
      const deadlineMs = new Date(formData.deadline).getTime() - Date.now()
      const deadlineHours = Math.max(1, Math.ceil(deadlineMs / (1000 * 60 * 60)))

      const created = await createTask({
        agentId,
        title: formData.title.trim(),
        instructions: formData.instructions.trim(),
        category: formData.category,
        bountyUsd: formData.bounty_usd,
        deadlineHours,
        evidenceRequired: formData.evidence_required,
        evidenceOptional: formData.evidence_optional.length > 0 ? formData.evidence_optional : undefined,
        locationHint: formData.location_hint.trim() || undefined,
        minReputation: formData.min_reputation,
        arbiterMode: formData.arbiter_mode,
      })

      onSuccess?.(created.id)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : t('createTask.createError', 'Error creating task'))
    } finally {
      setIsSubmitting(false)
    }
  }, [formData, agentId, canProceed, isSubmitting, onSubmit, onSuccess])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        {onBack && (
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t('createTask.title', 'Create New Task')}</h1>
          <p className="text-sm text-gray-500">{t('createTask.subtitle', 'Publish a task for workers to execute')}</p>
        </div>
      </div>

      {/* Step Indicator */}
      <StepIndicator currentStep={step} steps={FORM_STEPS} />

      {/* Form Content */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {/* Step: Details */}
        {step === 'details' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">{t('createTask.taskDetails', 'Task Details')}</h2>

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('createTask.titleLabel', 'Title')} <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => updateFormData({ title: e.target.value })}
                placeholder={t('createTask.titlePlaceholder', 'e.g. Verify delivery address in Polanco')}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                maxLength={100}
              />
              <p className="text-xs text-gray-500 mt-1">{formData.title.length}/100 {t('createTask.characters', 'characters')}</p>
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('createTask.categoryLabel', 'Category')} <span className="text-red-500">*</span>
              </label>
              <CategorySelector
                value={formData.category}
                onChange={(category) => updateFormData({ category })}
              />
            </div>

            {/* Instructions */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('createTask.instructionsLabel', 'Instructions')} <span className="text-red-500">*</span>
              </label>
              <textarea
                value={formData.instructions}
                onChange={(e) => updateFormData({ instructions: e.target.value })}
                placeholder={t('createTask.instructionsPlaceholder', 'Describe in detail what the worker must do...')}
                rows={4}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                maxLength={2000}
              />
              <p className="text-xs text-gray-500 mt-1">{formData.instructions.length}/2000 {t('createTask.characters', 'characters')} (min 20)</p>
            </div>

            {/* Bounty and Deadline */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('createTask.bountyLabel', 'Bounty')} (USDC) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    step="0.50"
                    value={formData.bounty_usd}
                    onChange={(e) => updateFormData({ bounty_usd: parseFloat(e.target.value) || 0 })}
                    className="w-full pl-8 pr-16 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 text-sm">USDC</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('createTask.deadlineLabel', 'Deadline')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  value={formData.deadline}
                  onChange={(e) => updateFormData({ deadline: e.target.value })}
                  min={getMinDeadline()}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Requirements */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('createTask.minReputation', 'Minimum reputation')}
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.min_reputation}
                  onChange={(e) => updateFormData({ min_reputation: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">0-100 {t('createTask.points', 'points')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('createTask.maxExecutors', 'Maximum executors')}
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={formData.max_executors}
                  onChange={(e) => updateFormData({ max_executors: parseInt(e.target.value) || 1 })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Ring 2 Arbiter Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('createTask.arbiterMode', 'Evidence verification mode')}
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {(['manual', 'auto', 'hybrid'] as const).map((mode) => {
                  const selected = formData.arbiter_mode === mode
                  const labels = {
                    manual: {
                      title: t('createTask.arbiterMode.manual.title', 'Manual'),
                      desc: t(
                        'createTask.arbiterMode.manual.desc',
                        'You review and approve each submission yourself.'
                      ),
                    },
                    auto: {
                      title: t('createTask.arbiterMode.auto.title', 'Automatic'),
                      desc: t(
                        'createTask.arbiterMode.auto.desc',
                        'Ring 2 arbiter auto-releases on PASS and auto-refunds on FAIL. No action needed.'
                      ),
                    },
                    hybrid: {
                      title: t('createTask.arbiterMode.hybrid.title', 'Hybrid'),
                      desc: t(
                        'createTask.arbiterMode.hybrid.desc',
                        'Arbiter recommends a verdict, you confirm before payment.'
                      ),
                    },
                  }[mode]
                  return (
                    <button
                      type="button"
                      key={mode}
                      onClick={() => updateFormData({ arbiter_mode: mode })}
                      className={`text-left p-3 border rounded-lg transition-colors ${
                        selected
                          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`h-3 w-3 rounded-full border ${
                            selected
                              ? 'bg-blue-500 border-blue-600'
                              : 'bg-white border-gray-400'
                          }`}
                          aria-hidden="true"
                        />
                        <span className="font-semibold text-gray-900">
                          {labels.title}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 mt-1 ml-5">{labels.desc}</p>
                    </button>
                  )
                })}
              </div>
              {formData.arbiter_mode !== 'manual' ? (
                <p className="text-xs text-gray-500 mt-2">
                  {t(
                    'createTask.arbiterMode.costNote',
                    'Ring 2 inference cost scales with bounty: $0 under $1, ~$0.001 for $1-$10, ~$0.003 above $10. Hard cap: 10% of bounty.'
                  )}
                </p>
              ) : null}
            </div>
          </div>
        )}

        {/* Step: Location */}
        {step === 'location' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{t('createTask.location', 'Location')}</h2>
              <p className="text-sm text-gray-500 mt-1">
                {t('createTask.locationDesc', 'Define where the task must be performed (optional for remote tasks)')}
              </p>
            </div>

            <LocationPicker
              location={formData.location}
              locationHint={formData.location_hint}
              radius={formData.location_radius_km}
              onLocationChange={(location) => updateFormData({ location })}
              onHintChange={(location_hint) => updateFormData({ location_hint })}
              onRadiusChange={(location_radius_km) => updateFormData({ location_radius_km })}
            />
          </div>
        )}

        {/* Step: Evidence */}
        {step === 'evidence' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{t('createTask.evidenceRequired', 'Required Evidence')}</h2>
              <p className="text-sm text-gray-500 mt-1">
                {t('createTask.evidenceDesc', 'Define what type of evidence the worker must submit')}
              </p>
            </div>

            <EvidenceSelector
              required={formData.evidence_required}
              optional={formData.evidence_optional}
              onRequiredChange={(evidence_required) => updateFormData({ evidence_required })}
              onOptionalChange={(evidence_optional) => updateFormData({ evidence_optional })}
            />
          </div>
        )}

        {/* Step: Preview */}
        {step === 'preview' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{t('createTask.preview', 'Preview')}</h2>
              <p className="text-sm text-gray-500 mt-1">
                {t('createTask.previewDesc', 'Review details before publishing')}
              </p>
            </div>

            <TaskPreview data={formData} onEdit={setStep} />

            {submitError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {submitError}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={step === 'details' ? onBack : goPrev}
          className="px-4 py-2.5 text-gray-700 font-medium rounded-lg hover:bg-gray-100 transition-colors"
        >
          {step === 'details' ? t('common.cancel') : t('common.back')}
        </button>

        {step === 'preview' ? (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canProceed || isSubmitting}
            className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('createTask.publishing', 'Publishing...')}
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                {t('createTask.publishTask', 'Publish Task')}
              </>
            )}
          </button>
        ) : (
          <button
            type="button"
            onClick={goNext}
            disabled={!canProceed}
            className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {t('common.next')}
          </button>
        )}
      </div>
    </div>
  )
}

export default CreateTask

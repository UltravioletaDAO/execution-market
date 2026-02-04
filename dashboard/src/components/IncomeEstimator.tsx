/**
 * IncomeEstimator - Calculadora de ingresos estimados para ejecutores
 *
 * Features:
 * - Slider de horas por semana (5-40)
 * - Selector de region (LATAM, NA, EU, APAC)
 * - Checkboxes de tipo de tarea
 * - Desglose de ingresos (bajo, promedio, alto)
 * - Comparacion con salario minimo regional
 */

import { useState, useMemo, useCallback } from 'react'

// Types
type Region = 'LATAM' | 'NA' | 'EU' | 'APAC'

interface TaskType {
  id: string
  name: string
  isPhysical: boolean
}

interface RegionConfig {
  name: string
  minRate: number
  maxRate: number
  avgTasksPerHour: number
  minWage: number
  minWageLabel: string
  currency: string
}

// Configuration
const TASK_TYPES: TaskType[] = [
  { id: 'verification', name: 'Verificacion fotografica', isPhysical: false },
  { id: 'data_collection', name: 'Recoleccion de datos', isPhysical: false },
  { id: 'survey', name: 'Encuestas', isPhysical: false },
  { id: 'delivery', name: 'Entregas', isPhysical: true },
  { id: 'mystery_shopping', name: 'Mystery shopping', isPhysical: true },
  { id: 'location_audit', name: 'Auditoria de ubicacion', isPhysical: true },
]

const REGION_CONFIG: Record<Region, RegionConfig> = {
  LATAM: {
    name: 'America Latina',
    minRate: 5,
    maxRate: 15,
    avgTasksPerHour: 2.5,
    minWage: 4, // Average across MX $6, CO $3, BR $4
    minWageLabel: 'Promedio LATAM',
    currency: 'USD',
  },
  NA: {
    name: 'Norteamerica',
    minRate: 10,
    maxRate: 30,
    avgTasksPerHour: 2,
    minWage: 15, // US federal effective
    minWageLabel: 'Salario minimo USA',
    currency: 'USD',
  },
  EU: {
    name: 'Europa',
    minRate: 10,
    maxRate: 30,
    avgTasksPerHour: 2,
    minWage: 12, // EU average
    minWageLabel: 'Promedio UE',
    currency: 'EUR',
  },
  APAC: {
    name: 'Asia-Pacifico',
    minRate: 6,
    maxRate: 18,
    avgTasksPerHour: 2.5,
    minWage: 5, // Average across region
    minWageLabel: 'Promedio APAC',
    currency: 'USD',
  },
}

const PHYSICAL_PREMIUM = 0.2 // 20% premium for physical tasks

interface IncomeEstimatorProps {
  className?: string
  onEstimateChange?: (estimate: {
    low: number
    average: number
    high: number
    hourlyRate: number
  }) => void
}

export function IncomeEstimator({ className = '', onEstimateChange }: IncomeEstimatorProps) {
  const [hoursPerWeek, setHoursPerWeek] = useState(20)
  const [region, setRegion] = useState<Region>('LATAM')
  const [selectedTaskTypes, setSelectedTaskTypes] = useState<string[]>(['verification', 'data_collection'])

  // Calculate physical task ratio
  const physicalRatio = useMemo(() => {
    if (selectedTaskTypes.length === 0) return 0
    const physicalCount = selectedTaskTypes.filter(
      (id) => TASK_TYPES.find((t) => t.id === id)?.isPhysical
    ).length
    return physicalCount / selectedTaskTypes.length
  }, [selectedTaskTypes])

  // Calculate estimates
  const estimates = useMemo(() => {
    const config = REGION_CONFIG[region]
    const hoursPerMonth = hoursPerWeek * 4.33 // Average weeks per month

    // Base rates with physical premium
    const physicalMultiplier = 1 + physicalRatio * PHYSICAL_PREMIUM
    const lowRate = config.minRate * physicalMultiplier
    const avgRate = ((config.minRate + config.maxRate) / 2) * physicalMultiplier
    const highRate = config.maxRate * physicalMultiplier

    // Tasks per month
    const tasksPerMonth = hoursPerMonth * config.avgTasksPerHour

    // Monthly estimates
    const lowEstimate = tasksPerMonth * lowRate * 0.7 // Conservative factor
    const avgEstimate = tasksPerMonth * avgRate
    const highEstimate = tasksPerMonth * highRate * 1.1 // Top performer bonus

    // Hourly rate equivalent
    const hourlyRate = avgEstimate / hoursPerMonth

    return {
      low: Math.round(lowEstimate),
      average: Math.round(avgEstimate),
      high: Math.round(highEstimate),
      hourlyRate: Math.round(hourlyRate * 100) / 100,
      tasksPerMonth: Math.round(tasksPerMonth),
    }
  }, [hoursPerWeek, region, physicalRatio])

  // Wage comparison
  const wageComparison = useMemo(() => {
    const config = REGION_CONFIG[region]
    const hoursPerMonth = hoursPerWeek * 4.33
    const minWageMonthly = config.minWage * hoursPerMonth

    const percentageDiff = ((estimates.average - minWageMonthly) / minWageMonthly) * 100

    return {
      minWageMonthly: Math.round(minWageMonthly),
      percentageDiff: Math.round(percentageDiff),
      label: config.minWageLabel,
    }
  }, [hoursPerWeek, region, estimates.average])

  // Toggle task type
  const toggleTaskType = useCallback((taskId: string) => {
    setSelectedTaskTypes((prev) =>
      prev.includes(taskId)
        ? prev.filter((id) => id !== taskId)
        : [...prev, taskId]
    )
  }, [])

  // Notify parent of changes
  useMemo(() => {
    if (onEstimateChange) {
      onEstimateChange({
        low: estimates.low,
        average: estimates.average,
        high: estimates.high,
        hourlyRate: estimates.hourlyRate,
      })
    }
  }, [estimates, onEstimateChange])

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900">
          Calculadora de Ingresos
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Estima cuanto podrias ganar con Execution Market
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Hours per week slider */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">
              Horas por semana
            </label>
            <span className="text-sm font-semibold text-blue-600">
              {hoursPerWeek} horas
            </span>
          </div>
          <input
            type="range"
            min={5}
            max={40}
            step={1}
            value={hoursPerWeek}
            onChange={(e) => setHoursPerWeek(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>5h</span>
            <span>20h</span>
            <span>40h</span>
          </div>
        </div>

        {/* Region selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Region
          </label>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value as Region)}
            className="w-full px-4 py-2.5 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white border-0"
          >
            {(Object.keys(REGION_CONFIG) as Region[]).map((key) => (
              <option key={key} value={key}>
                {REGION_CONFIG[key].name}
              </option>
            ))}
          </select>
        </div>

        {/* Task type checkboxes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Tipos de tarea preferidos
          </label>
          <div className="grid grid-cols-2 gap-2">
            {TASK_TYPES.map((task) => (
              <label
                key={task.id}
                className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedTaskTypes.includes(task.id)
                    ? 'bg-blue-50 border-2 border-blue-500'
                    : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedTaskTypes.includes(task.id)}
                  onChange={() => toggleTaskType(task.id)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{task.name}</span>
                {task.isPhysical && (
                  <span className="ml-auto text-xs px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded">
                    +20%
                  </span>
                )}
              </label>
            ))}
          </div>
          {physicalRatio > 0 && (
            <p className="text-xs text-orange-600 mt-2">
              * Tareas fisicas tienen un premium de +20%
            </p>
          )}
        </div>

        {/* Income breakdown */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-5">
          <h4 className="text-sm font-medium text-gray-700 mb-4">
            Ingreso Mensual Estimado
          </h4>

          <div className="grid grid-cols-3 gap-3 mb-4">
            {/* Low estimate */}
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500 mb-1">Conservador</div>
              <div className="text-xl font-bold text-gray-600">
                ${estimates.low}
              </div>
            </div>

            {/* Average estimate */}
            <div className="bg-blue-600 rounded-lg p-3 text-center text-white">
              <div className="text-xs text-blue-200 mb-1">Promedio</div>
              <div className="text-xl font-bold">
                ${estimates.average}
              </div>
            </div>

            {/* High estimate */}
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500 mb-1">Top Performer</div>
              <div className="text-xl font-bold text-green-600">
                ${estimates.high}
              </div>
            </div>
          </div>

          {/* Hourly rate */}
          <div className="flex items-center justify-between py-3 border-t border-gray-200">
            <span className="text-sm text-gray-600">Tarifa por hora equivalente</span>
            <span className="text-lg font-semibold text-gray-900">
              ${estimates.hourlyRate}/hr
            </span>
          </div>

          {/* Tasks estimate */}
          <div className="flex items-center justify-between py-3 border-t border-gray-200">
            <span className="text-sm text-gray-600">Tareas estimadas/mes</span>
            <span className="text-sm font-medium text-gray-700">
              ~{estimates.tasksPerMonth} tareas
            </span>
          </div>
        </div>

        {/* Regional comparison */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h4 className="text-sm font-medium text-gray-700 mb-3">
            Comparacion Regional
          </h4>

          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500">{wageComparison.label}</span>
                <span className="text-sm font-medium text-gray-600">
                  ${wageComparison.minWageMonthly}/mes
                </span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gray-400 rounded-full"
                  style={{ width: '40%' }}
                />
              </div>
            </div>

            <div className="text-center px-3">
              <div
                className={`text-2xl font-bold ${
                  wageComparison.percentageDiff >= 0
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}
              >
                {wageComparison.percentageDiff >= 0 ? '+' : ''}
                {wageComparison.percentageDiff}%
              </div>
              <div className="text-xs text-gray-500">
                {wageComparison.percentageDiff >= 0 ? 'por encima' : 'por debajo'}
              </div>
            </div>

            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500">Tu estimado</span>
                <span className="text-sm font-semibold text-blue-600">
                  ${estimates.average}/mes
                </span>
              </div>
              <div className="h-2 bg-blue-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full"
                  style={{
                    width: `${Math.min(
                      100,
                      (estimates.average / wageComparison.minWageMonthly) * 40
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="flex items-start gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-100">
          <svg
            className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div>
            <p className="text-sm text-yellow-800 font-medium">
              Aviso importante
            </p>
            <p className="text-xs text-yellow-700 mt-1">
              Estas estimaciones son aproximadas y dependen de la disponibilidad de
              tareas en tu zona, tu velocidad de trabajo, y la calidad de tus
              entregas. Los ingresos reales pueden variar significativamente. No
              garantizamos ningun nivel de ingresos.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default IncomeEstimator

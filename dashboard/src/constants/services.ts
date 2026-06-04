/**
 * Consumer service catalog for the Rappi-style "humans hire humans" flow.
 *
 * Each service maps a friendly es-CO label/icon to an existing physical
 * TaskCategory. The RequestService flow publishes an H2A task with
 * target_executor_type='human' (H2H), so a nearby human worker can pick it up.
 */
import type { TaskCategory } from '../types/database'

export interface ServiceDef {
  key: string
  icon: string
  label: string
  desc: string
  category: TaskCategory
  placeholder: string
}

export const SERVICES: ServiceDef[] = [
  {
    key: 'domicilio',
    icon: '🛵',
    label: 'Domicilio',
    desc: 'Entrega o recogida',
    category: 'physical_presence',
    placeholder: 'Recoger un pedido en X y entregarlo en Y antes de las 5pm.',
  },
  {
    key: 'mandado',
    icon: '📦',
    label: 'Mandado',
    desc: 'Compra o diligencia',
    category: 'simple_action',
    placeholder: 'Comprar X en el supermercado y traerlo a esta dirección.',
  },
  {
    key: 'tramite',
    icon: '🔑',
    label: 'Trámite',
    desc: 'Fila, firma o gestión',
    category: 'human_authority',
    placeholder: 'Hacer la fila en el banco y radicar este documento.',
  },
  {
    key: 'foto',
    icon: '📸',
    label: 'Foto / Evidencia',
    desc: 'Captura en sitio',
    category: 'digital_physical',
    placeholder: 'Tomar foto del estado del local en esta dirección.',
  },
  {
    key: 'hogar',
    icon: '🏠',
    label: 'Hogar',
    desc: 'Arreglos o limpieza',
    category: 'physical_presence',
    placeholder: 'Limpieza de apartamento de 2 habitaciones.',
  },
  {
    key: 'info',
    icon: '🔍',
    label: 'Info local',
    desc: 'Verificar algo en sitio',
    category: 'knowledge_access',
    placeholder: 'Verificar si el local está abierto y tomar nota de los precios.',
  },
]

export function getService(key: string): ServiceDef | undefined {
  return SERVICES.find((s) => s.key === key)
}

interface StatusBadgeProps {
  status: string
  variant?: 'task' | 'payment' | 'webhook' | 'default'
}

const taskColors: Record<string, string> = {
  published: 'bg-blue-500 text-white',
  accepted: 'bg-yellow-500 text-white',
  in_progress: 'bg-yellow-500 text-white',
  submitted: 'bg-purple-500 text-white',
  verifying: 'bg-indigo-500 text-white',
  completed: 'bg-green-500 text-white',
  expired: 'bg-gray-500 text-white',
  cancelled: 'bg-red-500 text-white',
  disputed: 'bg-red-600 text-white',
  partial: 'bg-teal-500 text-white',
}

const paymentColors: Record<string, string> = {
  confirmed: 'bg-green-500/20 text-green-400',
  pending: 'bg-yellow-500/20 text-yellow-400',
  failed: 'bg-red-500/20 text-red-400',
  deposit: 'bg-blue-500 text-white',
  release: 'bg-green-500 text-white',
  partial_release: 'bg-teal-500 text-white',
  fee: 'bg-purple-500 text-white',
  refund: 'bg-orange-500 text-white',
  withdrawal: 'bg-yellow-500 text-white',
  charge: 'bg-emerald-500 text-white',
  dispute: 'bg-red-500 text-white',
}

const webhookColors: Record<string, string> = {
  active: 'bg-green-500/20 text-green-400',
  inactive: 'bg-gray-500/20 text-gray-400',
  pending: 'bg-yellow-500/20 text-yellow-400',
  failed: 'bg-red-500/20 text-red-400',
  disabled: 'bg-gray-600/20 text-gray-500',
}

const defaultColors: Record<string, string> = {
  completed: 'bg-green-500/20 text-green-400',
  active: 'bg-green-500/20 text-green-400',
  success: 'bg-green-500/20 text-green-400',
  pending: 'bg-yellow-500/20 text-yellow-400',
  in_progress: 'bg-yellow-500/20 text-yellow-400',
  failed: 'bg-red-500/20 text-red-400',
  error: 'bg-red-500/20 text-red-400',
  cancelled: 'bg-red-500/20 text-red-400',
  published: 'bg-blue-500/20 text-blue-400',
  submitted: 'bg-purple-500/20 text-purple-400',
}

const colorMaps: Record<string, Record<string, string>> = {
  task: taskColors,
  payment: paymentColors,
  webhook: webhookColors,
  default: defaultColors,
}

export default function StatusBadge({ status, variant = 'default' }: StatusBadgeProps) {
  const map = colorMaps[variant] || defaultColors
  const colorClass = map[status] || 'bg-gray-500/20 text-gray-400'

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}

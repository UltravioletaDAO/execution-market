interface ToggleSwitchProps {
  enabled: boolean
  onChange: (val: boolean) => void
  disabled?: boolean
  label?: string
}

export default function ToggleSwitch({
  enabled,
  onChange,
  disabled = false,
  label,
}: ToggleSwitchProps) {
  const trackClass = enabled
    ? 'bg-em-600'
    : 'bg-gray-600'

  const knobTranslate = enabled
    ? 'translate-x-5'
    : 'translate-x-0'

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!enabled)}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full
          border-2 border-transparent transition-colors duration-200 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-em-500 focus:ring-offset-2 focus:ring-offset-gray-900
          ${trackClass}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <span
          aria-hidden="true"
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full
            bg-white shadow ring-0 transition duration-200 ease-in-out
            ${knobTranslate}
          `}
        />
      </button>
      {label && (
        <span className={`text-sm ${disabled ? 'text-gray-500' : 'text-gray-300'}`}>
          {label}
        </span>
      )}
    </div>
  )
}

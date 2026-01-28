/**
 * ThemeToggle Component
 *
 * A button component for toggling between light and dark modes.
 * Supports multiple variants and sizes.
 */

import { useTheme, type ThemeMode } from '../../hooks/useTheme';
import { cn } from '../../lib/utils';

export interface ThemeToggleProps {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Visual variant */
  variant?: 'icon' | 'button' | 'switch';
  /** Show labels */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

const sizeClasses = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-12 h-12',
};

const iconSizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

/**
 * Sun Icon
 */
function SunIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

/**
 * Moon Icon
 */
function MoonIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  );
}

/**
 * Monitor Icon (for system theme)
 */
function MonitorIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect width="20" height="14" x="2" y="3" rx="2" />
      <line x1="8" x2="16" y1="21" y2="21" />
      <line x1="12" x2="12" y1="17" y2="21" />
    </svg>
  );
}

/**
 * Icon-only theme toggle button
 */
export function ThemeToggle({
  size = 'md',
  variant = 'icon',
  showLabel = false,
  className,
}: ThemeToggleProps) {
  const { theme, isDark, toggleTheme } = useTheme();

  if (variant === 'switch') {
    return <ThemeSwitch size={size} className={className} />;
  }

  if (variant === 'button') {
    return (
      <ThemeButtonGroup
        size={size}
        showLabel={showLabel}
        className={className}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        'inline-flex items-center justify-center rounded-lg',
        'text-slate-600 dark:text-slate-400',
        'hover:bg-slate-100 dark:hover:bg-slate-800',
        'hover:text-slate-900 dark:hover:text-slate-100',
        'focus:outline-none focus:ring-2 focus:ring-chamba-500 focus:ring-offset-2',
        'focus:ring-offset-white dark:focus:ring-offset-slate-900',
        'transition-colors duration-200',
        sizeClasses[size],
        className
      )}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {isDark ? (
        <SunIcon className={iconSizeClasses[size]} />
      ) : (
        <MoonIcon className={iconSizeClasses[size]} />
      )}
    </button>
  );
}

/**
 * Theme switch (toggle style)
 */
export interface ThemeSwitchProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const switchSizeClasses = {
  sm: { track: 'w-11 h-6', thumb: 'w-4 h-4', translate: 'translate-x-5' },
  md: { track: 'w-14 h-7', thumb: 'w-5 h-5', translate: 'translate-x-7' },
  lg: { track: 'w-16 h-8', thumb: 'w-6 h-6', translate: 'translate-x-8' },
};

export function ThemeSwitch({ size = 'md', className }: ThemeSwitchProps) {
  const { isDark, toggleTheme } = useTheme();
  const { track, thumb, translate } = switchSizeClasses[size];

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      onClick={toggleTheme}
      className={cn(
        'relative inline-flex flex-shrink-0 cursor-pointer rounded-full',
        'border-2 border-transparent',
        'transition-colors duration-200 ease-in-out',
        'focus:outline-none focus:ring-2 focus:ring-chamba-500 focus:ring-offset-2',
        'focus:ring-offset-white dark:focus:ring-offset-slate-900',
        isDark ? 'bg-chamba-600' : 'bg-slate-200',
        track,
        className
      )}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      <span
        className={cn(
          'pointer-events-none relative inline-block rounded-full',
          'bg-white shadow-lg ring-0',
          'transition duration-200 ease-in-out',
          'flex items-center justify-center',
          thumb,
          isDark ? translate : 'translate-x-0'
        )}
      >
        {isDark ? (
          <MoonIcon className="w-3 h-3 text-chamba-600" />
        ) : (
          <SunIcon className="w-3 h-3 text-amber-500" />
        )}
      </span>
    </button>
  );
}

/**
 * Theme button group (light/dark/system)
 */
export interface ThemeButtonGroupProps {
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

const buttonGroupSizeClasses = {
  sm: 'p-1 text-xs',
  md: 'p-1.5 text-sm',
  lg: 'p-2 text-base',
};

const buttonSizeClasses = {
  sm: 'px-2 py-1',
  md: 'px-3 py-1.5',
  lg: 'px-4 py-2',
};

export function ThemeButtonGroup({
  size = 'md',
  showLabel = false,
  className,
}: ThemeButtonGroupProps) {
  const { themeMode, setTheme } = useTheme();

  const options: { value: ThemeMode; label: string; icon: typeof SunIcon }[] = [
    { value: 'light', label: 'Light', icon: SunIcon },
    { value: 'dark', label: 'Dark', icon: MoonIcon },
    { value: 'system', label: 'System', icon: MonitorIcon },
  ];

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-lg',
        'bg-slate-100 dark:bg-slate-800',
        buttonGroupSizeClasses[size],
        className
      )}
      role="radiogroup"
      aria-label="Theme selection"
    >
      {options.map(({ value, label, icon: Icon }) => {
        const isActive = themeMode === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => setTheme(value)}
            className={cn(
              'inline-flex items-center justify-center gap-1.5 rounded-md',
              'transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-chamba-500',
              buttonSizeClasses[size],
              isActive
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
            )}
            aria-label={`${label} theme`}
          >
            <Icon className={iconSizeClasses[size]} />
            {showLabel && <span>{label}</span>}
          </button>
        );
      })}
    </div>
  );
}

export default ThemeToggle;

/**
 * Input Component
 *
 * A flexible form input component with label, helper text, and error states.
 * Supports various input types and sizes.
 */

import {
  forwardRef,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
  type SelectHTMLAttributes,
  type ReactNode,
  useId,
} from 'react';
import { cn } from '../../lib/utils';

// ============================================================================
// Base Input Props
// ============================================================================

interface BaseInputProps {
  /** Label text */
  label?: string;
  /** Helper/description text */
  helperText?: string;
  /** Error message */
  error?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether the field is required */
  required?: boolean;
  /** Left addon/icon */
  leftAddon?: ReactNode;
  /** Right addon/icon */
  rightAddon?: ReactNode;
  /** Full width */
  fullWidth?: boolean;
}

// ============================================================================
// Input Component
// ============================================================================

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'>,
    BaseInputProps {}

const inputSizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-5 py-3 text-base',
};

const labelSizeClasses = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
};

const addonSizeClasses = {
  sm: 'px-2.5',
  md: 'px-3',
  lg: 'px-4',
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      helperText,
      error,
      size = 'md',
      required,
      leftAddon,
      rightAddon,
      fullWidth = true,
      className,
      id: providedId,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId ?? generatedId;
    const hasError = !!error;

    return (
      <div className={cn(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={id}
            className={cn(
              'block font-medium text-slate-700 dark:text-slate-300 mb-1.5',
              labelSizeClasses[size]
            )}
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          {leftAddon && (
            <div
              className={cn(
                'absolute inset-y-0 left-0 flex items-center',
                'text-slate-400 dark:text-slate-500',
                'pointer-events-none',
                addonSizeClasses[size]
              )}
            >
              {leftAddon}
            </div>
          )}
          <input
            ref={ref}
            id={id}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              error ? `${id}-error` : helperText ? `${id}-helper` : undefined
            }
            className={cn(
              // Base styles
              'w-full rounded-lg',
              'bg-white dark:bg-slate-800',
              'border',
              'text-slate-900 dark:text-slate-100',
              'placeholder:text-slate-400 dark:placeholder:text-slate-500',
              'transition-colors duration-200',
              // Focus styles
              'focus:outline-none focus:ring-2 focus:border-transparent',
              // Size
              inputSizeClasses[size],
              // Left addon padding
              leftAddon && (size === 'sm' ? 'pl-8' : size === 'lg' ? 'pl-12' : 'pl-10'),
              // Right addon padding
              rightAddon && (size === 'sm' ? 'pr-8' : size === 'lg' ? 'pr-12' : 'pr-10'),
              // Error state
              hasError
                ? 'border-red-500 dark:border-red-500 focus:ring-red-500'
                : 'border-slate-300 dark:border-slate-600 focus:ring-em-500',
              // Disabled state
              disabled && 'bg-slate-100 dark:bg-slate-700 cursor-not-allowed opacity-60',
              className
            )}
            {...props}
          />
          {rightAddon && (
            <div
              className={cn(
                'absolute inset-y-0 right-0 flex items-center',
                'text-slate-400 dark:text-slate-500',
                addonSizeClasses[size]
              )}
            >
              {rightAddon}
            </div>
          )}
        </div>
        {error && (
          <p
            id={`${id}-error`}
            className="mt-1.5 text-sm text-red-500 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {!error && helperText && (
          <p
            id={`${id}-helper`}
            className="mt-1.5 text-sm text-slate-500 dark:text-slate-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// ============================================================================
// Textarea Component
// ============================================================================

export interface TextareaProps
  extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'size'>,
    Omit<BaseInputProps, 'leftAddon' | 'rightAddon'> {
  /** Resize behavior */
  resize?: 'none' | 'vertical' | 'horizontal' | 'both';
}

const resizeClasses = {
  none: 'resize-none',
  vertical: 'resize-y',
  horizontal: 'resize-x',
  both: 'resize',
};

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      helperText,
      error,
      size = 'md',
      required,
      fullWidth = true,
      resize = 'vertical',
      rows = 4,
      className,
      id: providedId,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId ?? generatedId;
    const hasError = !!error;

    return (
      <div className={cn(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={id}
            className={cn(
              'block font-medium text-slate-700 dark:text-slate-300 mb-1.5',
              labelSizeClasses[size]
            )}
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          id={id}
          rows={rows}
          disabled={disabled}
          aria-invalid={hasError}
          aria-describedby={
            error ? `${id}-error` : helperText ? `${id}-helper` : undefined
          }
          className={cn(
            // Base styles
            'w-full rounded-lg',
            'bg-white dark:bg-slate-800',
            'border',
            'text-slate-900 dark:text-slate-100',
            'placeholder:text-slate-400 dark:placeholder:text-slate-500',
            'transition-colors duration-200',
            // Focus styles
            'focus:outline-none focus:ring-2 focus:border-transparent',
            // Size
            inputSizeClasses[size],
            // Resize
            resizeClasses[resize],
            // Error state
            hasError
              ? 'border-red-500 dark:border-red-500 focus:ring-red-500'
              : 'border-slate-300 dark:border-slate-600 focus:ring-em-500',
            // Disabled state
            disabled && 'bg-slate-100 dark:bg-slate-700 cursor-not-allowed opacity-60',
            className
          )}
          {...props}
        />
        {error && (
          <p
            id={`${id}-error`}
            className="mt-1.5 text-sm text-red-500 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {!error && helperText && (
          <p
            id={`${id}-helper`}
            className="mt-1.5 text-sm text-slate-500 dark:text-slate-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

// ============================================================================
// Select Component
// ============================================================================

export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'>,
    Omit<BaseInputProps, 'leftAddon' | 'rightAddon'> {
  /** Placeholder text */
  placeholder?: string;
  /** Select options */
  options?: Array<{
    value: string;
    label: string;
    disabled?: boolean;
  }>;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      helperText,
      error,
      size = 'md',
      required,
      fullWidth = true,
      placeholder,
      options,
      className,
      id: providedId,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId ?? generatedId;
    const hasError = !!error;

    return (
      <div className={cn(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={id}
            className={cn(
              'block font-medium text-slate-700 dark:text-slate-300 mb-1.5',
              labelSizeClasses[size]
            )}
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            id={id}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              error ? `${id}-error` : helperText ? `${id}-helper` : undefined
            }
            className={cn(
              // Base styles
              'w-full rounded-lg appearance-none cursor-pointer',
              'bg-white dark:bg-slate-800',
              'border',
              'text-slate-900 dark:text-slate-100',
              'transition-colors duration-200',
              // Focus styles
              'focus:outline-none focus:ring-2 focus:border-transparent',
              // Size
              inputSizeClasses[size],
              // Right padding for arrow
              'pr-10',
              // Error state
              hasError
                ? 'border-red-500 dark:border-red-500 focus:ring-red-500'
                : 'border-slate-300 dark:border-slate-600 focus:ring-em-500',
              // Disabled state
              disabled && 'bg-slate-100 dark:bg-slate-700 cursor-not-allowed opacity-60',
              className
            )}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options
              ? options.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    disabled={option.disabled}
                  >
                    {option.label}
                  </option>
                ))
              : children}
          </select>
          {/* Dropdown arrow */}
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <svg
              className="w-5 h-5 text-slate-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
        {error && (
          <p
            id={`${id}-error`}
            className="mt-1.5 text-sm text-red-500 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {!error && helperText && (
          <p
            id={`${id}-helper`}
            className="mt-1.5 text-sm text-slate-500 dark:text-slate-400"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

// ============================================================================
// Checkbox Component
// ============================================================================

export interface CheckboxProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size' | 'type'> {
  /** Label text */
  label?: string;
  /** Description text */
  description?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Error state */
  error?: boolean;
}

const checkboxSizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  (
    {
      label,
      description,
      size = 'md',
      error,
      className,
      id: providedId,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId ?? generatedId;

    return (
      <div className="flex items-start gap-3">
        <input
          ref={ref}
          id={id}
          type="checkbox"
          disabled={disabled}
          className={cn(
            'rounded',
            'border-slate-300 dark:border-slate-600',
            'bg-white dark:bg-slate-800',
            'text-em-500',
            'focus:ring-em-500 focus:ring-offset-0',
            'transition-colors',
            'cursor-pointer',
            error && 'border-red-500',
            disabled && 'cursor-not-allowed opacity-60',
            checkboxSizeClasses[size],
            className
          )}
          {...props}
        />
        {(label || description) && (
          <div className="flex-1">
            {label && (
              <label
                htmlFor={id}
                className={cn(
                  'font-medium text-slate-900 dark:text-slate-100 cursor-pointer',
                  size === 'sm' ? 'text-sm' : 'text-base',
                  disabled && 'cursor-not-allowed opacity-60'
                )}
              >
                {label}
              </label>
            )}
            {description && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                {description}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

// ============================================================================
// Radio Component
// ============================================================================

export interface RadioProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size' | 'type'> {
  /** Label text */
  label?: string;
  /** Description text */
  description?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Error state */
  error?: boolean;
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  (
    {
      label,
      description,
      size = 'md',
      error,
      className,
      id: providedId,
      disabled,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId ?? generatedId;

    return (
      <div className="flex items-start gap-3">
        <input
          ref={ref}
          id={id}
          type="radio"
          disabled={disabled}
          className={cn(
            'rounded-full',
            'border-slate-300 dark:border-slate-600',
            'bg-white dark:bg-slate-800',
            'text-em-500',
            'focus:ring-em-500 focus:ring-offset-0',
            'transition-colors',
            'cursor-pointer',
            error && 'border-red-500',
            disabled && 'cursor-not-allowed opacity-60',
            checkboxSizeClasses[size],
            className
          )}
          {...props}
        />
        {(label || description) && (
          <div className="flex-1">
            {label && (
              <label
                htmlFor={id}
                className={cn(
                  'font-medium text-slate-900 dark:text-slate-100 cursor-pointer',
                  size === 'sm' ? 'text-sm' : 'text-base',
                  disabled && 'cursor-not-allowed opacity-60'
                )}
              >
                {label}
              </label>
            )}
            {description && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                {description}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }
);

Radio.displayName = 'Radio';

// ============================================================================
// Search Input Component
// ============================================================================

export interface SearchInputProps extends Omit<InputProps, 'leftAddon' | 'rightAddon'> {
  /** Called when search is submitted */
  onSearch?: (value: string) => void;
  /** Show clear button */
  showClear?: boolean;
  /** Called when clear button is clicked */
  onClear?: () => void;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ onSearch, showClear, onClear, value, onChange, ...props }, ref) => {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && onSearch) {
        onSearch((e.target as HTMLInputElement).value);
      }
    };

    return (
      <Input
        ref={ref}
        type="search"
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        leftAddon={
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        }
        rightAddon={
          showClear && value ? (
            <button
              type="button"
              onClick={onClear}
              className="hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              aria-label="Clear search"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          ) : undefined
        }
        {...props}
      />
    );
  }
);

SearchInput.displayName = 'SearchInput';

export default Input;

/**
 * Dropdown Component
 *
 * A flexible dropdown/menu component with keyboard navigation and accessibility.
 * Supports different triggers, positions, and nested items.
 */

import {
  createContext,
  forwardRef,
  useContext,
  useState,
  useRef,
  useEffect,
  useCallback,
  type ReactNode,
  type HTMLAttributes,
  type KeyboardEvent,
  type MutableRefObject,
} from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../lib/utils';

// ============================================================================
// Context
// ============================================================================

interface DropdownContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  activeIndex: number;
  setActiveIndex: (index: number) => void;
}

const DropdownContext = createContext<DropdownContextValue | null>(null);

function useDropdown() {
  const context = useContext(DropdownContext);
  if (!context) {
    throw new Error('Dropdown components must be used within a Dropdown');
  }
  return context;
}

// ============================================================================
// Root Component
// ============================================================================

export interface DropdownProps {
  /** Child components */
  children: ReactNode;
  /** Whether the dropdown is controlled externally */
  open?: boolean;
  /** Called when open state changes */
  onOpenChange?: (open: boolean) => void;
  /** Additional class name */
  className?: string;
}

export function Dropdown({
  children,
  open: controlledOpen,
  onOpenChange,
  className,
}: DropdownProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const setOpen = useCallback(
    (newOpen: boolean) => {
      if (!isControlled) {
        setUncontrolledOpen(newOpen);
      }
      onOpenChange?.(newOpen);
      if (!newOpen) {
        setActiveIndex(-1);
      }
    },
    [isControlled, onOpenChange]
  );

  // Close on click outside
  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-dropdown]')) {
        setOpen(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [open, setOpen]);

  return (
    <DropdownContext.Provider value={{ open, setOpen, activeIndex, setActiveIndex }}>
      <div className={cn('relative inline-block', className)} data-dropdown>
        {children}
      </div>
    </DropdownContext.Provider>
  );
}

// ============================================================================
// Trigger Component
// ============================================================================

export interface DropdownTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  /** Whether the trigger is disabled */
  disabled?: boolean;
  /** Whether to render as a different element */
  asChild?: boolean;
}

export const DropdownTrigger = forwardRef<HTMLButtonElement, DropdownTriggerProps>(
  ({ onClick, onKeyDown, disabled, className, children, ...props }, ref) => {
    const { open, setOpen } = useDropdown();

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!disabled) {
        setOpen(!open);
        onClick?.(e);
      }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
      if (disabled) return;

      switch (e.key) {
        case 'Enter':
        case ' ':
        case 'ArrowDown':
          e.preventDefault();
          setOpen(true);
          break;
        case 'Escape':
          e.preventDefault();
          setOpen(false);
          break;
      }
      onKeyDown?.(e);
    };

    return (
      <button
        ref={ref}
        type="button"
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={className}
        {...props}
      >
        {children}
      </button>
    );
  }
);

DropdownTrigger.displayName = 'DropdownTrigger';

// ============================================================================
// Menu Component
// ============================================================================

export interface DropdownMenuProps extends HTMLAttributes<HTMLDivElement> {
  /** Position relative to trigger */
  position?: 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end' | 'left' | 'right';
  /** Alignment */
  align?: 'start' | 'center' | 'end';
  /** Width constraint */
  width?: 'auto' | 'trigger' | number;
  /** Use portal for rendering */
  portal?: boolean;
}

const positionClasses = {
  'bottom-start': 'top-full left-0 mt-1',
  'bottom-end': 'top-full right-0 mt-1',
  'top-start': 'bottom-full left-0 mb-1',
  'top-end': 'bottom-full right-0 mb-1',
  left: 'right-full top-0 mr-1',
  right: 'left-full top-0 ml-1',
};

export const DropdownMenu = forwardRef<HTMLDivElement, DropdownMenuProps>(
  (
    {
      position = 'bottom-start',
      align: _align = 'start',
      width = 'auto',
      portal = false,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const { open, setOpen, activeIndex, setActiveIndex } = useDropdown();
    const menuRef = useRef<HTMLDivElement>(null);
    const itemsRef = useRef<HTMLElement[]>([]);

    // Focus management
    useEffect(() => {
      if (open && menuRef.current) {
        menuRef.current.focus();
      }
    }, [open]);

    // Focus active item
    useEffect(() => {
      if (activeIndex >= 0 && itemsRef.current[activeIndex]) {
        itemsRef.current[activeIndex].focus();
      }
    }, [activeIndex]);

    const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
      const items = itemsRef.current.filter((item) => item && !item.hasAttribute('disabled'));
      const itemCount = items.length;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActiveIndex((activeIndex + 1) % itemCount);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActiveIndex(activeIndex <= 0 ? itemCount - 1 : activeIndex - 1);
          break;
        case 'Home':
          e.preventDefault();
          setActiveIndex(0);
          break;
        case 'End':
          e.preventDefault();
          setActiveIndex(itemCount - 1);
          break;
        case 'Escape':
          e.preventDefault();
          setOpen(false);
          break;
        case 'Tab':
          setOpen(false);
          break;
      }
    };

    if (!open) return null;

    const menuContent = (
      <div
        ref={(node) => {
          (menuRef as MutableRefObject<HTMLDivElement | null>).current = node;
          if (typeof ref === 'function') ref(node);
          else if (ref && 'current' in ref) (ref as MutableRefObject<HTMLDivElement | null>).current = node;
        }}
        role="menu"
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={cn(
          'absolute z-50 min-w-[12rem]',
          'bg-white dark:bg-slate-800',
          'rounded-lg shadow-lg',
          'border border-slate-200 dark:border-slate-700',
          'py-1',
          'animate-fade-in',
          'focus:outline-none',
          positionClasses[position],
          className
        )}
        style={typeof width === 'number' ? { width: `${width}px` } : undefined}
        {...props}
      >
        {children}
      </div>
    );

    if (portal) {
      return createPortal(menuContent, document.body);
    }

    return menuContent;
  }
);

DropdownMenu.displayName = 'DropdownMenu';

// ============================================================================
// Item Component
// ============================================================================

export interface DropdownItemProps extends HTMLAttributes<HTMLButtonElement> {
  /** Whether the item is disabled */
  disabled?: boolean;
  /** Icon to display before the label */
  icon?: ReactNode;
  /** Visual variant */
  variant?: 'default' | 'danger';
  /** Whether the item is currently selected */
  selected?: boolean;
  /** Close menu when clicked */
  closeOnClick?: boolean;
}

export const DropdownItem = forwardRef<HTMLButtonElement, DropdownItemProps>(
  (
    {
      disabled,
      icon,
      variant = 'default',
      selected,
      closeOnClick = true,
      onClick,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const { setOpen } = useDropdown();

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (disabled) return;
      onClick?.(e);
      if (closeOnClick) {
        setOpen(false);
      }
    };

    return (
      <button
        ref={ref}
        type="button"
        role="menuitem"
        disabled={disabled}
        onClick={handleClick}
        className={cn(
          'w-full flex items-center gap-2 px-4 py-2',
          'text-sm text-left',
          'transition-colors duration-150',
          'focus:outline-none',
          variant === 'danger'
            ? [
                'text-red-600 dark:text-red-400',
                'hover:bg-red-50 dark:hover:bg-red-900/20',
                'focus:bg-red-50 dark:focus:bg-red-900/20',
              ]
            : [
                'text-slate-700 dark:text-slate-300',
                'hover:bg-slate-100 dark:hover:bg-slate-700',
                'focus:bg-slate-100 dark:focus:bg-slate-700',
              ],
          selected && 'bg-slate-100 dark:bg-slate-700',
          disabled && 'opacity-50 cursor-not-allowed',
          className
        )}
        {...props}
      >
        {icon && <span className="flex-shrink-0 w-4 h-4">{icon}</span>}
        <span className="flex-1">{children}</span>
        {selected && (
          <svg
            className="w-4 h-4 text-em-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
      </button>
    );
  }
);

DropdownItem.displayName = 'DropdownItem';

// ============================================================================
// Label Component
// ============================================================================

export interface DropdownLabelProps extends HTMLAttributes<HTMLDivElement> {}

export const DropdownLabel = forwardRef<HTMLDivElement, DropdownLabelProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'px-4 py-2',
          'text-xs font-semibold uppercase tracking-wider',
          'text-slate-400 dark:text-slate-500',
          className
        )}
        {...props}
      />
    );
  }
);

DropdownLabel.displayName = 'DropdownLabel';

// ============================================================================
// Separator Component
// ============================================================================

export interface DropdownSeparatorProps extends HTMLAttributes<HTMLDivElement> {}

export const DropdownSeparator = forwardRef<HTMLDivElement, DropdownSeparatorProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        role="separator"
        className={cn(
          'my-1 border-t border-slate-200 dark:border-slate-700',
          className
        )}
        {...props}
      />
    );
  }
);

DropdownSeparator.displayName = 'DropdownSeparator';

// ============================================================================
// Checkbox Item Component
// ============================================================================

export interface DropdownCheckboxItemProps extends Omit<DropdownItemProps, 'selected'> {
  /** Whether the item is checked */
  checked?: boolean;
  /** Called when checked state changes */
  onCheckedChange?: (checked: boolean) => void;
}

export const DropdownCheckboxItem = forwardRef<HTMLButtonElement, DropdownCheckboxItemProps>(
  ({ checked, onCheckedChange, onClick, closeOnClick = false, children, ...props }, ref) => {
    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      onCheckedChange?.(!checked);
      onClick?.(e);
    };

    return (
      <DropdownItem
        ref={ref}
        onClick={handleClick}
        closeOnClick={closeOnClick}
        icon={
          <svg
            className={cn(
              'w-4 h-4',
              checked ? 'text-em-500' : 'text-transparent'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        }
        {...props}
      >
        {children}
      </DropdownItem>
    );
  }
);

DropdownCheckboxItem.displayName = 'DropdownCheckboxItem';

// ============================================================================
// Simple Dropdown (Convenience Component)
// ============================================================================

export interface SimpleDropdownProps {
  /** Trigger content */
  trigger: ReactNode;
  /** Menu items */
  items: Array<{
    label: string;
    onClick?: () => void;
    icon?: ReactNode;
    variant?: 'default' | 'danger';
    disabled?: boolean;
    separator?: boolean;
  }>;
  /** Position */
  position?: DropdownMenuProps['position'];
  /** Additional class for trigger */
  triggerClassName?: string;
  /** Additional class for menu */
  menuClassName?: string;
}

export function SimpleDropdown({
  trigger,
  items,
  position = 'bottom-end',
  triggerClassName,
  menuClassName,
}: SimpleDropdownProps) {
  return (
    <Dropdown>
      <DropdownTrigger
        className={cn(
          'inline-flex items-center justify-center p-2 rounded-lg',
          'text-slate-600 dark:text-slate-400',
          'hover:bg-slate-100 dark:hover:bg-slate-700',
          'transition-colors',
          triggerClassName
        )}
      >
        {trigger}
      </DropdownTrigger>
      <DropdownMenu position={position} className={menuClassName}>
        {items.map((item, index) =>
          item.separator ? (
            <DropdownSeparator key={index} />
          ) : (
            <DropdownItem
              key={index}
              onClick={item.onClick}
              icon={item.icon}
              variant={item.variant}
              disabled={item.disabled}
            >
              {item.label}
            </DropdownItem>
          )
        )}
      </DropdownMenu>
    </Dropdown>
  );
}

export default Dropdown;

/**
 * Reusable UI Components
 * A collection of styled, accessible UI primitives
 */

import React, { forwardRef, ButtonHTMLAttributes, InputHTMLAttributes, HTMLAttributes } from 'react';
import './ui.css';

// ============================================================================
// Card Component
// ============================================================================

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', variant = 'default', padding = 'md', children, ...props }, ref) => {
    const classes = [
      'ui-card',
      `ui-card--${variant}`,
      `ui-card--padding-${padding}`,
      className,
    ].filter(Boolean).join(' ');

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader: React.FC<HTMLAttributes<HTMLDivElement>> = ({
  className = '',
  children,
  ...props
}) => (
  <div className={`ui-card__header ${className}`} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<HTMLAttributes<HTMLHeadingElement>> = ({
  className = '',
  children,
  ...props
}) => (
  <h3 className={`ui-card__title ${className}`} {...props}>
    {children}
  </h3>
);

export const CardDescription: React.FC<HTMLAttributes<HTMLParagraphElement>> = ({
  className = '',
  children,
  ...props
}) => (
  <p className={`ui-card__description ${className}`} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<HTMLAttributes<HTMLDivElement>> = ({
  className = '',
  children,
  ...props
}) => (
  <div className={`ui-card__content ${className}`} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<HTMLAttributes<HTMLDivElement>> = ({
  className = '',
  children,
  ...props
}) => (
  <div className={`ui-card__footer ${className}`} {...props}>
    {children}
  </div>
);

// ============================================================================
// Badge Component
// ============================================================================

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'success' | 'warning';
  size?: 'sm' | 'md' | 'lg';
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant = 'default', size = 'md', children, ...props }, ref) => {
    const classes = [
      'ui-badge',
      `ui-badge--${variant}`,
      `ui-badge--${size}`,
      className,
    ].filter(Boolean).join(' ');

    return (
      <span ref={ref} className={classes} {...props}>
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

// Convenience component for severity badges
export const SeverityBadge: React.FC<{ severity?: string; className?: string }> = ({
  severity,
  className = '',
}) => {
  const normalizedSeverity = severity?.toLowerCase() ?? 'unknown';
  const validSeverities = ['critical', 'high', 'medium', 'low', 'info'];
  const variant = validSeverities.includes(normalizedSeverity)
    ? (normalizedSeverity as BadgeProps['variant'])
    : 'default';

  const label = normalizedSeverity.charAt(0).toUpperCase() + normalizedSeverity.slice(1);

  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
};

// ============================================================================
// Button Component
// ============================================================================

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = '',
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const classes = [
      'ui-button',
      `ui-button--${variant}`,
      `ui-button--${size}`,
      fullWidth && 'ui-button--full-width',
      loading && 'ui-button--loading',
      className,
    ].filter(Boolean).join(' ');

    return (
      <button
        ref={ref}
        className={classes}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <span className="ui-button__spinner" aria-hidden="true" />}
        <span className={loading ? 'ui-button__content--hidden' : ''}>{children}</span>
      </button>
    );
  }
);

Button.displayName = 'Button';

// ============================================================================
// Input Component
// ============================================================================

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, error, helperText, id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = Boolean(error);

    return (
      <div className={`ui-input-wrapper ${className}`}>
        {label && (
          <label htmlFor={inputId} className="ui-input__label">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`ui-input ${hasError ? 'ui-input--error' : ''}`}
          aria-invalid={hasError}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          {...props}
        />
        {error && (
          <span id={`${inputId}-error`} className="ui-input__error" role="alert">
            {error}
          </span>
        )}
        {helperText && !error && (
          <span id={`${inputId}-helper`} className="ui-input__helper">
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// ============================================================================
// Select Component
// ============================================================================

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps extends Omit<InputHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label?: string;
  options: SelectOption[];
  error?: string;
  onChange?: (value: string) => void;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = '', label, options, error, onChange, id, value, ...props }, ref) => {
    const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = Boolean(error);

    return (
      <div className={`ui-select-wrapper ${className}`}>
        {label && (
          <label htmlFor={selectId} className="ui-select__label">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={`ui-select ${hasError ? 'ui-select--error' : ''}`}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          aria-invalid={hasError}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <span className="ui-select__error" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

// ============================================================================
// Spinner / Loading Component
// ============================================================================

interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg';
}

export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className = '', ...props }) => (
  <div
    className={`ui-spinner ui-spinner--${size} ${className}`}
    role="status"
    aria-label="Loading"
    {...props}
  >
    <span className="ui-spinner__circle" />
  </div>
);

// ============================================================================
// Progress Bar Component
// ============================================================================

interface ProgressBarProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  showLabel?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  showLabel = false,
  variant = 'default',
  size = 'md',
  className = '',
  ...props
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  // Auto-determine variant based on value if not specified
  const autoVariant = variant === 'default'
    ? percentage >= 75 ? 'danger' : percentage >= 50 ? 'warning' : 'success'
    : variant;

  return (
    <div
      className={`ui-progress ui-progress--${size} ${className}`}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      {...props}
    >
      <div
        className={`ui-progress__bar ui-progress__bar--${autoVariant}`}
        style={{ width: `${percentage}%` }}
      />
      {showLabel && (
        <span className="ui-progress__label">{Math.round(percentage)}%</span>
      )}
    </div>
  );
};

// ============================================================================
// Tabs Component
// ============================================================================

interface Tab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = '' }) => (
  <div className={`ui-tabs ${className}`} role="tablist">
    {tabs.map((tab) => (
      <button
        key={tab.id}
        role="tab"
        aria-selected={activeTab === tab.id}
        aria-controls={`tabpanel-${tab.id}`}
        className={`ui-tabs__tab ${activeTab === tab.id ? 'ui-tabs__tab--active' : ''}`}
        onClick={() => onChange(tab.id)}
        disabled={tab.disabled}
      >
        {tab.icon && <span className="ui-tabs__icon">{tab.icon}</span>}
        {tab.label}
      </button>
    ))}
  </div>
);

interface TabPanelProps extends HTMLAttributes<HTMLDivElement> {
  tabId: string;
  activeTab: string;
}

export const TabPanel: React.FC<TabPanelProps> = ({
  tabId,
  activeTab,
  children,
  className = '',
  ...props
}) => {
  if (activeTab !== tabId) return null;

  return (
    <div
      id={`tabpanel-${tabId}`}
      role="tabpanel"
      aria-labelledby={tabId}
      className={`ui-tabs__panel ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

// ============================================================================
// Empty State Component
// ============================================================================

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => (
  <div className={`ui-empty-state ${className}`}>
    {icon && <div className="ui-empty-state__icon">{icon}</div>}
    <h3 className="ui-empty-state__title">{title}</h3>
    {description && <p className="ui-empty-state__description">{description}</p>}
    {action && <div className="ui-empty-state__action">{action}</div>}
  </div>
);

// ============================================================================
// Skeleton Loader Component
// ============================================================================

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  animation = 'pulse',
  className = '',
  style,
  ...props
}) => (
  <div
    className={`ui-skeleton ui-skeleton--${variant} ui-skeleton--${animation} ${className}`}
    style={{
      width: typeof width === 'number' ? `${width}px` : width,
      height: typeof height === 'number' ? `${height}px` : height,
      ...style,
    }}
    aria-hidden="true"
    {...props}
  />
);

// ============================================================================
// Tooltip Component
// ============================================================================

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = 'top',
  className = '',
}) => (
  <div className={`ui-tooltip-wrapper ${className}`}>
    {children}
    <div className={`ui-tooltip ui-tooltip--${position}`} role="tooltip">
      {content}
    </div>
  </div>
);

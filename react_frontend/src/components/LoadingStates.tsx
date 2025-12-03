/**
 * Loading States Components
 * Various loading indicators and skeleton screens
 */

import React from 'react';
import './LoadingStates.css';

// ============================================================================
// Page Loading
// ============================================================================

interface PageLoadingProps {
  message?: string;
}

export const PageLoading: React.FC<PageLoadingProps> = ({ message = 'Loading...' }) => (
  <div className="page-loading">
    <div className="page-loading__spinner">
      <div className="spinner spinner--lg" />
    </div>
    <p className="page-loading__message">{message}</p>
  </div>
);

// ============================================================================
// Skeleton Components
// ============================================================================

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1rem',
  borderRadius = '4px',
  className = '',
}) => (
  <div
    className={`skeleton ${className}`}
    style={{
      width: typeof width === 'number' ? `${width}px` : width,
      height: typeof height === 'number' ? `${height}px` : height,
      borderRadius,
    }}
  />
);

export const SkeletonText: React.FC<{ lines?: number }> = ({ lines = 3 }) => (
  <div className="skeleton-text">
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        width={i === lines - 1 ? '60%' : '100%'}
        height="0.875rem"
        className="skeleton-text__line"
      />
    ))}
  </div>
);

export const SkeletonCard: React.FC = () => (
  <div className="skeleton-card">
    <div className="skeleton-card__header">
      <Skeleton width={40} height={40} borderRadius="50%" />
      <div className="skeleton-card__header-text">
        <Skeleton width="60%" height="1rem" />
        <Skeleton width="40%" height="0.75rem" />
      </div>
    </div>
    <div className="skeleton-card__body">
      <SkeletonText lines={2} />
    </div>
    <div className="skeleton-card__footer">
      <Skeleton width="30%" height="2rem" borderRadius="6px" />
    </div>
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number; cols?: number }> = ({
  rows = 5,
  cols = 4,
}) => (
  <div className="skeleton-table">
    <div className="skeleton-table__header">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} height="1rem" />
      ))}
    </div>
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={rowIndex} className="skeleton-table__row">
        {Array.from({ length: cols }).map((_, colIndex) => (
          <Skeleton key={colIndex} height="0.875rem" />
        ))}
      </div>
    ))}
  </div>
);

// ============================================================================
// Dashboard Skeleton
// ============================================================================

export const DashboardSkeleton: React.FC = () => (
  <div className="dashboard-skeleton">
    {/* Stats Row */}
    <div className="dashboard-skeleton__stats">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="dashboard-skeleton__stat">
          <Skeleton width="50%" height="0.75rem" />
          <Skeleton width="40%" height="2rem" />
        </div>
      ))}
    </div>

    {/* Chart */}
    <div className="dashboard-skeleton__chart">
      <Skeleton width="30%" height="1.25rem" />
      <Skeleton height={200} borderRadius="8px" />
    </div>

    {/* Patient Cards */}
    <div className="dashboard-skeleton__cards">
      {Array.from({ length: 6 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  </div>
);

// ============================================================================
// Patient Detail Skeleton
// ============================================================================

export const PatientDetailSkeleton: React.FC = () => (
  <div className="patient-detail-skeleton">
    {/* Header */}
    <div className="patient-detail-skeleton__header">
      <Skeleton width={60} height={60} borderRadius="50%" />
      <div className="patient-detail-skeleton__header-info">
        <Skeleton width="40%" height="1.5rem" />
        <Skeleton width="25%" height="1rem" />
      </div>
    </div>

    {/* Tabs */}
    <div className="patient-detail-skeleton__tabs">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} width={80} height="2rem" borderRadius="6px" />
      ))}
    </div>

    {/* Content */}
    <div className="patient-detail-skeleton__content">
      <div className="patient-detail-skeleton__section">
        <Skeleton width="20%" height="1.25rem" />
        <SkeletonText lines={4} />
      </div>
      <div className="patient-detail-skeleton__section">
        <Skeleton width="25%" height="1.25rem" />
        <div className="patient-detail-skeleton__grid">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="patient-detail-skeleton__grid-item">
              <Skeleton width="60%" height="0.75rem" />
              <Skeleton width="40%" height="1.5rem" />
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

// ============================================================================
// Inline Loading
// ============================================================================

interface InlineLoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export const InlineLoading: React.FC<InlineLoadingProps> = ({
  size = 'md',
  text,
}) => (
  <span className={`inline-loading inline-loading--${size}`}>
    <span className="inline-loading__spinner" />
    {text && <span className="inline-loading__text">{text}</span>}
  </span>
);

// ============================================================================
// Button Loading
// ============================================================================

export const ButtonLoading: React.FC = () => (
  <span className="button-loading">
    <span className="button-loading__dot" />
    <span className="button-loading__dot" />
    <span className="button-loading__dot" />
  </span>
);

export default {
  PageLoading,
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTable,
  DashboardSkeleton,
  PatientDetailSkeleton,
  InlineLoading,
  ButtonLoading,
};

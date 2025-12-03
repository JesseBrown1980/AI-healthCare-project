/**
 * System Status Page
 * Health monitoring and adapter status dashboard
 */

import React, { useEffect, useState, useCallback } from 'react';
import { getHealthStatus, getAdaptersStatus } from '../api';
import type { HealthStatus } from '../api/types';
import { useNotification, useAutoRefresh } from '../hooks';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Spinner,
  ProgressBar,
} from '../components/ui';
import './SystemStatusPage.css';

// ============================================================================
// System Status Page Component
// ============================================================================

const SystemStatusPage: React.FC = () => {
  const { error: notifyError } = useNotification();

  // State
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [adapters, setAdapters] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchData = useCallback(async () => {
    try {
      const [healthData, adapterData] = await Promise.all([
        getHealthStatus().catch(() => null),
        getAdaptersStatus().catch(() => null),
      ]);

      if (healthData) setHealth(healthData);
      if (adapterData) setAdapters(adapterData);
      setLastUpdated(new Date());
    } catch (err) {
      notifyError('Fetch Error', 'Unable to fetch system status');
    } finally {
      setLoading(false);
    }
  }, [notifyError]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 30 seconds
  useAutoRefresh(fetchData, { enabled: true, interval: 30000, immediate: false });

  // ============================================================================
  // Render
  // ============================================================================

  if (loading) {
    return (
      <div className="system-status system-status--loading">
        <Spinner size="lg" />
        <p>Loading system status...</p>
      </div>
    );
  }

  return (
    <div className="system-status">
      {/* Header */}
      <header className="system-status__header">
        <div>
          <h1 className="system-status__title">System Status</h1>
          <p className="system-status__subtitle">
            Monitor system health, AI adapters, and service availability
          </p>
        </div>
        <div className="system-status__actions">
          {lastUpdated && (
            <span className="system-status__updated">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button variant="outline" onClick={fetchData}>
            ↻ Refresh
          </Button>
        </div>
      </header>

      {/* Overall Status */}
      <section className="system-status__overview">
        <Card className={`status-overview status-overview--${health?.status ?? 'unknown'}`}>
          <CardContent>
            <div className="status-overview__content">
              <div className="status-overview__indicator">
                <StatusIndicator status={health?.status ?? 'unknown'} size="lg" />
              </div>
              <div className="status-overview__info">
                <h2 className="status-overview__title">
                  {getStatusTitle(health?.status)}
                </h2>
                <p className="status-overview__message">
                  {health?.message ?? 'Unable to determine system status'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* System Metrics */}
      {health && (
        <section className="system-status__metrics">
          <Card>
            <CardHeader>
              <CardTitle>System Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="metrics-grid">
                <MetricCard
                  label="CPU Usage"
                  value={health.cpu_usage ?? 0}
                  unit="%"
                  max={100}
                  warning={70}
                  critical={90}
                />
                <MetricCard
                  label="Memory Usage"
                  value={health.memory_usage ?? 0}
                  unit="%"
                  max={100}
                  warning={80}
                  critical={95}
                />
                <MetricCard
                  label="Disk Usage"
                  value={health.disk_usage ?? 0}
                  unit="%"
                  max={100}
                  warning={80}
                  critical={95}
                />
                <MetricCard
                  label="Active Connections"
                  value={health.active_connections ?? 0}
                  unit=""
                  max={1000}
                  warning={800}
                  critical={950}
                />
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Services Status */}
      {health?.services && (
        <section className="system-status__services">
          <Card>
            <CardHeader>
              <CardTitle>Services</CardTitle>
              <CardDescription>Status of backend services and dependencies</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="services-grid">
                {Object.entries(health.services).map(([name, status]) => (
                  <ServiceCard key={name} name={name} status={status} />
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* AI Adapters */}
      <section className="system-status__adapters">
        <Card>
          <CardHeader>
            <CardTitle>AI Adapters (S-LoRA)</CardTitle>
            <CardDescription>
              Specialty-specific model adapters for clinical analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!adapters || !adapters.adapters || Object.keys(adapters.adapters).length === 0 ? (
              <p className="adapters-empty">No adapter information available</p>
            ) : (
              <div className="adapters-grid">
                {Object.values(adapters.adapters).map((adapter: any) => (
                  <AdapterCard key={adapter.name} adapter={adapter} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Version Info */}
      {health?.version && (
        <section className="system-status__version">
          <Card>
            <CardContent>
              <div className="version-info">
                <span className="version-info__label">API Version</span>
                <span className="version-info__value">{health.version}</span>
                {health.uptime && (
                  <>
                    <span className="version-info__label">Uptime</span>
                    <span className="version-info__value">{formatUptime(health.uptime)}</span>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
};

// ============================================================================
// Status Indicator Component
// ============================================================================

interface StatusIndicatorProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, size = 'md' }) => {
  const normalizedStatus = status.toLowerCase();
  const statusClass = ['healthy', 'ok', 'operational'].includes(normalizedStatus)
    ? 'healthy'
    : ['degraded', 'warning'].includes(normalizedStatus)
    ? 'degraded'
    : ['unhealthy', 'error', 'critical'].includes(normalizedStatus)
    ? 'unhealthy'
    : 'unknown';

  return (
    <div className={`status-indicator status-indicator--${statusClass} status-indicator--${size}`}>
      <span className="status-indicator__dot" />
    </div>
  );
};

// ============================================================================
// Metric Card Component
// ============================================================================

interface MetricCardProps {
  label: string;
  value: number;
  unit: string;
  max: number;
  warning: number;
  critical: number;
}

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  max,
  warning,
  critical,
}) => {
  const percentage = (value / max) * 100;
  const variant = value >= critical ? 'danger' : value >= warning ? 'warning' : 'success';

  return (
    <div className="metric-card">
      <div className="metric-card__header">
        <span className="metric-card__label">{label}</span>
        <span className={`metric-card__value metric-card__value--${variant}`}>
          {value.toFixed(1)}{unit}
        </span>
      </div>
      <ProgressBar value={percentage} variant={variant} size="sm" />
    </div>
  );
};

// ============================================================================
// Service Card Component
// ============================================================================

interface ServiceCardProps {
  name: string;
  status: string | boolean;
}

const ServiceCard: React.FC<ServiceCardProps> = ({ name, status }) => {
  const isHealthy =
    status === true ||
    status === 'healthy' ||
    status === 'ok' ||
    status === 'operational' ||
    status === 'connected';

  return (
    <div className={`service-card service-card--${isHealthy ? 'healthy' : 'unhealthy'}`}>
      <StatusIndicator status={isHealthy ? 'healthy' : 'unhealthy'} size="sm" />
      <span className="service-card__name">{formatServiceName(name)}</span>
      <Badge variant={isHealthy ? 'success' : 'critical'} size="sm">
        {typeof status === 'boolean' ? (status ? 'Online' : 'Offline') : status}
      </Badge>
    </div>
  );
};

// ============================================================================
// Adapter Card Component
// ============================================================================

interface AdapterCardProps {
  adapter: any;
}

const AdapterCard: React.FC<AdapterCardProps> = ({ adapter }) => {
  const isLoaded = adapter.loaded ?? adapter.status === 'loaded';

  return (
    <div className={`adapter-card adapter-card--${isLoaded ? 'loaded' : 'unloaded'}`}>
      <div className="adapter-card__header">
        <h4 className="adapter-card__name">{formatAdapterName(adapter.name)}</h4>
        <Badge variant={isLoaded ? 'success' : 'default'} size="sm">
          {isLoaded ? 'Loaded' : 'Not Loaded'}
        </Badge>
      </div>
      <div className="adapter-card__details">
        {adapter.specialty && (
          <div className="adapter-card__detail">
            <span className="adapter-card__label">Specialty</span>
            <span className="adapter-card__value">{adapter.specialty}</span>
          </div>
        )}
        {adapter.version && (
          <div className="adapter-card__detail">
            <span className="adapter-card__label">Version</span>
            <span className="adapter-card__value">{adapter.version}</span>
          </div>
        )}
        {adapter.size_mb !== undefined && (
          <div className="adapter-card__detail">
            <span className="adapter-card__label">Size</span>
            <span className="adapter-card__value">{adapter.size_mb.toFixed(1)} MB</span>
          </div>
        )}
        {adapter.last_used && (
          <div className="adapter-card__detail">
            <span className="adapter-card__label">Last Used</span>
            <span className="adapter-card__value">
              {new Date(adapter.last_used).toLocaleString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Helper Functions
// ============================================================================

function getStatusTitle(status?: string): string {
  if (!status) return 'Status Unknown';
  const normalized = status.toLowerCase();
  if (['healthy', 'ok', 'operational'].includes(normalized)) return 'All Systems Operational';
  if (['degraded', 'warning'].includes(normalized)) return 'Degraded Performance';
  if (['unhealthy', 'error', 'critical'].includes(normalized)) return 'System Issues Detected';
  return 'Status Unknown';
}

function formatServiceName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatAdapterName(name: string): string {
  return name
    .replace(/_adapter$/i, '')
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);

  return parts.join(' ') || '< 1m';
}

export default SystemStatusPage;

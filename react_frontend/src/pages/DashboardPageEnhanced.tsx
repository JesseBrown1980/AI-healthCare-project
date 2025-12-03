/**
 * Enhanced Dashboard Page
 * Rich patient dashboard with visualizations, filtering, and real-time updates
 */

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDashboardPatients, getDashboardSummary } from '../api';
import type { DashboardPatient, DashboardSummary } from '../api/types';
import { usePatientStore, useAppStore } from '../store';
import { useNotification, useDebounce, useAutoRefresh, useIsMobile } from '../hooks';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Input,
  Select,
  Badge,
  SeverityBadge,
  Spinner,
  EmptyState,
  Skeleton,
} from '../components/ui';
import {
  SeverityDistributionChart,
  RiskGauge,
  StatCard,
} from '../components/charts';
import './DashboardPage.css';

// ============================================================================
// Constants
// ============================================================================

const SEVERITY_OPTIONS = [
  { value: 'all', label: 'All Severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
  { value: 'info', label: 'Info' },
];

const SORT_OPTIONS = [
  { value: 'severity', label: 'Sort by Severity' },
  { value: 'risk', label: 'Sort by Risk Score' },
  { value: 'name', label: 'Sort by Name' },
  { value: 'recent', label: 'Recently Analyzed' },
];

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info', 'unknown'];

// ============================================================================
// Dashboard Page Component
// ============================================================================

const DashboardPageEnhanced: React.FC = () => {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const { success, error: notifyError } = useNotification();

  // Local state
  const [patients, setPatients] = useState<DashboardPatient[]>([]);
  const [, setSummary] = useState<DashboardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [sortBy, setSortBy] = useState('severity');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const debouncedSearch = useDebounce(searchQuery, 300);

  // Store
  const { filters, setFilter } = usePatientStore();
  const { preferences } = useAppStore();

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [patientsData, summaryData] = await Promise.all([
        getDashboardPatients(),
        getDashboardSummary().catch(() => []), // Summary is optional
      ]);

      setPatients(patientsData);
      setSummary(summaryData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(message);
      notifyError('Dashboard Error', message);
    } finally {
      setLoading(false);
    }
  }, [notifyError]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh
  useAutoRefresh(fetchData, {
    enabled: preferences.autoRefresh,
    interval: preferences.refreshInterval * 1000,
    immediate: false,
  });

  // ============================================================================
  // Computed Data
  // ============================================================================

  // Get unique specialties for filter dropdown
  const specialties = useMemo(() => {
    const unique = new Set<string>();
    patients.forEach((p) => {
      if (p.specialty) unique.add(p.specialty);
    });
    return [{ value: 'all', label: 'All Specialties' }, ...Array.from(unique).map((s) => ({ value: s.toLowerCase(), label: s }))];
  }, [patients]);

  // Filter and sort patients
  const filteredPatients = useMemo(() => {
    let result = [...patients];

    // Search filter
    if (debouncedSearch) {
      const query = debouncedSearch.toLowerCase();
      result = result.filter(
        (p) =>
          p.name?.toLowerCase().includes(query) ||
          p.patient_id.toLowerCase().includes(query) ||
          p.specialty?.toLowerCase().includes(query)
      );
    }

    // Severity filter
    if (severityFilter !== 'all') {
      result = result.filter(
        (p) => p.highest_alert_severity?.toLowerCase() === severityFilter
      );
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case 'severity':
          return getSeverityRank(a.highest_alert_severity) - getSeverityRank(b.highest_alert_severity);
        case 'risk':
          return (b.latest_risk_score ?? 0) - (a.latest_risk_score ?? 0);
        case 'name':
          return (a.name ?? a.patient_id).localeCompare(b.name ?? b.patient_id);
        case 'recent':
          return new Date(b.last_analyzed_at ?? 0).getTime() - new Date(a.last_analyzed_at ?? 0).getTime();
        default:
          return 0;
      }
    });

    return result;
  }, [patients, debouncedSearch, severityFilter, sortBy]);

  // Dashboard statistics
  const stats = useMemo(() => {
    const criticalCount = patients.filter((p) => p.highest_alert_severity?.toLowerCase() === 'critical').length;
    const highRiskCount = patients.filter((p) => (p.latest_risk_score ?? 0) >= 0.7).length;
    const avgRiskScore = patients.length > 0
      ? patients.reduce((sum, p) => sum + (p.latest_risk_score ?? 0), 0) / patients.length
      : 0;

    return {
      totalPatients: patients.length,
      criticalAlerts: criticalCount,
      highRiskPatients: highRiskCount,
      avgRiskScore: avgRiskScore,
    };
  }, [patients]);

  // ============================================================================
  // Handlers
  // ============================================================================

  const handlePatientClick = (patientId: string) => {
    navigate(`/patient/${patientId}`);
  };

  const handleRefresh = () => {
    fetchData();
    success('Refreshing', 'Dashboard data is being updated');
  };

  // ============================================================================
  // Render
  // ============================================================================

  if (loading && patients.length === 0) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard__header">
        <div className="dashboard__header-content">
          <h1 className="dashboard__title">Patient Dashboard</h1>
          <p className="dashboard__subtitle">
            Monitor patient risk scores and clinical alerts in real-time
          </p>
        </div>
        <div className="dashboard__header-actions">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            {loading ? <Spinner size="sm" /> : '↻'} Refresh
          </Button>
          <Button onClick={() => navigate('/query')}>
            Ask Medical Question
          </Button>
        </div>
      </header>

      {/* Statistics Cards */}
      <section className="dashboard__stats">
        <StatCard
          title="Total Patients"
          value={stats.totalPatients}
          icon={<span>👥</span>}
        />
        <StatCard
          title="Critical Alerts"
          value={stats.criticalAlerts}
          icon={<span>🚨</span>}
        />
        <StatCard
          title="High Risk"
          value={stats.highRiskPatients}
          icon={<span>⚠️</span>}
        />
        <div className="dashboard__stat-gauge">
          <RiskGauge
            value={stats.avgRiskScore}
            label="Avg Risk Score"
            size="md"
          />
        </div>
      </section>

      {/* Charts Section */}
      {patients.length > 0 && (
        <section className="dashboard__charts">
          <Card>
            <CardHeader>
              <CardTitle>Alert Severity Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <SeverityDistributionChart
                alerts={patients.map((p) => ({ severity: p.highest_alert_severity }))}
                height={200}
              />
            </CardContent>
          </Card>
        </section>
      )}

      {/* Filters */}
      <section className="dashboard__filters">
        <div className="dashboard__search">
          <Input
            placeholder="Search patients by name or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="dashboard__filter-controls">
          <Select
            options={SEVERITY_OPTIONS}
            value={severityFilter}
            onChange={setSeverityFilter}
          />
          <Select
            options={specialties}
            value={filters.specialty}
            onChange={(v) => setFilter('specialty', v)}
          />
          <Select
            options={SORT_OPTIONS}
            value={sortBy}
            onChange={setSortBy}
          />
          {!isMobile && (
            <div className="dashboard__view-toggle">
              <Button
                variant={viewMode === 'grid' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                Grid
              </Button>
              <Button
                variant={viewMode === 'list' ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
              >
                List
              </Button>
            </div>
          )}
        </div>
      </section>

      {/* Error State */}
      {error && (
        <div className="dashboard__error">
          <Card variant="outlined">
            <CardContent>
              <p className="dashboard__error-text">{error}</p>
              <Button variant="outline" onClick={fetchData}>
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Patient List */}
      {filteredPatients.length === 0 ? (
        <EmptyState
          icon={<span style={{ fontSize: '3rem' }}>🔍</span>}
          title="No patients found"
          description={
            searchQuery || severityFilter !== 'all'
              ? 'Try adjusting your search or filter criteria'
              : 'No patient data is available'
          }
          action={
            searchQuery || severityFilter !== 'all' ? (
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery('');
                  setSeverityFilter('all');
                }}
              >
                Clear Filters
              </Button>
            ) : undefined
          }
        />
      ) : viewMode === 'grid' ? (
        <section className="dashboard__patient-grid">
          {filteredPatients.map((patient) => (
            <PatientCard
              key={patient.patient_id}
              patient={patient}
              onClick={() => handlePatientClick(patient.patient_id)}
            />
          ))}
        </section>
      ) : (
        <section className="dashboard__patient-list">
          <PatientTable
            patients={filteredPatients}
            onPatientClick={handlePatientClick}
          />
        </section>
      )}

      {/* Results count */}
      <footer className="dashboard__footer">
        <p className="dashboard__results-count">
          Showing {filteredPatients.length} of {patients.length} patients
        </p>
      </footer>
    </div>
  );
};

// ============================================================================
// Patient Card Component
// ============================================================================

interface PatientCardProps {
  patient: DashboardPatient;
  onClick: () => void;
}

const PatientCard: React.FC<PatientCardProps> = ({ patient, onClick }) => {
  const riskScore = patient.latest_risk_score ?? 0;
  const riskPercent = Math.round(riskScore * 100);

  return (
    <Card variant="elevated" className="patient-card" onClick={onClick}>
      <div className="patient-card__header">
        <div className="patient-card__info">
          <h3 className="patient-card__name">{patient.name ?? 'Unknown Patient'}</h3>
          <p className="patient-card__id">ID: {patient.patient_id}</p>
        </div>
        <SeverityBadge severity={patient.highest_alert_severity} />
      </div>

      <div className="patient-card__body">
        {patient.specialty && (
          <Badge variant="info" size="sm">
            {patient.specialty}
          </Badge>
        )}

        <div className="patient-card__risk">
          <span className="patient-card__risk-label">Risk Score</span>
          <div className="patient-card__risk-bar">
            <div
              className="patient-card__risk-fill"
              style={{
                width: `${riskPercent}%`,
                backgroundColor: getRiskColor(riskPercent),
              }}
            />
          </div>
          <span className="patient-card__risk-value">{riskPercent}%</span>
        </div>
      </div>

      <div className="patient-card__footer">
        {patient.last_analyzed_at && (
          <span className="patient-card__timestamp">
            Analyzed: {formatRelativeTime(patient.last_analyzed_at)}
          </span>
        )}
        <Button variant="ghost" size="sm">
          View Details →
        </Button>
      </div>
    </Card>
  );
};

// ============================================================================
// Patient Table Component
// ============================================================================

interface PatientTableProps {
  patients: DashboardPatient[];
  onPatientClick: (id: string) => void;
}

const PatientTable: React.FC<PatientTableProps> = ({ patients, onPatientClick }) => {
  return (
    <div className="patient-table">
      <table>
        <thead>
          <tr>
            <th>Patient</th>
            <th>Specialty</th>
            <th>Severity</th>
            <th>Risk Score</th>
            <th>Last Analyzed</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {patients.map((patient) => (
            <tr key={patient.patient_id} onClick={() => onPatientClick(patient.patient_id)}>
              <td>
                <div className="patient-table__name">
                  <strong>{patient.name ?? 'Unknown'}</strong>
                  <span>{patient.patient_id}</span>
                </div>
              </td>
              <td>{patient.specialty ?? '—'}</td>
              <td>
                <SeverityBadge severity={patient.highest_alert_severity} />
              </td>
              <td>
                <span className="patient-table__risk">
                  {Math.round((patient.latest_risk_score ?? 0) * 100)}%
                </span>
              </td>
              <td>
                {patient.last_analyzed_at
                  ? formatRelativeTime(patient.last_analyzed_at)
                  : 'Never'}
              </td>
              <td>
                <Button variant="ghost" size="sm">
                  View
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ============================================================================
// Dashboard Skeleton (Loading State)
// ============================================================================

const DashboardSkeleton: React.FC = () => (
  <div className="dashboard">
    <header className="dashboard__header">
      <div>
        <Skeleton variant="text" width={200} height={32} />
        <Skeleton variant="text" width={300} height={20} style={{ marginTop: 8 }} />
      </div>
    </header>

    <section className="dashboard__stats">
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} variant="rectangular" height={100} />
      ))}
    </section>

    <section className="dashboard__patient-grid">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <Skeleton key={i} variant="rectangular" height={180} />
      ))}
    </section>
  </div>
);

// ============================================================================
// Helper Functions
// ============================================================================

function getSeverityRank(severity?: string): number {
  const normalized = severity?.toLowerCase() ?? 'unknown';
  const index = SEVERITY_ORDER.indexOf(normalized);
  return index === -1 ? SEVERITY_ORDER.length : index;
}

function getRiskColor(percentage: number): string {
  if (percentage < 20) return '#16a34a';
  if (percentage < 40) return '#65a30d';
  if (percentage < 60) return '#d97706';
  if (percentage < 80) return '#ea580c';
  return '#dc2626';
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default DashboardPageEnhanced;

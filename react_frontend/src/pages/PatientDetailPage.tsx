/**
 * Patient Detail Page
 * Comprehensive patient analysis view with all clinical data
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { analyzePatient } from '../api';
import type { AnalysisResult, Alert, Recommendation } from '../api/types';
import { usePatientStore } from '../store';
import { useNotification } from '../hooks';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  // CardFooter,
  Button,
  Badge,
  SeverityBadge,
  Select,
  Tabs,
  TabPanel,
  Spinner,
  EmptyState,
  ProgressBar,
  // Tooltip,
} from '../components/ui';
import {
  RiskScoreBarChart,
  RiskRadarChart,
  RiskGauge,
  SeverityDistributionChart,
} from '../components/charts';
import './PatientDetailPage.css';

// ============================================================================
// Constants
// ============================================================================

const SPECIALTY_OPTIONS = [
  { value: 'auto', label: 'Auto-detect Specialty' },
  { value: 'cardiology', label: 'Cardiology' },
  { value: 'oncology', label: 'Oncology' },
  { value: 'neurology', label: 'Neurology' },
  { value: 'endocrinology', label: 'Endocrinology' },
  { value: 'pulmonology', label: 'Pulmonology' },
  { value: 'gastroenterology', label: 'Gastroenterology' },
  { value: 'nephrology', label: 'Nephrology' },
  { value: 'rheumatology', label: 'Rheumatology' },
  { value: 'infectious_disease', label: 'Infectious Disease' },
];

const TABS = [
  { id: 'summary', label: 'Summary' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'risks', label: 'Risk Assessment' },
  { id: 'medications', label: 'Medications' },
  { id: 'recommendations', label: 'Recommendations' },
  { id: 'data', label: 'Patient Data' },
];

// ============================================================================
// Patient Detail Page Component
// ============================================================================

const PatientDetailPage: React.FC = () => {
  const { id: patientId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success, error: notifyError } = useNotification();

  // State
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('summary');
  const [specialty, setSpecialty] = useState('auto');
  const [includeRecommendations] = useState(true);

  // Store
  const { getAnalysisResult, setAnalysisResult } = usePatientStore();

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchAnalysis = useCallback(async (useCache = true) => {
    if (!patientId) return;

    // Check cache first
    if (useCache) {
      const cached = getAnalysisResult(patientId);
      if (cached) {
        setResult(cached);
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const analysisResult = await analyzePatient(patientId, {
        includeRecommendations,
        specialty: specialty === 'auto' ? undefined : specialty,
      });

      if (analysisResult?.status === 'error') {
        const errorMessage = (analysisResult as any).error ?? 'Analysis failed';
        setError(errorMessage);
        notifyError('Analysis Failed', errorMessage);
        return;
      }

      setResult(analysisResult);
      setAnalysisResult(patientId, analysisResult);
      success('Analysis Complete', `Patient ${patientId} analyzed successfully`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to analyze patient';
      setError(message);
      notifyError('Analysis Error', message);
    } finally {
      setLoading(false);
    }
  }, [patientId, specialty, includeRecommendations, getAnalysisResult, setAnalysisResult, success, notifyError]);

  // Initial load - check cache
  useEffect(() => {
    if (patientId) {
      const cached = getAnalysisResult(patientId);
      if (cached) {
        setResult(cached);
      }
    }
  }, [patientId, getAnalysisResult]);

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleAnalyze = () => {
    fetchAnalysis(false);
  };

  const handleExplainRisk = (riskType: string) => {
    navigate(`/explain/${patientId}?risk=${riskType}`);
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="patient-detail">
      {/* Header */}
      <header className="patient-detail__header">
        <div className="patient-detail__header-left">
          <Button variant="ghost" onClick={() => navigate(-1)}>
            ← Back
          </Button>
          <div className="patient-detail__title-section">
            <h1 className="patient-detail__title">
              {result?.summary?.patient_name ?? patientId ?? 'Patient Analysis'}
            </h1>
            <p className="patient-detail__subtitle">
              Patient ID: {patientId}
              {result?.analysis_timestamp && (
                <span> • Last analyzed: {formatDateTime(result.analysis_timestamp)}</span>
              )}
            </p>
          </div>
        </div>

        <div className="patient-detail__header-right">
          <Select
            options={SPECIALTY_OPTIONS}
            value={specialty}
            onChange={setSpecialty}
          />
          <Button
            onClick={handleAnalyze}
            loading={loading}
            disabled={loading}
          >
            {result ? 'Re-analyze' : 'Analyze Patient'}
          </Button>
        </div>
      </header>

      {/* Loading State */}
      {loading && !result && (
        <div className="patient-detail__loading">
          <Spinner size="lg" />
          <p>Analyzing patient data...</p>
          <p className="patient-detail__loading-hint">
            This may take a moment as we process clinical data and generate insights.
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !result && (
        <Card className="patient-detail__error">
          <CardContent>
            <EmptyState
              icon={<span style={{ fontSize: '3rem' }}>⚠️</span>}
              title="Analysis Failed"
              description={error}
              action={
                <Button onClick={handleAnalyze}>Try Again</Button>
              }
            />
          </CardContent>
        </Card>
      )}

      {/* No Analysis Yet */}
      {!loading && !error && !result && (
        <Card className="patient-detail__empty">
          <CardContent>
            <EmptyState
              icon={<span style={{ fontSize: '3rem' }}>🔬</span>}
              title="No Analysis Available"
              description="Click the button above to analyze this patient's clinical data and generate AI-powered insights."
              action={
                <Button onClick={handleAnalyze}>Start Analysis</Button>
              }
            />
          </CardContent>
        </Card>
      )}

      {/* Analysis Results */}
      {result && (
        <>
          {/* Quick Stats */}
          <section className="patient-detail__quick-stats">
            <QuickStatCard
              label="Overall Risk"
              value={`${Math.round((result.overall_risk_score ?? 0) * 100)}%`}
              severity={result.highest_alert_severity}
            />
            <QuickStatCard
              label="Active Alerts"
              value={result.alerts?.length ?? 0}
              icon="🚨"
            />
            <QuickStatCard
              label="Conditions"
              value={result.summary?.active_conditions_count ?? 0}
              icon="📋"
            />
            <QuickStatCard
              label="Medications"
              value={result.summary?.current_medications_count ?? 0}
              icon="💊"
            />
            {result.analysis_duration_seconds && (
              <QuickStatCard
                label="Analysis Time"
                value={`${result.analysis_duration_seconds.toFixed(1)}s`}
                icon="⏱️"
              />
            )}
          </section>

          {/* Tabs */}
          <Tabs tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

          {/* Tab Panels */}
          <div className="patient-detail__content">
            {/* Summary Tab */}
            <TabPanel tabId="summary" activeTab={activeTab}>
              <SummaryTab result={result} />
            </TabPanel>

            {/* Alerts Tab */}
            <TabPanel tabId="alerts" activeTab={activeTab}>
              <AlertsTab alerts={result.alerts ?? []} />
            </TabPanel>

            {/* Risk Assessment Tab */}
            <TabPanel tabId="risks" activeTab={activeTab}>
              <RiskAssessmentTab
                riskScores={result.risk_scores ?? {}}
                overallRisk={result.overall_risk_score ?? 0}
                onExplain={handleExplainRisk}
              />
            </TabPanel>

            {/* Medications Tab */}
            <TabPanel tabId="medications" activeTab={activeTab}>
              <MedicationsTab medicationReview={result.medication_review} />
            </TabPanel>

            {/* Recommendations Tab */}
            <TabPanel tabId="recommendations" activeTab={activeTab}>
              <RecommendationsTab recommendations={result.recommendations ?? []} />
            </TabPanel>

            {/* Patient Data Tab */}
            <TabPanel tabId="data" activeTab={activeTab}>
              <PatientDataTab patientData={result.patient_data} />
            </TabPanel>
          </div>
        </>
      )}
    </div>
  );
};

// ============================================================================
// Quick Stat Card Component
// ============================================================================

interface QuickStatCardProps {
  label: string;
  value: string | number;
  severity?: string;
  icon?: string;
}

const QuickStatCard: React.FC<QuickStatCardProps> = ({ label, value, severity, icon }) => (
  <div className="quick-stat">
    {icon && <span className="quick-stat__icon">{icon}</span>}
    {severity && <SeverityBadge severity={severity} />}
    <span className="quick-stat__value">{value}</span>
    <span className="quick-stat__label">{label}</span>
  </div>
);

// ============================================================================
// Summary Tab
// ============================================================================

interface SummaryTabProps {
  result: AnalysisResult;
}

const SummaryTab: React.FC<SummaryTabProps> = ({ result }) => {
  const summary = result.summary;

  return (
    <div className="summary-tab">
      <div className="summary-tab__grid">
        {/* Patient Info */}
        <Card>
          <CardHeader>
            <CardTitle>Patient Information</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="info-list">
              <div className="info-list__item">
                <dt>Name</dt>
                <dd>{summary?.patient_name ?? 'Unknown'}</dd>
              </div>
              <div className="info-list__item">
                <dt>Age</dt>
                <dd>{summary?.age ?? 'Unknown'}</dd>
              </div>
              <div className="info-list__item">
                <dt>Gender</dt>
                <dd>{summary?.gender ?? 'Unknown'}</dd>
              </div>
              <div className="info-list__item">
                <dt>Active Conditions</dt>
                <dd>{summary?.active_conditions_count ?? 0}</dd>
              </div>
              <div className="info-list__item">
                <dt>Current Medications</dt>
                <dd>{summary?.current_medications_count ?? 0}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* Risk Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="risk-overview">
              <RiskGauge
                value={result.overall_risk_score ?? 0}
                label="Overall Risk"
                size="lg"
              />
            </div>
          </CardContent>
        </Card>

        {/* Narrative Summary */}
        <Card className="summary-tab__narrative">
          <CardHeader>
            <CardTitle>Clinical Summary</CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.narrative_summary ? (
              <p className="narrative-text">{summary.narrative_summary}</p>
            ) : (
              <p className="narrative-text narrative-text--empty">
                No narrative summary available.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Key Conditions */}
        <Card>
          <CardHeader>
            <CardTitle>Key Conditions</CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.key_conditions?.length ? (
              <div className="tag-list">
                {summary.key_conditions.map((condition, i) => (
                  <Badge key={i} variant="warning">
                    {condition}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="empty-text">No key conditions identified.</p>
            )}
          </CardContent>
        </Card>

        {/* Key Medications */}
        <Card>
          <CardHeader>
            <CardTitle>Key Medications</CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.key_medications?.length ? (
              <div className="tag-list">
                {summary.key_medications.map((med, i) => (
                  <Badge key={i} variant="info">
                    {med}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="empty-text">No key medications identified.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// ============================================================================
// Alerts Tab
// ============================================================================

interface AlertsTabProps {
  alerts: Alert[];
}

const AlertsTab: React.FC<AlertsTabProps> = ({ alerts }) => {
  if (alerts.length === 0) {
    return (
      <EmptyState
        icon={<span style={{ fontSize: '3rem' }}>✅</span>}
        title="No Active Alerts"
        description="No clinical alerts were generated for this patient."
      />
    );
  }

  // Sort by severity
  const sortedAlerts = [...alerts].sort((a, b) => {
    const order = ['critical', 'high', 'medium', 'low', 'info'];
    return order.indexOf(a.severity?.toLowerCase() ?? 'info') - order.indexOf(b.severity?.toLowerCase() ?? 'info');
  });

  return (
    <div className="alerts-tab">
      <div className="alerts-tab__header">
        <h3>{alerts.length} Alert{alerts.length !== 1 ? 's' : ''}</h3>
        <SeverityDistributionChart alerts={alerts} height={150} />
      </div>

      <div className="alerts-tab__list">
        {sortedAlerts.map((alert, index) => (
          <Card key={alert.id ?? index} className="alert-card">
            <CardContent>
              <div className="alert-card__header">
                <SeverityBadge severity={alert.severity} />
                {alert.code && <Badge variant="default">{alert.code}</Badge>}
                {alert.timestamp && (
                  <span className="alert-card__timestamp">{alert.timestamp}</span>
                )}
              </div>
              <p className="alert-card__message">{alert.message}</p>
              {alert.recommendation && (
                <div className="alert-card__recommendation">
                  <strong>Recommendation:</strong> {alert.recommendation}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Risk Assessment Tab
// ============================================================================

interface RiskAssessmentTabProps {
  riskScores: Record<string, number>;
  overallRisk: number;
  onExplain: (riskType: string) => void;
}

const RiskAssessmentTab: React.FC<RiskAssessmentTabProps> = ({
  riskScores,
  // overallRisk is available but not currently used
  onExplain,
}) => {
  const hasRiskScores = Object.keys(riskScores).length > 0;

  if (!hasRiskScores) {
    return (
      <EmptyState
        icon={<span style={{ fontSize: '3rem' }}>📊</span>}
        title="No Risk Scores Available"
        description="Risk assessment data is not available for this patient."
      />
    );
  }

  return (
    <div className="risk-tab">
      <div className="risk-tab__grid">
        {/* Bar Chart */}
        <Card className="risk-tab__chart">
          <CardHeader>
            <CardTitle>Risk Score Breakdown</CardTitle>
            <CardDescription>
              Individual risk scores across different clinical domains
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RiskScoreBarChart riskScores={riskScores} height={350} />
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card className="risk-tab__radar">
          <CardHeader>
            <CardTitle>Risk Profile</CardTitle>
            <CardDescription>
              Comparative view of all risk factors
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RiskRadarChart riskScores={riskScores} height={300} />
          </CardContent>
        </Card>

        {/* Individual Risk Cards */}
        <div className="risk-tab__cards">
          {Object.entries(riskScores)
            .filter(([, value]) => value !== undefined)
            .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
            .map(([key, value]) => (
              <Card key={key} className="risk-card">
                <CardContent>
                  <div className="risk-card__header">
                    <span className="risk-card__name">{formatRiskLabel(key)}</span>
                    <span className="risk-card__value">
                      {Math.round((value ?? 0) * 100)}%
                    </span>
                  </div>
                  <ProgressBar value={(value ?? 0) * 100} size="md" />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onExplain(key)}
                    className="risk-card__explain"
                  >
                    Explain this score →
                  </Button>
                </CardContent>
              </Card>
            ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Medications Tab
// ============================================================================

interface MedicationsTabProps {
  medicationReview?: AnalysisResult['medication_review'];
}

const MedicationsTab: React.FC<MedicationsTabProps> = ({ medicationReview }) => {
  if (!medicationReview) {
    return (
      <EmptyState
        icon={<span style={{ fontSize: '3rem' }}>💊</span>}
        title="No Medication Data"
        description="Medication review data is not available for this patient."
      />
    );
  }

  const { total_medications, potential_issues, medications } = medicationReview;

  return (
    <div className="medications-tab">
      {/* Stats */}
      <div className="medications-tab__stats">
        <Card>
          <CardContent>
            <div className="med-stat">
              <span className="med-stat__value">{total_medications ?? 0}</span>
              <span className="med-stat__label">Total Medications</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <div className="med-stat">
              <span className="med-stat__value med-stat__value--warning">
                {potential_issues?.length ?? 0}
              </span>
              <span className="med-stat__label">Potential Issues</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Potential Issues */}
      {potential_issues && potential_issues.length > 0 && (
        <Card className="medications-tab__issues">
          <CardHeader>
            <CardTitle>⚠️ Potential Issues</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="issues-list">
              {potential_issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Medication List */}
      <Card>
        <CardHeader>
          <CardTitle>Medication List</CardTitle>
        </CardHeader>
        <CardContent>
          {medications && medications.length > 0 ? (
            <div className="medication-list">
              {medications.map((med, i) => (
                <div key={i} className="medication-item">
                  <div className="medication-item__main">
                    <Badge
                      variant={med.status === 'active' ? 'success' : 'default'}
                      size="sm"
                    >
                      {med.status ?? 'Unknown'}
                    </Badge>
                    <span className="medication-item__name">
                      {med.name ?? 'Unknown Medication'}
                    </span>
                  </div>
                  {(med.dosage || med.frequency) && (
                    <span className="medication-item__details">
                      {[med.dosage, med.frequency].filter(Boolean).join(' • ')}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-text">No medications on record.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ============================================================================
// Recommendations Tab
// ============================================================================

interface RecommendationsTabProps {
  recommendations: Recommendation[];
}

const RecommendationsTab: React.FC<RecommendationsTabProps> = ({ recommendations }) => {
  if (recommendations.length === 0) {
    return (
      <EmptyState
        icon={<span style={{ fontSize: '3rem' }}>💡</span>}
        title="No Recommendations"
        description="No clinical recommendations were generated for this patient."
      />
    );
  }

  // Sort by priority
  const sortedRecs = [...recommendations].sort((a, b) => {
    const order = ['high', 'medium', 'low'];
    return order.indexOf(a.priority ?? 'low') - order.indexOf(b.priority ?? 'low');
  });

  return (
    <div className="recommendations-tab">
      <div className="recommendations-tab__list">
        {sortedRecs.map((rec, index) => (
          <Card key={rec.id ?? index} className="recommendation-card">
            <CardContent>
              <div className="recommendation-card__header">
                <h4 className="recommendation-card__title">
                  {rec.title ?? `Recommendation ${index + 1}`}
                </h4>
                {rec.priority && (
                  <Badge
                    variant={
                      rec.priority === 'high'
                        ? 'critical'
                        : rec.priority === 'medium'
                        ? 'warning'
                        : 'info'
                    }
                  >
                    {rec.priority} priority
                  </Badge>
                )}
              </div>
              {rec.recommendation && (
                <p className="recommendation-card__body">{rec.recommendation}</p>
              )}
              {rec.rationale && (
                <div className="recommendation-card__rationale">
                  <strong>Rationale:</strong> {rec.rationale}
                </div>
              )}
              {rec.sources && rec.sources.length > 0 && (
                <div className="recommendation-card__sources">
                  <strong>Sources:</strong>
                  <ul>
                    {rec.sources.map((source, i) => (
                      <li key={i}>{source.title ?? source.url ?? 'Source'}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Patient Data Tab (Raw FHIR Data Browser)
// ============================================================================

interface PatientDataTabProps {
  patientData?: AnalysisResult['patient_data'];
}

const PatientDataTab: React.FC<PatientDataTabProps> = ({ patientData }) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  if (!patientData) {
    return (
      <EmptyState
        icon={<span style={{ fontSize: '3rem' }}>📁</span>}
        title="No Patient Data"
        description="Raw patient data is not available."
      />
    );
  }

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const sections = [
    { key: 'patient', label: 'Patient Demographics', icon: '👤' },
    { key: 'conditions', label: 'Conditions', icon: '🏥' },
    { key: 'medications', label: 'Medications', icon: '💊' },
    { key: 'observations', label: 'Observations', icon: '📊' },
    { key: 'diagnostic_reports', label: 'Diagnostic Reports', icon: '📋' },
    { key: 'allergies', label: 'Allergies', icon: '⚠️' },
    { key: 'procedures', label: 'Procedures', icon: '🔧' },
    { key: 'immunizations', label: 'Immunizations', icon: '💉' },
    { key: 'care_plans', label: 'Care Plans', icon: '📝' },
  ];

  return (
    <div className="patient-data-tab">
      {sections.map(({ key, label, icon }) => {
        const data = patientData[key as keyof typeof patientData];
        const hasData = data && (Array.isArray(data) ? data.length > 0 : Object.keys(data).length > 0);
        const isExpanded = expandedSections.has(key);

        return (
          <Card key={key} className="data-section">
            <button
              className="data-section__header"
              onClick={() => toggleSection(key)}
              aria-expanded={isExpanded}
            >
              <span className="data-section__icon">{icon}</span>
              <span className="data-section__label">{label}</span>
              <Badge variant={hasData ? 'success' : 'default'} size="sm">
                {Array.isArray(data) ? data.length : hasData ? '1' : '0'}
              </Badge>
              <span className="data-section__chevron">{isExpanded ? '▼' : '▶'}</span>
            </button>
            {isExpanded && (
              <div className="data-section__content">
                {hasData ? (
                  <pre className="data-section__json">
                    {JSON.stringify(data, null, 2)}
                  </pre>
                ) : (
                  <p className="empty-text">No data available.</p>
                )}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
};

// ============================================================================
// Helper Functions
// ============================================================================

function formatDateTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString();
}

function formatRiskLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/risk$/i, '')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default PatientDetailPage;

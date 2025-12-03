/**
 * Explainability Page
 * SHAP-based model explainability visualizations
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { request } from '../api';
import type { ExplainResponse } from '../api/types';
import { useNotification } from '../hooks';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Select,
  Spinner,
  EmptyState,
  Badge,
} from '../components/ui';
import { ShapWaterfallChart } from '../components/charts';
import './ExplainabilityPage.css';

// ============================================================================
// Constants
// ============================================================================

const RISK_TYPE_OPTIONS = [
  { value: 'cardiovascular_risk', label: 'Cardiovascular Risk' },
  { value: 'readmission_risk', label: 'Readmission Risk' },
  { value: 'mortality_risk', label: 'Mortality Risk' },
  { value: 'fall_risk', label: 'Fall Risk' },
  { value: 'sepsis_risk', label: 'Sepsis Risk' },
  { value: 'overall_risk', label: 'Overall Risk' },
];

// ============================================================================
// Explainability Page Component
// ============================================================================

const ExplainabilityPage: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { error: notifyError } = useNotification();

  // State
  const [riskType, setRiskType] = useState(searchParams.get('risk') ?? 'cardiovascular_risk');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchExplanation = useCallback(async () => {
    if (!patientId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await request<ExplainResponse>(`/explain/${patientId}`, {
        method: 'GET',
      });

      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch explanation';
      setError(message);
      notifyError('Explanation Error', message);
    } finally {
      setLoading(false);
    }
  }, [patientId, notifyError]);

  useEffect(() => {
    fetchExplanation();
  }, [fetchExplanation]);

  // ============================================================================
  // Computed Data
  // ============================================================================

  const shapData = result
    ? result.feature_names.map((feature, index) => ({
        feature,
        value: result.shap_values[index],
      }))
    : [];

  const positiveContributors = shapData
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value);

  const negativeContributors = shapData
    .filter((d) => d.value < 0)
    .sort((a, b) => a.value - b.value);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="explainability-page">
      {/* Header */}
      <header className="explainability-page__header">
        <div className="explainability-page__header-left">
          <Button variant="ghost" onClick={() => navigate(-1)}>
            ← Back
          </Button>
          <div>
            <h1 className="explainability-page__title">Risk Score Explanation</h1>
            <p className="explainability-page__subtitle">
              Understanding what factors contribute to the patient's risk assessment
            </p>
          </div>
        </div>

        <div className="explainability-page__header-right">
          <Select
            label="Risk Type"
            options={RISK_TYPE_OPTIONS}
            value={riskType}
            onChange={setRiskType}
          />
        </div>
      </header>

      {/* Loading State */}
      {loading && (
        <div className="explainability-page__loading">
          <Spinner size="lg" />
          <p>Generating explanation...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <Card>
          <CardContent>
            <EmptyState
              icon={<span style={{ fontSize: '3rem' }}>⚠️</span>}
              title="Explanation Unavailable"
              description={error}
              action={<Button onClick={fetchExplanation}>Try Again</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && !loading && (
        <div className="explainability-page__content">
          {/* Overview */}
          <div className="explainability-page__overview">
            <Card className="overview-card">
              <CardContent>
                <div className="overview-card__content">
                  <span className="overview-card__label">Patient ID</span>
                  <span className="overview-card__value">{result.patient_id}</span>
                </div>
              </CardContent>
            </Card>
            <Card className="overview-card">
              <CardContent>
                <div className="overview-card__content">
                  <span className="overview-card__label">Risk Score</span>
                  <span className="overview-card__value overview-card__value--large">
                    {result.risk_score !== undefined
                      ? `${Math.round(result.risk_score * 100)}%`
                      : 'N/A'}
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card className="overview-card">
              <CardContent>
                <div className="overview-card__content">
                  <span className="overview-card__label">Base Value</span>
                  <span className="overview-card__value">
                    {result.base_value !== undefined
                      ? `${Math.round(result.base_value * 100)}%`
                      : 'N/A'}
                  </span>
                </div>
              </CardContent>
            </Card>
            <Card className="overview-card">
              <CardContent>
                <div className="overview-card__content">
                  <span className="overview-card__label">Model</span>
                  <span className="overview-card__value">{result.model_type ?? 'Unknown'}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* SHAP Waterfall Chart */}
          <Card className="explainability-page__chart">
            <CardHeader>
              <CardTitle>Feature Contributions (SHAP Values)</CardTitle>
              <CardDescription>
                This chart shows how each clinical feature contributes to the final risk score.
                Green bars indicate factors that decrease risk, while red bars indicate factors
                that increase risk.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {shapData.length > 0 ? (
                <ShapWaterfallChart
                  shapValues={shapData}
                  baseValue={result.base_value}
                  height={Math.max(400, shapData.length * 35)}
                />
              ) : (
                <EmptyState
                  title="No SHAP Data"
                  description="Feature contribution data is not available."
                />
              )}
            </CardContent>
          </Card>

          {/* Feature Lists */}
          <div className="explainability-page__features">
            {/* Risk Increasing Factors */}
            <Card className="feature-list feature-list--negative">
              <CardHeader>
                <CardTitle>
                  <span className="feature-list__icon">🔺</span>
                  Risk-Increasing Factors
                </CardTitle>
              </CardHeader>
              <CardContent>
                {positiveContributors.length > 0 ? (
                  <ul className="feature-list__items">
                    {positiveContributors.map((item, index) => (
                      <li key={index} className="feature-list__item">
                        <span className="feature-list__name">
                          {formatFeatureName(item.feature)}
                        </span>
                        <Badge variant="critical">
                          +{(item.value * 100).toFixed(1)}%
                        </Badge>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="feature-list__empty">No risk-increasing factors identified.</p>
                )}
              </CardContent>
            </Card>

            {/* Risk Decreasing Factors */}
            <Card className="feature-list feature-list--positive">
              <CardHeader>
                <CardTitle>
                  <span className="feature-list__icon">🔻</span>
                  Risk-Decreasing Factors
                </CardTitle>
              </CardHeader>
              <CardContent>
                {negativeContributors.length > 0 ? (
                  <ul className="feature-list__items">
                    {negativeContributors.map((item, index) => (
                      <li key={index} className="feature-list__item">
                        <span className="feature-list__name">
                          {formatFeatureName(item.feature)}
                        </span>
                        <Badge variant="success">
                          {(item.value * 100).toFixed(1)}%
                        </Badge>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="feature-list__empty">No risk-decreasing factors identified.</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Interpretation Guide */}
          <Card className="explainability-page__guide">
            <CardHeader>
              <CardTitle>How to Interpret This Explanation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="interpretation-guide">
                <div className="interpretation-guide__item">
                  <h4>Base Value</h4>
                  <p>
                    The base value represents the average prediction across all patients in the
                    training data. It's the starting point before considering any patient-specific
                    features.
                  </p>
                </div>
                <div className="interpretation-guide__item">
                  <h4>SHAP Values</h4>
                  <p>
                    SHAP (SHapley Additive exPlanations) values show how much each feature
                    contributes to pushing the prediction away from the base value. Positive
                    values increase the risk score, while negative values decrease it.
                  </p>
                </div>
                <div className="interpretation-guide__item">
                  <h4>Clinical Relevance</h4>
                  <p>
                    The features with the largest absolute SHAP values have the most impact on
                    this patient's risk score. These are the factors that clinicians should
                    prioritize when developing care plans.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Helper Functions
// ============================================================================

function formatFeatureName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

export default ExplainabilityPage;

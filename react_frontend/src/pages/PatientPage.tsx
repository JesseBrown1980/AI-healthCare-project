import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { analyzePatient } from "../api";
import type { AnalysisResult } from "../api/types";
import "./PatientPage.css";

const severityOrder = ["critical", "high", "medium", "low", "info", "unknown"] as const;

const specialtyOptions = [
  { label: "Auto-detect", value: "auto" },
  { label: "Cardiology", value: "cardiology" },
  { label: "Oncology", value: "oncology" },
  { label: "Neurology", value: "neurology" },
  { label: "Endocrinology", value: "endocrinology" },
  { label: "Pulmonology", value: "pulmonology" },
  { label: "Gastroenterology", value: "gastroenterology" },
  { label: "Nephrology", value: "nephrology" },
];

const formatSeverity = (severity?: string) => {
  if (!severity) return "Unknown";
  const normalized = severity.toLowerCase();
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
};

const getSeverityClass = (severity?: string) => {
  const normalized = severity?.toLowerCase();
  return severityOrder.includes(normalized as (typeof severityOrder)[number])
    ? normalized
    : "unknown";
};

const formatRiskLabel = (key: string) => {
  return key
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const PatientPage = () => {
  const params = useParams();
  const [patientId, setPatientId] = useState(params.id ?? "");
  const [specialty, setSpecialty] = useState("auto");
  const [includeRecommendations, setIncludeRecommendations] = useState(true);
  const [includeReasoning, setIncludeReasoning] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    if (params.id) {
      setPatientId(params.id);
    }
  }, [params.id]);

  const riskScores = useMemo(() => {
    return Object.entries(result?.risk_scores ?? {});
  }, [result?.risk_scores]);

  const handleAnalyze = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!patientId.trim()) {
      setError("Please enter a Patient ID.");
      setResult(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const apiResult = await analyzePatient(patientId.trim(), {
        includeRecommendations,
        specialty: specialty === "auto" ? undefined : specialty,
      });

      if (apiResult?.status === "error") {
        const message = (apiResult as unknown as { error?: string }).error;
        setError(message ?? "Analysis failed to complete.");
        setResult(null);
        return;
      }

      setResult(apiResult);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to analyze patient.";
      setError(message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const renderAlerts = () => {
    if (!result?.alerts?.length) {
      return <div className="patient__state">No alerts were returned.</div>;
    }

    return (
      <div className="patient__alert-list">
        {result.alerts.map((alert, index) => {
          const severityClass = getSeverityClass(alert.severity);
          return (
            <div key={`${alert.message}-${index}`} className="patient__alert-card">
              <div className="patient__alert-top">
                <span className={`severity-badge severity-badge--${severityClass}`}>
                  {formatSeverity(alert.severity)}
                </span>
                {alert.code && <span className="patient__pill">Code: {alert.code}</span>}
                {alert.timestamp && <span className="patient__pill">{alert.timestamp}</span>}
              </div>
              <div className="patient__alert-body">
                <p className="patient__alert-message">{alert.message}</p>
                {alert.recommendation && (
                  <p className="patient__alert-recommendation">
                    Recommendation: {alert.recommendation}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderRiskScores = () => {
    if (!riskScores.length) {
      return <div className="patient__state">No risk scores available.</div>;
    }

    return (
      <div className="patient__risk-grid">
        {riskScores.map(([name, value]) => {
          const normalized = Number.isFinite(value) ? Math.max(0, Math.min(value, 1)) : 0;
          const percent = Math.round(normalized * 100);
          return (
            <div key={name} className="patient__risk-item">
              <div className="patient__risk-header">
                <span className="patient__risk-name">{formatRiskLabel(name)}</span>
                <span className="patient__risk-score">{percent}%</span>
              </div>
              <div className="patient__risk-bar">
                <span className="patient__risk-bar-value" style={{ width: `${percent}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderMedicationReview = () => {
    if (!result?.medication_review) {
      return <div className="patient__state">No medication review provided.</div>;
    }

    const { total_medications, potential_issues, medications } = result.medication_review;

    return (
      <div className="patient__medication">
        <div className="patient__stat-cards">
          <div className="patient__stat-card">
            <span className="patient__stat-label">Total Medications</span>
            <span className="patient__stat-value">{total_medications ?? "—"}</span>
          </div>
          <div className="patient__stat-card">
            <span className="patient__stat-label">Potential Issues</span>
            <span className="patient__stat-value">{potential_issues?.length ?? 0}</span>
          </div>
        </div>

        {potential_issues?.length ? (
          <div className="patient__list-block">
            <h4>Potential Issues</h4>
            <ul>
              {potential_issues.map((issue, idx) => (
                <li key={`${issue}-${idx}`}>{issue}</li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="patient__state patient__state--muted">No potential issues noted.</div>
        )}

        {medications?.length ? (
          <div className="patient__list-block">
            <h4>Medications</h4>
            <ul>
              {medications.map((med, idx) => (
                <li key={`${med.name ?? "med"}-${idx}`}>
                  <span className="patient__pill">{med.status ?? "Unknown"}</span>
                  <span className="patient__list-text">{med.name ?? "Unspecified medication"}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    );
  };

  const renderRecommendations = () => {
    if (!includeRecommendations) {
      return <div className="patient__state patient__state--muted">Recommendations were skipped.</div>;
    }

    if (!result?.recommendations?.length) {
      return <div className="patient__state">No recommendations returned.</div>;
    }

    return (
      <div className="patient__recommendations">
        {result.recommendations.map((rec, idx) => (
          <div key={`${rec.title ?? "rec"}-${idx}`} className="patient__recommendation-card">
            <div className="patient__recommendation-header">
              <h4>{rec.title ?? "Recommendation"}</h4>
              {rec.priority && <span className="patient__pill">{rec.priority}</span>}
            </div>
            {rec.recommendation && <p className="patient__recommendation-body">{rec.recommendation}</p>}
            {includeReasoning && rec.rationale && (
              <p className="patient__recommendation-rationale">Reasoning: {rec.rationale}</p>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderSummary = () => {
    const summary = result?.summary;

    return (
      <div className="patient__summary">
        <div className="patient__stat-cards">
          <div className="patient__stat-card">
            <span className="patient__stat-label">Patient</span>
            <span className="patient__stat-value">{summary?.patient_name ?? result?.patient_id}</span>
          </div>
          <div className="patient__stat-card">
            <span className="patient__stat-label">Active Conditions</span>
            <span className="patient__stat-value">{summary?.active_conditions_count ?? "—"}</span>
          </div>
          <div className="patient__stat-card">
            <span className="patient__stat-label">Current Medications</span>
            <span className="patient__stat-value">{summary?.current_medications_count ?? "—"}</span>
          </div>
          <div className="patient__stat-card">
            <span className="patient__stat-label">Specialty</span>
            <span className="patient__stat-value">
              {specialtyOptions.find((s) => s.value === specialty)?.label ?? "Auto-detect"}
            </span>
          </div>
        </div>

        {summary?.narrative_summary ? (
          <p className="patient__narrative">{summary.narrative_summary}</p>
        ) : (
          <p className="patient__narrative patient__narrative--muted">
            No narrative summary provided by the analysis.
          </p>
        )}

        <div className="patient__chips">
          {summary?.key_conditions?.map((condition) => (
            <span key={condition} className="patient__chip">
              {condition}
            </span>
          ))}
          {summary?.key_medications?.map((med) => (
            <span key={med} className="patient__chip patient__chip--muted">
              {med}
            </span>
          ))}
        </div>
      </div>
    );
  };

  const renderMetadata = () => {
    if (!result) return null;

    const duration =
      result.analysis_duration_seconds ?? result.analysis_metadata?.analysis_duration_seconds;
    const analyzedAt = result.analysis_timestamp ?? result.last_analyzed_at;

    return (
      <div className="patient__meta-grid">
        <div className="patient__meta-item">
          <span className="patient__meta-label">Status</span>
          <span className="patient__meta-value">{result.status ?? "Completed"}</span>
        </div>
        <div className="patient__meta-item">
          <span className="patient__meta-label">Analyzed At</span>
          <span className="patient__meta-value">{analyzedAt ?? "Not available"}</span>
        </div>
        <div className="patient__meta-item">
          <span className="patient__meta-label">Duration</span>
          <span className="patient__meta-value">
            {typeof duration === "number" ? `${duration.toFixed(2)}s` : "Not provided"}
          </span>
        </div>
        {result.notify_sent !== undefined && (
          <div className="patient__meta-item">
            <span className="patient__meta-label">Notifications</span>
            <span className="patient__meta-value">
              {result.notify_sent ? "Sent" : "Not sent"}
            </span>
          </div>
        )}
      </div>
    );
  };

  const renderReasoning = () => {
    if (!includeReasoning) {
      return null;
    }

    if (!result?.reasoning) {
      return <div className="patient__state patient__state--muted">No reasoning provided.</div>;
    }

    const reasoning = Array.isArray(result.reasoning)
      ? result.reasoning.join("\n")
      : result.reasoning;

    return <pre className="patient__reasoning">{reasoning}</pre>;
  };

  return (
    <section className="page patient">
      <div className="patient__header">
        <div>
          <h1>Patient Analysis</h1>
          <p className="patient__description">
            Mirror the Streamlit experience with actionable clinical insights and risk views.
          </p>
        </div>
      </div>

      <form className="patient__form" onSubmit={handleAnalyze}>
        <div className="patient__row">
          <label className="patient__field">
            <span>Patient ID</span>
            <input
              type="text"
              placeholder="patient-12345"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
            />
          </label>
          <label className="patient__field">
            <span>Specialty</span>
            <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
              {specialtyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="patient__row patient__row--options">
          <label className="patient__checkbox">
            <input
              type="checkbox"
              checked={includeRecommendations}
              onChange={(e) => setIncludeRecommendations(e.target.checked)}
            />
            Include Recommendations
          </label>
          <label className="patient__checkbox">
            <input
              type="checkbox"
              checked={includeReasoning}
              onChange={(e) => setIncludeReasoning(e.target.checked)}
            />
            Include Reasoning
          </label>
        </div>

        <div className="patient__actions">
          <button className="patient__button" type="submit" disabled={loading}>
            {loading ? "Analyzing…" : "Analyze Patient"}
          </button>
        </div>
      </form>

      {error && <div className="patient__state patient__state--error">{error}</div>}
      {loading && !error && <div className="patient__state">Analyzing patient…</div>}

      {result && !error && !loading && (
        <div className="patient__results">
          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Summary</h2>
              <p>Key patient facts and the model's narrative overview.</p>
            </div>
            {renderSummary()}
          </div>

          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Alerts</h2>
              <p>Clinical alerts returned by the analysis engine.</p>
            </div>
            {renderAlerts()}
          </div>

          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Risk Assessment</h2>
              <p>Relative risk scores for the patient's current presentation.</p>
            </div>
            {renderRiskScores()}
          </div>

          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Medication Review</h2>
              <p>Medication counts, potential issues, and current therapies.</p>
            </div>
            {renderMedicationReview()}
          </div>

          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Recommendations</h2>
              <p>Clinical recommendations and rationales.</p>
            </div>
            {renderRecommendations()}
          </div>

          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Reasoning</h2>
              <p>Chain-of-thought or supporting rationale when available.</p>
            </div>
            {renderReasoning()}
          </div>

          <div className="patient__section">
            <div className="patient__section-header">
              <h2>Analysis Metadata</h2>
              <p>Timing and delivery details for this run.</p>
            </div>
            {renderMetadata()}
          </div>
        </div>
      )}
    </section>
  );
};

export default PatientPage;

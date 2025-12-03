import { useMemo, useState, type FormEvent } from "react";
import { queryMedical } from "../api";
import type { QueryResult } from "../api/types";
import "./Interactions.css";

const QueryPage = () => {
  const [patientId, setPatientId] = useState("");
  const [question, setQuestion] = useState("");
  const [includeReasoning, setIncludeReasoning] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setShowReasoning(false);

    try {
      const response = await queryMedical(question, {
        patientId: patientId.trim() || undefined,
        includeReasoning,
      });
      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit query.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const confidenceDisplay = useMemo(() => {
    if (result?.confidence == null) return "Not available";
    const value = result.confidence;
    if (value <= 1) {
      return `${Math.round(value * 100)}%`;
    }
    return value.toFixed(2);
  }, [result]);

  const renderReasoning = () => {
    if (!result?.reasoning) return null;
    const reasoning = Array.isArray(result.reasoning)
      ? result.reasoning
      : [result.reasoning];

    return (
      <div className="interactions__section">
        <div className="interactions__section-header">
          <h3>Reasoning</h3>
          <button
            className="interactions__toggle"
            type="button"
            onClick={() => setShowReasoning((prev) => !prev)}
            aria-expanded={showReasoning}
          >
            {showReasoning ? "Hide" : "Show"}
          </button>
        </div>
        {showReasoning && (
          <ul className="interactions__list">
            {reasoning.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ul>
        )}
      </div>
    );
  };

  const renderSources = () => {
    if (!result?.sources) return null;
    if (Array.isArray(result.sources)) {
      return (
        <ul className="interactions__list">
          {result.sources.map((source, index) => (
            <li key={index}>{String(source)}</li>
          ))}
        </ul>
      );
    }

    if (typeof result.sources === "object") {
      return (
        <pre className="interactions__code-block">{JSON.stringify(result.sources, null, 2)}</pre>
      );
    }

    return <p className="interactions__muted">{String(result.sources)}</p>;
  };

  return (
    <section className="page interactions">
      <div className="interactions__header">
        <div>
          <h1>Clinical Query</h1>
          <p className="interactions__description">
            Ask a question about a patient and optionally include reasoning in the response.
          </p>
        </div>
      </div>

      <form className="interactions__form" onSubmit={handleSubmit}>
        <label className="interactions__field">
          <span>Patient ID (optional)</span>
          <input
            type="text"
            value={patientId}
            onChange={(event) => setPatientId(event.target.value)}
            placeholder="Enter a FHIR patient ID"
          />
        </label>

        <label className="interactions__field">
          <span>Question</span>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What follow-up is recommended for this patient?"
            rows={5}
            required
          />
        </label>

        <label className="interactions__checkbox">
          <input
            type="checkbox"
            checked={includeReasoning}
            onChange={(event) => setIncludeReasoning(event.target.checked)}
          />
          <span>Include reasoning</span>
        </label>

        <button className="interactions__submit" type="submit" disabled={loading}>
          {loading ? "Submitting…" : "Submit query"}
        </button>
      </form>

      {error && <div className="interactions__alert interactions__alert--error">{error}</div>}

      {result && (
        <div className="interactions__card" aria-live="polite">
          <div className="interactions__section">
            <h3>Answer</h3>
            <p>{result.answer ?? "No answer returned."}</p>
          </div>

          {renderReasoning()}

          <div className="interactions__section">
            <h3>Sources</h3>
            {renderSources() || <p className="interactions__muted">No sources provided.</p>}
          </div>

          <div className="interactions__meta">
            <div>
              <span className="interactions__label">Confidence</span>
              <strong>{confidenceDisplay}</strong>
            </div>
            <div>
              <span className="interactions__label">Status</span>
              <strong>{result.status}</strong>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default QueryPage;

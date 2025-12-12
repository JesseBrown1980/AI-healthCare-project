import { useState, type FormEvent } from "react";
import { submitFeedback } from "../api";
import "./Interactions.css";

const FeedbackPage = () => {
  const [queryId, setQueryId] = useState("");
  const [feedbackType, setFeedbackType] = useState("positive");
  const [correctedText, setCorrectedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!queryId.trim()) {
      setError("Query ID is required.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await submitFeedback(queryId.trim(), feedbackType, correctedText || undefined);
      setSuccess(response.message || "Feedback submitted successfully.");
      setQueryId("");
      setCorrectedText("");
      setFeedbackType("positive");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit feedback.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const showCorrectionField = feedbackType === "correction";

  return (
    <section className="page interactions">
      <div className="interactions__header">
        <div>
          <h1>Feedback</h1>
          <p className="interactions__description">
            Share feedback about a query result to help improve responses.
          </p>
        </div>
      </div>

      <form className="interactions__form" onSubmit={handleSubmit}>
        <label className="interactions__field">
          <span>Query ID</span>
          <input
            type="text"
            value={queryId}
            onChange={(event) => setQueryId(event.target.value)}
            placeholder="Enter the query ID"
            required
          />
        </label>

        <label className="interactions__field">
          <span>Feedback type</span>
          <select value={feedbackType} onChange={(event) => setFeedbackType(event.target.value)}>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="correction">Correction</option>
          </select>
        </label>

        {showCorrectionField && (
          <label className="interactions__field">
            <span>Corrected answer (optional)</span>
            <textarea
              value={correctedText}
              onChange={(event) => setCorrectedText(event.target.value)}
              placeholder="Provide a corrected answer if applicable"
              rows={4}
            />
          </label>
        )}

        <button className="interactions__submit" type="submit" disabled={loading}>
          {loading ? "Submitting…" : "Submit feedback"}
        </button>
      </form>

      {error && <div className="interactions__alert interactions__alert--error">{error}</div>}
      {success && <div className="interactions__alert interactions__alert--success">{success}</div>}
    </section>
  );
};

export default FeedbackPage;

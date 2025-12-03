import { useEffect, useMemo, useState, type FormEvent } from "react";
import { getAdaptersStatus, getHealthStatus } from "../api";
import type { AdaptersStatus, HealthStatus } from "../api/types";
import "./Interactions.css";

const SettingsPage = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [adaptersStatus, setAdaptersStatus] = useState<AdaptersStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState("light");
  const [detailLevel, setDetailLevel] = useState("standard");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      setError(null);
      try {
        const [health, adapters] = await Promise.all([getHealthStatus(), getAdaptersStatus()]);
        setHealthStatus(health);
        setAdaptersStatus(adapters);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load status.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void fetchStatus();
  }, []);

  const isHealthy = useMemo(() => {
    const status = healthStatus?.status?.toLowerCase();
    return status === "healthy" || status === "ok";
  }, [healthStatus]);

  const activeAdapters = adaptersStatus?.active_adapters ?? [];
  const availableAdapters = adaptersStatus?.available_adapters ?? [];

  const handleSave = (event: FormEvent) => {
    event.preventDefault();
    setSaveMessage("Settings saved");
  };

  return (
    <section className="page interactions">
      <div className="interactions__header">
        <div>
          <h1>Settings</h1>
          <p className="interactions__description">Manage application preferences and API connectivity.</p>
        </div>
      </div>

      {loading && <div className="interactions__state">Loading status…</div>}
      {error && <div className="interactions__alert interactions__alert--error">{error}</div>}

      {!loading && !error && (
        <div className="interactions__grid">
          <div className="interactions__card">
            <div className="interactions__section-header">
              <h3>API Connection</h3>
              <span className={`status-indicator ${isHealthy ? "status-indicator--ok" : "status-indicator--error"}`}>
                {isHealthy ? "Healthy" : "Unavailable"}
              </span>
            </div>
            <p className="interactions__muted">
              Service: {healthStatus?.service ?? "Unknown"} | Version: {healthStatus?.version ?? "N/A"}
            </p>
            {healthStatus?.vendor && <p className="interactions__muted">Vendor: {healthStatus.vendor}</p>}
          </div>

          <div className="interactions__card">
            <div className="interactions__section-header">
              <h3>Adapters</h3>
              <span className="interactions__badge">
                {activeAdapters.length} active / {availableAdapters.length || "N/A"} available
              </span>
            </div>
            <ul className="interactions__list">
              {activeAdapters.length ? (
                activeAdapters.map((adapter) => <li key={adapter}>{adapter}</li>)
              ) : (
                <li className="interactions__muted">No active adapters reported.</li>
              )}
            </ul>
          </div>
        </div>
      )}

      <form className="interactions__form interactions__card" onSubmit={handleSave}>
        <h3>Preferences</h3>
        <label className="interactions__field">
          <span>Theme</span>
          <select value={theme} onChange={(event) => setTheme(event.target.value)}>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>

        <label className="interactions__field">
          <span>Response detail level</span>
          <select value={detailLevel} onChange={(event) => setDetailLevel(event.target.value)}>
            <option value="brief">Brief</option>
            <option value="standard">Standard</option>
            <option value="detailed">Detailed</option>
          </select>
        </label>

        <button className="interactions__submit" type="submit">Save settings</button>
        {saveMessage && <div className="interactions__alert interactions__alert--success">{saveMessage}</div>}
      </form>
    </section>
  );
};

export default SettingsPage;

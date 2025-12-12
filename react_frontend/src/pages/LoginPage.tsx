import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./LoginPage.css";

type LocationState = { from?: { pathname?: string } } | null;

const LoginPage = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("changeme");
  const [patientId, setPatientId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fromState = (location.state as LocationState)?.from;
  const redirectPath = fromState?.pathname || "/dashboard";

  if (isAuthenticated && !isLoading) {
    return <Navigate to={redirectPath} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await login({ email, password, patient: patientId || undefined });
      navigate(redirectPath, { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="page">
      <div className="login-page">
        <div>
          <h1>Login</h1>
          <p className="login-page__intro">
            Use the demo credentials configured on the backend to obtain a short-lived JWT.
            Enable the <code>ENABLE_DEMO_LOGIN</code> flag on the API server before attempting to sign in.
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-form__field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="login-form__field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <div className="login-form__field">
            <label htmlFor="patient">Patient ID (optional)</label>
            <input
              id="patient"
              name="patient"
              type="text"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="demo-patient"
            />
          </div>

          {error ? <div className="login-form__error">{error}</div> : null}

          <div className="login-form__actions">
            <button className="login-form__button" type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
            <span>{redirectPath === "/login" ? "" : `You will return to ${redirectPath}`}</span>
          </div>

          <div className="login-form__hint">
            <strong>Tip:</strong> By default the demo API uses <code>demo@example.com</code> / <code>changeme</code>.
            Provide the patient ID configured in <code>DASHBOARD_PATIENT_IDS</code> to scope queries.
          </div>
        </form>
      </div>
    </section>
  );
};

export default LoginPage;

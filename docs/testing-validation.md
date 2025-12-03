# Testing, Validation, and Production Readiness

This guide summarizes the current test coverage, quick validation steps, and a short checklist to prepare the system for production demonstrations.

## What is Already Covered by Automated Tests
- **Dashboard response structure**: The dashboard endpoint test constructs sample patient analysis payloads and verifies the response includes expected metadata and alert summaries.
- **Alert severity ordering**: Helper logic returns a `critical` severity when any critical alert is present, ensuring the highest urgency bubbles to the top.
- **Risk score ranges**: Risk scoring functions produce normalized values between 0 and 1, with polypharmacy adding an incremental risk component.
- **Highest-risk derivation**: Aggregation routines choose the maximum available numeric risk score, matching clinician expectations for headline risk.

## Quick Manual Validation
Because the full stack depends on external services (FHIR data sources, LLM keys), a lightweight manual pass can still exercise end-to-end wiring once endpoints are aligned with the clients:
1. **Launch the FastAPI app locally** (or via Docker) and open Swagger UI at `/docs`.
2. **Authenticate or supply a token directly** if login is disabled. The demo login route can be enabled with `ENABLE_DEMO_LOGIN=true`.
3. **Call the dashboard and analyze endpoints** using Swagger, Postman, or the mobile client. Confirm HTTP 200 responses and that alerts, risk scores, and summaries appear for multiple sample patients.
4. **Trigger notification paths** by calling `/api/v1/analyze-patient` with `notify=true` to verify Slack/FCM hooks (if configured) are exercised without errors.

## Performance Notes
- The current stack does not connect to large FHIR datasets or heavyweight LLMs, so local runs should be responsive.
- External calls (LLM providers) and SHAP explanations will dominate latency; both are invoked asynchronously so concurrent requests can make progress during I/O waits.
- Uvicorn reload is disabled by default in production settings to avoid hot-reload overhead.

## Production-Readiness Checklist
- **Align API contracts with the frontend/mobile clients**: Add any missing routes or adjust client calls so that dashboards, login flows, and analysis requests share the same URL patterns.
- **Exercise critical flows with real inputs**: Once API alignment is complete, run dashboard and analyze requests from the mobile app (or Postman) to ensure end-to-end data retrieval, risk scoring, and alert surfaces all succeed.
- **Verify external credentials**: Populate `.env` with valid SMART-on-FHIR, LLM, and notification credentials and confirm requests complete without authentication errors.
- **Monitor resource hotspots**: Track latency for LLM and SHAP calls and cache stable outputs where possible to improve responsiveness.
- **Review alert/risk thresholds with clinicians**: Validate that severity ordering and polypharmacy penalties align with clinical safety expectations before broad demonstrations.

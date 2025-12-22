# 🏥 AI-Powered Healthcare Assistant with FHIR Integration

## Overview

An intelligent healthcare data bridge that connects Electronic Health Record (EHR) systems via FHIR (Fast Healthcare Interoperability Resources) standards with cutting-edge AI analytics. This application serves as middleware between healthcare data and actionable clinical insights, powered by advanced machine learning techniques.

### Key Capabilities

- **Patient Data Integration**: Seamlessly pull patient records (medications, labs, clinical notes) via FHIR APIs
- **Intelligent Summaries & Alerts**: Generate concise patient histories with red-flag alerts (abnormal labs, overdue screenings)
- **Clinical Decision Support**: AI-driven recommendations with citations to medical guidelines
- **Cross-App Communication**: Send insights and notifications to external applications and clinician interfaces
- **Continuous Learning**: Adapt to corrections and feedback to improve recommendations over time

---

## 🎯 Innovation Highlights

This project showcases state-of-the-art AI techniques applied to healthcare:

### 1. **Bi-Directional/Business-Integrated ML (BIML)**
A robust multi-layered data handling approach that manages complex healthcare datasets while integrating clinical business logic (privacy constraints, hospital-specific workflows) with ML outcomes. This ensures AI suggestions align with real-world clinical operations.

### 2. **Meta-Learning for Compositionality (MLC)**
The system continuously learns and adapts through:
- **Online Learning**: Incorporates user feedback and corrections in real-time
- **Compositional Reasoning**: Breaks down complex queries into modular learned components
- **Personalization**: Tailors responses to individual hospital protocols and user preferences

### 2.1 **Reinforcement Learning for Adaptive Recommendations**
- **Reward signals from feedback**: Clinician approvals, explicit positive/negative ratings, and corrected recommendations are converted into reward values that steer policy updates.
- **Adaptive performance**: The agent prioritizes actions that historically improved safety, guideline adherence, and workflow fit, leading to more context-aware recommendations over time.
- **Feedback-to-policy loop**: Rewards are aggregated with interaction metadata (specialty, acuity, contraindications) so the policy learns which actions perform best in comparable clinical scenarios.
- **Clinical caution**: Reinforcement learning outputs must be carefully validated and monitored in clinical settings to avoid unsafe or biased behavior; keep human oversight in the loop.

### 3. **Sparse LoRA (S-LoRA) Efficiency** ⭐
Our proprietary efficiency innovation optimizes fine-tuned models for healthcare:
- **Multi-Specialty Adapters**: Maintain separate LoRA modules for cardiology, oncology, etc., swappable without GPU bloat
- **Long-Sequence Optimization**: Efficiently handles multi-year patient histories that standard models struggle with
- **Memory-Efficient Fine-tuning**: Parameter-efficient adaptation without retraining large base models
- **Adaptive Composition**: Intelligently combines multiple specialty adapters for comprehensive patient analysis

### 4. **Algorithm of Thought (AoT)**
Enhanced reasoning through step-by-step processing:
- **Chain-of-Thought Prompting**: Internal iteration for complex medical reasoning
- **Transparent Logic**: Shows reasoning path before conclusions
- **Multi-Step Problem Solving**: Crucial for diagnostic queries and treatment recommendations

### 5. **Retrieval-Augmented Generation (RAG-Fusion)**
Live knowledge integration ensures cutting-edge medical information:
- **Medical Literature Integration**: Access to clinical guidelines and journal articles
- **Evidence-Based Recommendations**: Every suggestion grounded in current medical evidence
- **Source Citation**: Builds clinician trust through transparency

### 6. **Large Language Model Backbone**
- Flexible core supporting GPT-4, LLaMA-2, or other advanced LLMs
- Upgradeable architecture for future model improvements
- Natural language understanding optimized for medical terminology

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Dashboard | Chat Interface | Decision Support Views   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐ │
│  │ API Routes  │  │ Auth/Security│ │ Error Handling     │ │
│  └─────────────┘  └─────────────┘  └────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
          │            │            │
          ▼            ▼            ▼
┌──────────────────┐ ┌────────────────────┐ ┌──────────────┐
│  FHIR Connector  │ │  LLM + RAG Engine  │ │ S-LoRA Mgmt  │
│  (Healthcare)    │ │  (Reasoning)       │ │ (Efficiency) │
└──────────────────┘ └────────────────────┘ └──────────────┘
          │            │            │
    ┌─────▼─────┐ ┌───▼──────┐ ┌──▼────────┐
    │ EHR/FHIR  │ │ Medical  │ │ MLC Learn │
    │ Servers   │ │ KB Index │ │ Feedback  │
    └───────────┘ └──────────┘ └───────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10–3.12 (prebuilt wheels for all dependencies, including pandas)
- Node.js 16+ and npm (optional; required only for the React frontend)
- API keys for LLM service (OpenAI, Anthropic, or local LLaMA)
- FHIR-compliant healthcare data source (or test data)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JesseBrown1980/AI-healthCare-project.git
   cd AI-healthCare-project
   ```

2. **Set up backend environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
   > Tip: You can also install backend + test dependencies from the repo root with
   > `pip install -r requirements.txt`, which pulls in FastAPI, uvicorn, and the
   > supporting stack used by the backend APIs.

   **Default ports (and how to override them)**
   | Component | Default port | How to change |
   | --- | --- | --- |
   | Backend (FastAPI) | `8000` | Set `PORT` before starting `main.py` |
   | Streamlit UI (default frontend) | `3000` | Pass `--server.port` to `streamlit run` (the desktop wrapper points here by default; override it with `DESKTOP_APP_URL`) |
   | React dev server (optional) | `3000` | Configure your React dev server port or set `DESKTOP_APP_URL` when testing with the desktop shell |
   | FHIR test server (docker) | `8080` | Edit `docker-compose.yml` port mapping or `FHIR_SERVER_URL` |

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your FHIR server URL, API keys, etc.
   ```
   - **Epic USCDI sandbox**: Create a free developer account and register a SMART-on-FHIR app at the [Epic on FHIR](https://fhir.epic.com/Documentation?docId=sandbox) portal. Copy your `client_id`/`client_secret`, set `EPIC_FHIR_BASE_URL`/`EPIC_SMART_AUTH_URL`/`EPIC_SMART_TOKEN_URL` from the example defaults in `.env`, and use your app credentials for `SMART_CLIENT_ID`/`SMART_CLIENT_SECRET`.
   - **Cerner sandbox**: Sign up for an account in the [Oracle Health (Cerner) code console](https://code.cerner.com/developer/smart-on-fhir/). Register a SMART app, capture your `client_id`/`client_secret`, and replace `YOUR_TENANT_ID` in the Cerner `CERNER_SMART_*` URLs in `.env` with the tenant ID assigned to your sandbox project.
   - **General SMART overrides**: If your EHR provides a `.well-known/smart-configuration` endpoint, leave `SMART_AUTH_URL` and `SMART_TOKEN_URL` blank. The connector automatically discovers authorization/token URLs from `SMART_WELL_KNOWN` (or from `{FHIR_SERVER_URL}/.well-known/smart-configuration` and vendor presets) when explicit overrides are not provided.

4. **Start the backend server**
   ```bash
   python main.py
   # Server runs on http://localhost:8000
   ```

5. **Run the Streamlit UI (default frontend)**
   ```bash
   cd ../frontend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py --server.port 3000
   # UI available at http://localhost:3000
   ```
   The Streamlit experience is the default user interface. Use it if you want the quickest path to a working UI without Node.js.

6. **(Optional/in-progress) Run the React frontend**
   ```bash
   cd ../react_frontend
   npm install
   npm start
   # UI available at http://localhost:3000
   ```
   The React client is currently a skeleton: no API calls are wired up yet and several components/pages are stubs. Use it only if you plan to build out the React experience yourself. For demos, deployments, or user testing, the Streamlit UI remains the only fully working frontend today.

7. **Run the mobile app**
   ```bash
   cd ../mobile
   npm install
   npm start
   # Requires Node.js 16+; Metro server starts for the mobile client
   ```
   > Mobile testing requires demo login endpoints to be enabled on the backend.
   > Set `ENABLE_DEMO_LOGIN=true` (and optionally `DEMO_LOGIN_EMAIL`/`DEMO_LOGIN_PASSWORD`)
   > before launching the app; otherwise `/api/v1/auth/login` returns `404` when the
   > mobile client calls the demo login route. Demo JWTs are validated with the
   > `DEMO_JWT_SECRET`/`DEMO_JWT_ISSUER` values, so use the same settings for any
   > external client that needs to mint tokens locally.

### Testing, Validation, and Production Readiness

- See [`docs/testing-validation.md`](docs/testing-validation.md) for a summary of existing automated coverage, quick manual validation steps (including Swagger/Postman flows), and a short checklist to align APIs with the frontend/mobile clients before demos.

### Troubleshooting

- **401 Unauthorized on API requests**
  - Ensure requests include a bearer token: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/profile`.
  - If tokens come from the demo login, confirm the backend was started with valid `DEMO_JWT_SECRET`/`DEMO_JWT_ISSUER` values so signatures and issuers match.

- **`/api/v1/auth/login` returns 404 when testing the mobile demo**
  - The demo login route is disabled by default; enable it by exporting `ENABLE_DEMO_LOGIN=true` before starting the backend:
    ```bash
    ENABLE_DEMO_LOGIN=true uvicorn main:app --reload
    ```
  - If already running, check the current setting with `grep ENABLE_DEMO_LOGIN .env` or `echo "$ENABLE_DEMO_LOGIN"`.

- **Demo JWT validation fails because secrets/issuers don’t match**
  - Verify the backend environment matches the values used to mint demo tokens:
    ```bash
    grep -E "DEMO_JWT_SECRET|DEMO_JWT_ISSUER" .env
    ```
  - Regenerate tokens (or update the env vars) so both the mobile client and backend use the same `DEMO_JWT_SECRET` and `DEMO_JWT_ISSUER`.

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access at http://localhost:3000
```

---

## 🧠 Memory and cache management

- Use `ANALYSIS_HISTORY_LIMIT` to cap how many recent analyses are retained in memory (default: 200). Older entries are dropped automatically to keep memory bounded for long-running processes.
- Call `POST /api/v1/cache/clear` to flush both the in-memory analysis history and the patient dashboard summary cache. This is useful after load tests or when refreshing demo data without restarting the service.
- Set `ANALYSIS_CACHE_TTL_SECONDS` (default: 300) to reuse completed analyses for a short window and de-duplicate concurrent requests for the same patient/specialty combination. This reduces repeated FHIR/LLM calls during dashboard refreshes without introducing a full job queue.
- For horizontal scaling or Kubernetes deployments, move these caches to a shared store (database, Redis, etc.) so state is consistent across processes. The current single-process cache is intended for local and demo use.

---

## 📲 Mobile Notifications and Device Registration

- **Endpoint**: `POST /api/v1/register-device`
  - Registers a mobile device token for push notifications.
  - Request body (JSON):
    - `device_token` (string): FCM device token provided by the mobile client.
    - `platform` (string): Mobile platform identifier (e.g., `ios`, `android`).
  - Response: `{ "status": "registered", "device": { ... } }` when the device is tracked for notifications.
  - Requires authentication using the same token scheme as other protected API routes.
  - **Environment variables**:
    - `FCM_SERVER_KEY`: Server key from Firebase Cloud Messaging used to authorize push notification delivery.
    - `NOTIFICATION_URL`: Optional callback URL to receive notification payloads in parallel with FCM (left empty to disable).
    - `SLACK_WEBHOOK_URL`: Optional Slack incoming webhook to receive summaries of critical alerts.
    - `ENABLE_NOTIFICATIONS`: Set to `true` to enable outbound notifications. Requests must also specify `notify=true`.
    - Push notifications include a human-readable `title` and `body` (e.g., "Patient 1234: 2 alerts" / "Alerts: cardiovascular risk: 0.85"), which are required by FCM clients for display.

 Set `FCM_SERVER_KEY` in the backend environment to enable delivery to registered devices; without it, the service will skip FCM sends and log that no destination is configured. When `SLACK_WEBHOOK_URL` is provided, a critical-alert summary payload similar to the following will be sent:

```json
{
  "text": "*Critical alert for patient* `1234`\nAlerts detected: 1 critical / 2 total\n• Critical condition identified: MI (condition)\nTop risk: cardiovascular risk (0.85)"
}
```

To trigger notifications from the analysis API, ensure `ENABLE_NOTIFICATIONS=true` and call `/api/v1/analyze-patient` with `notify=true` in the query or payload.

---

## 📚 Module Guide

## 🔍 SHAP Explainability

SHAP (SHapley Additive exPlanations) assigns each feature a contribution score for a specific prediction, helping you see how data points push a model’s output higher or lower. Explainability is critical in healthcare because clinicians need to verify that model-driven insights align with clinical reasoning, detect potential bias, and build trust before acting on recommendations.

### How to read the SHAP plots
- **Summary plots**: Each dot represents a patient example; color shows feature value (e.g., high vs. low lab results), and position on the x-axis shows whether the feature increased or decreased risk. Dense clusters highlight features that consistently matter.
- **Force plots / decision plots**: Arrows pointing right increase the predicted risk or score; arrows pointing left decrease it. The baseline starts at the model’s expected value, and contributions accumulate to the final prediction.
- **Dependence plots**: Show how a single feature’s value affects SHAP contribution, often colored by an interacting feature to reveal nonlinear effects.

### Modeling notes
- The current workflow uses a surrogate model for SHAP analysis to provide fast, stable explanations while the production model handles core predictions.
- You can swap in more sophisticated models (e.g., gradient boosting, transformers, or calibrated classifiers) for either the primary predictor or the surrogate explainer as long as they expose the needed prediction interface for SHAP.

## Backend Components
- The `FHIRConnector` validates incoming FHIR Patient resources using `fhir.resources` when available; if the optional dependency isn't installed, it transparently falls back to a no-op validator.
- Configure the connector's `use_proxies` parameter to `False` in environments without SOCKS proxy support to avoid initialization warnings.
- The connector streams through paginated FHIR bundles by following `link["next"]` URLs until exhaustion, preserving the initial query parameters for the first page and then reusing the server-provided continuation links for subsequent requests. Use the cache time-to-live (TTL) setting in your environment configuration to control how long fetched bundle pages are retained before refresh.

### Backend Modules

#### `/backend/fhir_connector.py`
- Connects to FHIR-compliant EHR systems
- Authenticates with OAuth2/API keys
- Parses FHIR resource types (Patient, Medication, Observation, Condition)
- Normalizes data into internal representations

#### `/backend/llm_engine.py`
- LLM core interfacing with external APIs or local models
- Prompt engineering for medical contexts
- Response generation with medical terminology handling
- Model switching and upgrade compatibility

#### `/backend/rag_fusion.py`
- Retrieval-Augmented Generation component
- Queries medical literature databases
- Integrates clinical guidelines
- Citation management and evidence tracking

#### `/backend/s_lora_manager.py`
- Sparse LoRA adapter management system
- Handles multiple specialty-specific adapters
- Intelligent adapter composition and switching
- Memory optimization for GPU/CPU usage

#### `/backend/mlc_learning.py`
- Meta-Learning for Compositionality implementation
- Online learning from user feedback
- Model adaptation and personalization
- Compositional task decomposition

#### `/backend/aot_reasoner.py`
- Algorithm of Thought reasoning engine
- Chain-of-thought prompting strategies
- Step-by-step reasoning transparency
- Multi-step problem solving for complex queries

#### `/backend/patient_analyzer.py`
- Core analysis engine combining all components
- Patient data interpretation
- Risk score calculation that weights age, high-risk conditions (e.g., hypertension, diabetes, smoking status), and medication burden—including polypharmacy thresholds that surface deprescribing opportunities
- Decision support generation

### Data Models (`/models/`)
- `FHIR_models.py`: Healthcare resource definitions
- `request_models.py`: API request/response schemas
- `alert_models.py`: Clinical alert definitions

### Frontend (`/frontend/`)
- **Current UI: Streamlit.** Entry point at [`frontend/app.py`](frontend/app.py) with dependencies in [`frontend/requirements.txt`](frontend/requirements.txt). Launch with `streamlit run app.py --server.port 3000` (see Quick Start step 5).
- Dashboard for patient data visualization
- Chat interface for querying the AI
- Decision support recommendations panel
- Alert notification system
- **Planned/optional React UI.** A React SPA is planned for teams that prefer that workflow; once available, use the optional React commands in the setup section (`npm install && npm start`) to run it.

---

## 🔌 API Endpoints

### Patient Analysis
```bash
POST /api/v1/analyze-patient
{
  "fhir_patient_id": "patient-123",
  "include_recommendations": true,
  "specialty": "cardiology"
}
→ Returns: { summary, alerts, risk_score, recommendations, reasoning }
```

### FHIR Data Fetch
```bash
GET /api/v1/patient/{patient_id}/fhir
→ Returns: Full FHIR patient bundle from connected EHR
```

### Feedback (for MLC learning)
```bash
POST /api/v1/feedback
{
  "query_id": "q-456",
  "feedback": "positive|negative|correction",
  "corrected_text": "optional corrected recommendation"
}
```

### Medical Query
```bash
POST /api/v1/query
{
  "question": "What are treatment options for this patient?",
  "patient_context": {...}
}
→ Returns: { answer, reasoning, sources, confidence }
```

### Adapter Management (S-LoRA)
```bash
GET /api/v1/adapters
→ Returns: { active_adapters, available_adapters, memory_usage }
```

---

## 🎓 How S-LoRA Solves Healthcare Challenges

### The Problem
Standard LLMs struggle with:
- Long patient histories (memory limits)
- Multiple medical specialties simultaneously
- Efficient domain adaptation
- Real-time model updates

### The S-LoRA Solution
1. **Specialty-Specific Adapters**: Instead of one large model, maintain lightweight LoRA adapters for each specialty
2. **Dynamic Composition**: Intelligently select/combine adapters based on patient presentation
3. **Memory Efficiency**: Multiple adapters consume far less GPU memory than full model copies
4. **Rapid Adaptation**: New specialties can be added via targeted fine-tuning

**Example Usage**:
```python
# For a cardiac patient with diabetes
s_lora_manager = SLoRAManager()
adapters = s_lora_manager.select_adapters(
    specialties=["cardiology", "endocrinology"],
    patient_data=patient_record
)
response = llm.generate(prompt, adapters=adapters)
```

---

## 🔒 Security & Compliance

- **HIPAA Ready**: Built with healthcare data privacy as default
- **OAuth2 Authentication**: Secure EHR system access
- **Data Encryption**: End-to-end encryption for sensitive patient data
- **Audit Logging**: Complete audit trail of all patient data access
- **Role-Based Access Control**: Clinician, admin, researcher roles

---

## 📊 Deployment Options

### Option 1: Standalone Desktop App
```bash
# Using PyInstaller
pip install pyinstaller
pyinstaller --onefile main.py --name "HealthCare-AI"

# Creates: dist/HealthCare-AI.exe (Windows) or .app (macOS)
# Double-click to launch with full UI
```

### Option 2: Docker Container (Hospital Server)
```bash
docker build -t healthcare-ai:latest .
docker run -p 8000:8000 -p 3000:3000 \
  -e FHIR_SERVER_URL=https://hospital-ehr.com/fhir \
  healthcare-ai:latest
```

### Option 3: Kubernetes Deployment
```bash
kubectl apply -f k8s/deployment.yaml
# Scalable, production-grade healthcare service
```

---

## 🔄 Real-Time Dashboard Updates

The dashboard now exposes two strategies for keeping patient cards fresh. **Polling is the default** to keep the implementation simple and firewall-friendly, while a WebSocket option is available for richer interactivity.

### Default: Polling
- **Endpoint**: `GET /api/v1/patients/dashboard`
- **Payload**: Each record includes `patient_id`, `name`, `latest_risk_score`, `highest_alert_severity`, and `last_analyzed_at`.
- **Frontend guidance**: Trigger a refresh every **15–30 seconds** (configurable per deployment) and display `last_analyzed_at` in the dashboard header or list items so clinicians know data freshness. A ready-made Streamlit page lives at `frontend/pages/2_Multi_Patient_Dashboard.py` and auto-refreshes with `st_autorefresh`.

### Advanced: WebSockets
- **Endpoint**: `ws://<backend-host>/ws/patient-updates`
- **Behavior**: The backend broadcasts a `{"event": "dashboard_update", "data": {...summary}}` message whenever a patient analysis finishes. Each message mirrors the summary shape used by the polling endpoint, including `last_updated` and risk metrics.
- **Client loop**: After connecting and authenticating at the network layer, listen for incoming JSON messages and merge them into the current dashboard state (fall back to polling if the socket drops).

Use polling by default, and enable the WebSocket channel where bidirectional connectivity is allowed and UI responsiveness is critical.

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests (requires FHIR test server)
pytest tests/integration/ -v

# Run with coverage
pytest --cov=backend tests/

# Validate notification flows
pytest tests/test_notifications.py -k analyze_patient_sends_notifications
pytest tests/test_notifications.py -k register_device_stores_tokens
```

---

## 📈 Performance Benchmarks

- **Patient Data Fetch**: <500ms (via FHIR API)
- **Initial Analysis**: <2 seconds (summary + alerts)
- **Decision Support Generation**: <5 seconds (with RAG)
- **LLM Response**: <10 seconds (with reasoning chain)
- **Memory Per Adapter**: ~100MB (S-LoRA vs. 1-2GB full model)

---

## 🤝 Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for guidelines.

---

## 📄 License

MIT License - See `LICENSE` file

---

## 🎯 Roadmap

- [ ] Integration with major EHR systems (Epic, Cerner)
- [ ] Mobile app (iOS/Android) for clinician alerts
- [ ] Advanced MLC with reinforcement learning
- [ ] Explainability dashboards with SHAP analysis
- [ ] Real-time multi-patient dashboard
- [ ] Regulatory approvals (FDA, CE marking)

---

## 👨‍💼 About

This project demonstrates cutting-edge AI applied to healthcare, combining:
- **Domain Expertise**: Healthcare standards (FHIR/HL7)
- **AI Innovation**: S-LoRA, MLC, RAG-Fusion, Algorithm of Thought
- **Product Excellence**: Polished UX, secure deployment, real-world integration

Designed to position senior AI/healthcare tech roles and showcase the ability to bridge research and production systems.

---

## 📞 Support

For questions or issues:
- GitHub Issues: [Issues](https://github.com/JesseBrown1980/AI-healthCare-project/issues)
- Email: jessebrown.soft1980@gmail.com
- Documentation: [Full Docs](./docs/)

---

**Built with ❤️ for healthcare innovation**

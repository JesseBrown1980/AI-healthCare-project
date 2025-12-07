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
- Python 3.9+
- Node.js 16+ (for frontend)
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

5. **Set up and run frontend**
   ```bash
   cd ../frontend
   npm install
   npm start
   # UI available at http://localhost:3000
   ```

6. **Run the mobile app**
   ```bash
   cd ../mobile
   npm install
   npm start
   # Requires Node.js 16+; Metro server starts for the mobile client
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access at http://localhost:3000
```

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

Set `FCM_SERVER_KEY` in the backend environment to enable delivery to registered devices; without it, the service will skip FCM sends and log that no destination is configured.

---

## 📚 Module Guide

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
- React-based SPA with Tailwind CSS
- Dashboard for patient data visualization
- Chat interface for querying the AI
- Decision support recommendations panel
- Alert notification system

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

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests (requires FHIR test server)
pytest tests/integration/ -v

# Run with coverage
pytest --cov=backend tests/
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

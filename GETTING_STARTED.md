# Getting Started: Healthcare AI Assistant

## What is This Project?

An intelligent AI-powered healthcare application that bridges electronic health record (EHR) systems with cutting-edge artificial intelligence. It provides:

- **FHIR Integration**: Seamlessly connects to hospital EHR systems
- **Clinical Intelligence**: AI-driven patient analysis and decision support
- **Advanced AI Techniques**: S-LoRA, Meta-Learning, RAG-Fusion, Algorithm of Thought
- **Evidence-Based**: Grounded in medical guidelines and current knowledge
- **Secure & Compliant**: HIPAA-ready architecture

---

## Quick Overview (5-Minute Read)

### The Problem It Solves

Healthcare providers struggle with:
1. **Information Overload**: Too much patient data to process manually
2. **Decision Support**: Need evidence-based recommendations
3. **Integration**: Multiple systems don't talk to each other
4. **Alert Fatigue**: Important signals lost in noise

### The Solution

This AI assistant acts as an intelligent middleware that:
1. **Pulls** patient data from any FHIR-compliant EHR
2. **Analyzes** using advanced AI (LLM + RAG + reasoning)
3. **Surfaces** actionable insights and alerts
4. **Supports** clinical decision-making with evidence

### Real-World Example

**Scenario**: A clinician wants a comprehensive analysis of a patient with multiple conditions

```
Input: Patient ID from EHR
↓
[AI System]
- Fetches all FHIR records (conditions, medications, labs)
- Selects best medical specialty adapters (S-LoRA)
- Identifies alerts and risks
- Retrieves relevant guidelines (RAG-Fusion)
- Generates step-by-step reasoning (Algorithm of Thought)
- Creates personalized recommendations
↓
Output: Comprehensive analysis with:
✓ Summary of patient status
✓ Critical alerts highlighted
✓ Risk scores calculated
✓ Treatment recommendations with evidence
✓ Transparent reasoning chain
```

---

## Installation (Choose Your Method)

### Fastest Way: Docker

If you have Docker installed:

```bash
# 1. Clone project
git clone https://github.com/JesseBrown1980/AI-healthCare-project.git
cd AI-healthCare-project

# 2. Copy and configure
cp .env.example .env
# Edit .env with your API keys and FHIR server URL
nano .env

# 3. Start everything
docker-compose up

# 4. Access
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# 1. Clone and navigate
git clone https://github.com/JesseBrown1980/AI-healthCare-project.git
cd AI-healthCare-project

# 2. Setup backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# 3. In another terminal, setup frontend
cd frontend
python -m venv venv_fe
source venv_fe/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

See `INSTALL.md` for detailed installation options.

---

## First Steps

### 1. Configure API Keys

The system needs access to an LLM. Choose your provider:

**Option A: OpenAI (GPT-4)**
```bash
# Get key from https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-..."
```

**Option B: Local LLaMA (No API key needed)**
```bash
# Install Ollama: https://ollama.ai
ollama pull llama2
# Set in .env: LLM_MODEL=llama2
```

### 2. Connect to FHIR Data Source

Configure your EHR connection in `.env` using SMART-on-FHIR credentials:

```env
FHIR_SERVER_URL=https://your-hospital-fhir.com/fhir
SMART_CLIENT_ID=your-smart-client-id
SMART_CLIENT_SECRET=super-secret
SMART_SCOPE="system/*.read patient/*.read user/*.read"
# Optional overrides if discovery is not available
# SMART_AUTH_URL=https://ehr-authorize.example.com
# SMART_TOKEN_URL=https://ehr-token.example.com
# SMART_WELL_KNOWN=https://your-hospital-fhir.com/fhir/.well-known/smart-configuration
# SMART_AUDIENCE=https://your-hospital-fhir.com/fhir
# SMART_REFRESH_TOKEN=provided-refresh-token
```

Or use test FHIR server (included with docker-compose):
```env
FHIR_SERVER_URL=http://localhost:8080/fhir
```

### 3. Try It Out!

#### Via Web Interface

1. Go to http://localhost:3000
2. Click "Patient Analysis"
3. Enter a patient ID (try `demo-patient-1` for test data)
4. Click "Analyze Patient"

#### Via API

```bash
curl -X POST http://localhost:8000/api/v1/analyze-patient \
  -H "Content-Type: application/json" \
  -d '{
    "fhir_patient_id": "patient-example-1",
    "include_recommendations": true,
    "specialty": "cardiology"
  }'
```

---

## Understanding the Components

### 🏥 FHIR Connector (`backend/fhir_connector.py`)
Handles healthcare data integration
- Fetches patient records from EHR systems
- Parses healthcare standards (FHIR resources)
- Normalizes diverse data formats

### 🧠 LLM Engine (`backend/llm_engine.py`)
The AI reasoning core
- Interfaces with language models (GPT-4, Claude, LLaMA)
- Handles medical prompt engineering
- Provides natural language understanding

### 💾 RAG-Fusion (`backend/rag_fusion.py`)
Knowledge retrieval system
- Searches medical guidelines and protocols
- Retrieves evidence from literature
- Provides citations and sources

### 🎯 S-LoRA Manager (`backend/s_lora_manager.py`)
Efficient model adaptation
- Manages specialty-specific adapters
- Optimizes for long patient histories
- Composes multiple adapters intelligently

### 🧭 Algorithm of Thought (`backend/aot_reasoner.py`)
Step-by-step reasoning
- Generates transparent reasoning chains
- Supports multi-step clinical decisions
- Shows "thinking" for explainability

### 🎓 MLC Learning (`backend/mlc_learning.py`)
Continuous improvement
- Learns from user feedback
- Adapts to preferences
- Improves over time

### 📊 Patient Analyzer (`backend/patient_analyzer.py`)
Central orchestrator
- Combines all components
- Performs comprehensive analysis
- Generates reports

---

## Working with Patients

### Analyzing a Single Patient

```python
# Via API
POST /api/v1/analyze-patient
{
  "fhir_patient_id": "patient-123",
  "include_recommendations": true,
  "specialty": "cardiology"
}

# Returns:
{
  "summary": {...},
  "alerts": [...],
  "risk_scores": {...},
  "recommendations": {...},
  "reasoning": "..."
}
```

### Querying Medical Knowledge

```python
POST /api/v1/query
{
  "question": "What are treatment options for hypertensive crisis?",
  "patient_id": "patient-123",
  "include_reasoning": true
}

# Returns evidence-based answer with:
- Answer
- Reasoning chain
- Sources/citations
- Confidence score
```

### Providing Feedback (for learning)

```python
POST /api/v1/feedback
{
  "query_id": "q-456",
  "feedback_type": "correction",
  "corrected_text": "The correct answer should be..."
}
```

---

## Running Tests Locally

The project includes a comprehensive test suite to validate functionality without needing external services.

### Run All Tests

```bash
# From project root
pytest -q

# Example output:
# 7 passed in 0.19s
```

### Run Specific Test Categories

```bash
# FHIR connector tests
pytest tests/test_fhir_connector.py -v

# S-LoRA adapter tests
pytest tests/test_s_lora.py -v

# Meta-Learning tests
pytest tests/test_mlc_learning.py -v

# End-to-end pipeline tests
pytest tests/test_patient_analyzer_e2e.py -v
```

### What Tests Validate

| Test | Purpose |
|------|---------|
| `test_fhir_connector.py` | FHIR data fetching and normalization |
| `test_s_lora.py` | Adapter selection and activation |
| `test_mlc_learning.py` | Feedback processing and composition |
| `test_patient_analyzer_e2e.py` | Full pipeline with mocked components |

### Test Results Explained

✅ **7 passed** = All components working correctly
- FHIR connector can parse patient data
- S-LoRA can select and activate adapters
- MLC Learning can process feedback
- Full analysis pipeline works end-to-end

---

## Wiring LLM Providers

The system supports multiple LLM backends. Configure your preferred provider:

### Option 1: OpenAI (Recommended for getting started)

1. **Get API Key**:
   - Visit https://platform.openai.com/api-keys
   - Create new secret key
   - Copy the key (starts with `sk-`)

2. **Configure in `.env`**:
   ```bash
   LLM_MODEL=gpt-4
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. **Install OpenAI client** (included in requirements.txt):
   ```bash
   pip install openai
   ```

4. **Test connection**:
   ```bash
   # Via Python
   python -c "from openai import OpenAI; client = OpenAI(api_key='your-key'); print('✅ Connected')"
   ```

### Option 2: Anthropic Claude

1. **Get API Key**:
   - Visit https://console.anthropic.com
   - Create new API key

2. **Configure in `.env`**:
   ```bash
   LLM_MODEL=claude-3-opus
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

3. **Install Anthropic client**:
   ```bash
   pip install anthropic
   ```

### Option 3: Local LLaMA (Free, No API Key Needed)

**Best for**: Privacy-focused deployments, no API costs

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl https://ollama.ai/install.sh | sh
   
   # Windows: Download from https://ollama.ai
   ```

2. **Download Model**:
   ```bash
   ollama pull llama2
   # Or for better quality:
   ollama pull mistral
   ```

3. **Configure in `.env`**:
   ```bash
   LLM_MODEL=llama2
   # No API key needed
   ```

4. **Start Ollama** (in background):
   ```bash
   ollama serve
   ```

5. **Test in another terminal**:
   ```bash
   curl http://localhost:11434/api/generate -X POST \
     -d '{"model":"llama2","prompt":"Hello"}'
   ```

---

## Key Features Explained

### S-LoRA (Why It Matters)

**The Problem**: 
- Full LLM copies are huge (2-13GB)
- Managing multiple specialties is memory-intensive
- Long patient histories cause token limits

**Our Solution (S-LoRA)**:
- Multiple lightweight adapters (~100MB each)
- One for cardiology, one for oncology, etc.
- Compose them together dynamically
- Handle multi-year patient records efficiently

**Result**: 
```
Traditional: One 13GB model = limited flexibility
Our System: 10 × 100MB adapters + smart composition = powerful & efficient
```

### RAG-Fusion (Always Up-to-Date)

Instead of relying on static training data, RAG-Fusion:
1. Takes your question
2. Retrieves latest medical guidelines/research
3. Grounds answer in current evidence
4. Cites sources for verification

**Example**:
```
Q: "Latest recommendation for type 2 diabetes?"
↓ RAG-Fusion fetches ADA 2024 guidelines
A: "Current recommendation is GLP-1 RA as second line..."
   Sources: ADA Clinical Guidelines 2024
```

### Algorithm of Thought (Transparent Reasoning)

Instead of just giving an answer, the AI shows its work:

```
Clinical Question: Patient with chest pain?

Step 1: Identify presenting symptoms
  → Chest pain, shortness of breath, diaphoresis

Step 2: Review patient history
  → Age 65, hypertension, diabetes, smoking history

Step 3: Consider differential diagnoses
  → Acute MI (most likely)
  → Stable angina
  → Pulmonary embolism
  → GERD

Step 4: Evaluate diagnostic tests
  → Troponin elevated: 0.5 ng/ml (abnormal)
  → EKG shows ST elevation in II, III

Step 5: Assessment
  → Acute STEMI, recommend urgent catheterization
```

This transparency builds clinician trust and allows verification.

---

## Common Tasks

### Task 1: Analyze New Patient

```bash
# 1. Via web UI
Go to http://localhost:3000 → Patient Analysis → Enter ID → Click Analyze

# 2. Via API
curl -X POST http://localhost:8000/api/v1/analyze-patient \
  -H "Content-Type: application/json" \
  -d '{"fhir_patient_id":"new-patient-id"}'
```

### Task 2: Get Medical Recommendation

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/query \
  -d '{
    "question":"Best treatment for atrial fibrillation?",
    "patient_id":"patient-456"
  }'

# Or via web UI → Medical Query tab
```

### Task 3: Improve System (Provide Feedback)

```bash
# After getting a response you want to correct:
curl -X POST http://localhost:8000/api/v1/feedback \
  -d '{
    "query_id":"q-789",
    "feedback_type":"correction",
    "corrected_text":"The correct answer is..."
  }'
```

---

## Deployment Options

### Development (Your Computer)
```bash
# Single command
docker-compose up
```

### Hospital Server (Scaling)
```bash
# Deploy with Docker
docker build -t healthcare-ai .
docker run -e FHIR_SERVER_URL=... healthcare-ai
```

### Enterprise (Kubernetes)
```bash
# Production-grade deployment
helm install healthcare-ai ./k8s
```

See `INSTALL.md` for detailed deployment guides.

---

## Troubleshooting

### "Connection refused" Error
```bash
# Check if services are running
docker-compose ps

# View logs
docker-compose logs backend
```

### API Key Issues
```bash
# Verify key is set
echo $OPENAI_API_KEY

# Update in .env and restart
docker-compose restart backend
```

### FHIR Connection Failed
```bash
# Test FHIR server directly
curl https://your-fhir-server/fhir/Patient/test

# Check credentials in .env
# Verify API key has Patient read permission
```

See `INSTALL.md` for more troubleshooting.

---

## Next Steps

1. ✅ **Install**: Follow installation guide
2. ✅ **Configure**: Set up API keys and FHIR server
3. ✅ **Test**: Try with sample patient data
4. ✅ **Customize**: Modify frontend for your needs
5. ✅ **Deploy**: Choose production deployment method
6. ✅ **Integrate**: Connect with your hospital systems

---

## Learning Resources

- 📖 **Full Documentation**: See `./docs/` directory
- 🎓 **API Docs**: http://localhost:8000/docs
- 🔬 **Research Papers**: Links in README
- 💬 **Community**: https://github.com/JesseBrown1980/AI-healthCare-project/discussions

---

## Support

- **Questions**: Open GitHub discussion
- **Bugs**: Report with reproducible example
- **Features**: Submit as GitHub issue
- **Contact**: hello@jessebrown.dev

---

## Important Disclaimers

⚠️ **This is a research/educational project**
- NOT approved for clinical use
- Should not make final clinical decisions
- Always consult qualified healthcare providers
- Requires proper regulatory approval for deployment

✅ **Best used as**:
- Decision support assistant
- Learning tool for healthcare IT
- Research platform
- Integration showcase

---

**Ready to get started?** 
→ Go to `INSTALL.md` for installation steps
→ Try the web interface at http://localhost:3000

---

Questions? Open an issue or contact: hello@jessebrown.dev

# AI-Powered Healthcare Assistant - Installation & Setup Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM**: Minimum 8GB (16GB+ recommended for LLM features)
- **Storage**: 5GB free space minimum
- **GPU**: Optional but recommended for LLM features (NVIDIA CUDA 11.8+)

### Software Requirements
- **Python**: 3.9 or higher
- **Node.js**: 16.0 or higher (for frontend)
- **Docker**: 20.10+ (optional, for containerized deployment)
- **Git**: For version control

---

## Quick Start (5 minutes)

### Option 1: Docker (Recommended for first-time users)

```bash
# Clone repository
git clone https://github.com/JesseBrown1980/AI-healthCare-project.git
cd AI-healthCare-project

# Copy environment file
cp .env.example .env

# Edit .env with your settings (API keys, FHIR server URL, etc.)
nano .env

# Start with Docker Compose
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Option 2: Local Development

```bash
# Clone repository
git clone https://github.com/JesseBrown1980/AI-healthCare-project.git
cd AI-healthCare-project

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
python -m venv venv_frontend
source venv_frontend/bin/activate  # On Windows: venv_frontend\Scripts\activate
pip install -r requirements.txt

# Run backend
cd ../backend
python main.py

# In another terminal, run frontend
cd frontend
streamlit run app.py
```

---

## Installation Methods

### Method 1: Standalone Executable (Windows/Mac)

```bash
# Install PyInstaller
pip install pyinstaller

# Build standalone executable
cd backend
pyinstaller --onefile \
  --add-data "requirements.txt:." \
  --hidden-import=pydantic \
  --hidden-import=fastapi \
  --hidden-import=uvicorn \
  main.py

# Executable created in: dist/main.exe (Windows) or dist/main (macOS)
```

### Method 2: Docker Container

```bash
# Build image
docker build -t healthcare-ai:latest .

# Run container
docker run -p 8000:8000 -p 3000:3000 \
  -e FHIR_SERVER_URL=https://your-ehr.com/fhir \
  -e OPENAI_API_KEY=your-key \
  healthcare-ai:latest
```

### Method 3: Kubernetes (Production)

```bash
# Create namespace
kubectl create namespace healthcare

# Deploy with Helm
helm install healthcare-ai ./k8s/healthcare-ai-chart \
  --namespace healthcare \
  --values ./k8s/values.yaml
```

---

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit `.env` with Your Settings

```env
# FHIR Server Configuration
FHIR_SERVER_URL=https://fhir.example.com/fhir
SMART_CLIENT_ID=your-smart-client-id
SMART_CLIENT_SECRET=your-smart-client-secret
SMART_SCOPE="system/*.read patient/*.read user/*.read"
# Optional SMART overrides
# SMART_AUTH_URL=https://ehr-authorize.example.com
# SMART_TOKEN_URL=https://ehr-token.example.com
# SMART_WELL_KNOWN=https://fhir.example.com/fhir/.well-known/smart-configuration
# SMART_AUDIENCE=https://fhir.example.com/fhir
# SMART_REFRESH_TOKEN=provided-refresh-token

# LLM Configuration
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Application Settings
HOST=0.0.0.0
PORT=8000
DEBUG=False
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./healthcare_ai.db

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### 3. API Key Setup

#### OpenAI (GPT-4)
1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Copy to `.env` as `OPENAI_API_KEY`

#### Anthropic (Claude)
1. Go to https://console.anthropic.com
2. Create new API key
3. Copy to `.env` as `ANTHROPIC_API_KEY`

#### FHIR Server
Contact your healthcare IT department for:
- FHIR server URL
- API credentials or OAuth2 configuration

---

## Running the Application

### Starting the Backend

```bash
cd backend
source venv/bin/activate

# Development mode (with auto-reload)
python main.py --reload

# Production mode
python main.py
```

Backend runs on: **http://localhost:8000**

API Documentation: **http://localhost:8000/docs**

### Starting the Frontend

```bash
cd frontend
source venv_frontend/bin/activate

# Run Streamlit app
streamlit run app.py
```

Frontend runs on: **http://localhost:3000**

### Using Docker Compose

```bash
# Start all services
docker-compose up

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down
```

---

## Testing

### Unit Tests

```bash
cd backend
pytest tests/ -v
```

### Integration Tests

```bash
# Requires running FHIR test server
pytest tests/integration/ -v
```

### API Testing with curl

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Analyze patient
curl -X POST http://localhost:8000/api/v1/analyze-patient \
  -H "Content-Type: application/json" \
  -d '{
    "fhir_patient_id": "patient-123",
    "include_recommendations": true,
    "specialty": "cardiology"
  }'

# Medical query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the treatment options?",
    "include_reasoning": true
  }'
```

---

## Troubleshooting

### Issue: "Connection refused" on localhost:8000

**Solution:**
```bash
# Check if backend is running
netstat -an | grep 8000

# Kill process on port 8000 (if needed)
lsof -ti:8000 | xargs kill -9

# Restart backend
python backend/main.py
```

### Issue: FHIR server connection error

**Solution:**
```bash
# Verify FHIR URL is correct
curl -I https://your-fhir-server/fhir

# Check API credentials
# Test with curl using provided credentials
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://your-fhir-server/fhir/Patient/123
```

### Issue: OpenAI API key error

**Solution:**
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Check account has credits
# Visit https://platform.openai.com/account/billing/overview

# Update .env with correct key
export OPENAI_API_KEY=sk-...
```

### Issue: Module import errors

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Should be 3.9+
```

### Issue: Streamlit port already in use

**Solution:**
```bash
# Run on different port
streamlit run frontend/app.py --server.port=3001

# Or kill existing process
lsof -ti:3000 | xargs kill -9
```

---

## Performance Optimization

### GPU Acceleration

If you have an NVIDIA GPU:

```bash
# Install CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU is available
python -c "import torch; print(torch.cuda.is_available())"
```

### Memory Optimization

In `.env`:
```env
# Reduce model size for limited RAM
LLM_MODEL=gpt-3.5-turbo  # Instead of gpt-4
BASE_MODEL=mistral-7b    # Instead of 13b/70b
```

### Database Setup (Optional)

For production deployment with database:

```bash
# Initialize PostgreSQL
sudo apt-get install postgresql

# Create database
createdb healthcare_ai

# Update .env
DATABASE_URL=postgresql://user:password@localhost/healthcare_ai

# Run migrations
alembic upgrade head
```

---

## Next Steps

1. **Configure FHIR Connection**: Set up connection to your healthcare system
2. **Add API Keys**: Configure LLM and services
3. **Load Medical Knowledge**: Import clinical guidelines and protocols
4. **Test with Sample Patient**: Use provided test data
5. **Customize UI**: Modify frontend/app.py for your needs
6. **Deploy**: Choose your deployment method

---

## Support & Documentation

- **Full Documentation**: See `./docs/` directory
- **API Documentation**: http://localhost:8000/docs
- **Issues**: https://github.com/JesseBrown1980/AI-healthCare-project/issues
- **Contributing**: See `CONTRIBUTING.md`

---

## License

MIT License - See `LICENSE` file

---

**Need help?** Please open an issue on GitHub or contact: hello@jessebrown.dev

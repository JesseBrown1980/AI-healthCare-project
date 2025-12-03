# Quick Reference Guide

## 🚀 Getting Started (< 5 minutes)

```bash
# Clone and setup
git clone https://github.com/JesseBrown1980/AI-healthCare-project.git
cd AI-healthCare-project

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
docker-compose up

# Access
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

---

## 📌 Key Commands

### Docker
```bash
docker-compose up              # Start all services
docker-compose down            # Stop services
docker-compose logs -f         # View logs
docker-compose ps              # Check status
```

### Backend
```bash
cd backend
python main.py                 # Run server
pytest tests/                  # Run tests
python -m pytest --cov         # Coverage report
```

### Frontend
```bash
cd frontend
streamlit run app.py           # Run dashboard
streamlit run app.py --logger.level=debug
```

---

## 🔌 API Quick Reference

### Patient Analysis
```bash
curl -X POST http://localhost:8000/api/v1/analyze-patient \
  -H "Content-Type: application/json" \
  -d '{
    "fhir_patient_id": "patient-123",
    "include_recommendations": true,
    "specialty": "cardiology"
  }'
```

### Medical Query
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -d '{
    "question": "What are treatment options?",
    "include_reasoning": true
  }'
```

### Provide Feedback
```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -d '{
    "query_id": "q-456",
    "feedback_type": "correction",
    "corrected_text": "The correct answer..."
  }'
```

### Check System Status
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/adapters
curl http://localhost:8000/api/v1/stats
```

---

## 📁 Project Structure

```
AI-healthCare-project/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── fhir_connector.py        # EHR integration
│   ├── llm_engine.py            # LLM interface
│   ├── rag_fusion.py            # Knowledge retrieval
│   ├── s_lora_manager.py        # LoRA adapters
│   ├── mlc_learning.py          # Learning system
│   ├── aot_reasoner.py          # Reasoning engine
│   ├── patient_analyzer.py      # Orchestration
│   └── requirements.txt         # Python deps
├── frontend/
│   ├── app.py                   # Streamlit UI
│   └── requirements.txt
├── models/
│   └── request_models.py        # Data models
├── tests/                       # Unit/integration tests
├── docs/                        # Documentation
├── docker-compose.yml           # Docker setup
├── Dockerfile                   # Backend container
├── Dockerfile.frontend          # Frontend container
├── README.md                    # Main documentation
├── GETTING_STARTED.md           # Quick start
├── INSTALL.md                   # Installation guide
├── CONTRIBUTING.md              # Contributing guide
├── LICENSE                      # MIT license
└── .env.example                 # Config template
```

---

## ⚙️ Configuration (.env)

### Essential
```env
FHIR_SERVER_URL=http://localhost:8080/fhir
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...
```

### Optional
```env
FHIR_API_KEY=your-key
ANTHROPIC_API_KEY=sk-ant-...
DEBUG=False
LOG_LEVEL=INFO
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | `lsof -ti:8000 \| xargs kill -9` |
| Module not found | `pip install -r requirements.txt` |
| FHIR connection error | Check FHIR_SERVER_URL in .env |
| API key error | Verify OPENAI_API_KEY is set |
| Docker won't start | `docker-compose down && docker-compose up` |

---

## 📊 Performance Tips

### For Limited Resources
```env
LLM_MODEL=gpt-3.5-turbo        # Faster, cheaper
BASE_MODEL=mistral-7b          # Smaller model
```

### For GPU Acceleration
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## 🎯 Common Use Cases

### Use Case 1: Analyze New Patient
1. Go to http://localhost:3000
2. Select "Patient Analysis"
3. Enter Patient ID
4. Click "Analyze Patient"

### Use Case 2: Ask Clinical Question
1. Go to "Medical Query"
2. Enter question
3. Optionally provide patient ID
4. Click "Query AI"

### Use Case 3: Improve System
1. Get response
2. Go to "Feedback"
3. Enter query ID
4. Select feedback type
5. Submit

---

## 🔗 Important Links

- **GitHub**: https://github.com/JesseBrown1980/AI-healthCare-project
- **API Docs**: http://localhost:8000/docs (when running)
- **OpenAI Keys**: https://platform.openai.com/api-keys
- **FHIR Standard**: https://www.hl7.org/fhir/
- **Streamlit Docs**: https://docs.streamlit.io

---

## 📖 Documentation

- `README.md` - Overview and architecture
- `GETTING_STARTED.md` - Feature explanations
- `INSTALL.md` - Installation details
- `CONTRIBUTING.md` - How to contribute
- `PROJECT_SUMMARY.md` - Complete project summary

---

## 🆘 Getting Help

- **Issues**: Create GitHub issue
- **Discussions**: GitHub discussions
- **Email**: hello@jessebrown.dev
- **Documentation**: Check docs/ folder

---

## ✅ Pre-Deployment Checklist

- [ ] Environment variables configured
- [ ] FHIR server connected
- [ ] API keys valid
- [ ] Docker installed (if using)
- [ ] Port 8000 & 3000 available
- [ ] Tests passing
- [ ] Documentation reviewed

---

## 🚀 Deployment Steps

```bash
# 1. Verify everything works
docker-compose up
# Test: http://localhost:3000

# 2. Build for production
docker build -t healthcare-ai:prod .

# 3. Push to registry
docker tag healthcare-ai:prod your-registry/healthcare-ai:prod
docker push your-registry/healthcare-ai:prod

# 4. Deploy to cloud
# Use cloud provider's deployment tools
# (AWS ECR, GCP Cloud Run, Azure Container Registry, etc.)
```

---

## 📱 Quick Links

- **Local Frontend**: http://localhost:3000
- **Local API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

---

## 🎓 Learning Path

1. **Start**: Read `GETTING_STARTED.md`
2. **Install**: Follow `INSTALL.md`
3. **Explore**: Try web UI features
4. **Code**: Review backend modules
5. **Contribute**: See `CONTRIBUTING.md`
6. **Deploy**: Choose deployment option

---

**Need help? Check the full documentation files or open a GitHub issue.**

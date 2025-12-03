
import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Mock heavy dependencies BEFORE importing main
# We need to list the modules that ServiceContainer imports
# backend.di.container imports:
# from backend.llm_engine import LLMEngine
# from backend.rag_fusion import RAGFusion
# from backend.s_lora_manager import SLoRAManager
# from backend.mlc_learning import MLCLearning
# from backend.aot_reasoner import AoTReasoner

@pytest.fixture
def mock_app():
    with patch("backend.di.container.LLMEngine"), \
         patch("backend.di.container.RAGFusion"), \
         patch("backend.di.container.SLoRAManager"), \
         patch("backend.di.container.MLCLearning"), \
         patch("backend.di.container.AoTReasoner"), \
         patch("backend.di.container.FhirHttpClient"), \
         patch("backend.di.container.FhirResourceService"):
         
        from backend.main import app
        yield app

def test_analyze_patient_route_exists(mock_app):
    with TestClient(mock_app) as client:
        # We don't care about the body validation failing (422) or auth (401)
        # We just want to ensure it is NOT 404
        response = client.post("/api/v1/analyze-patient", json={})
        print(f"Response status: {response.status_code}")
        assert response.status_code != 404, "Endpoint /api/v1/analyze-patient not found!"

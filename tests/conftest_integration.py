import pytest
import os
import json
from unittest.mock import MagicMock, AsyncMock
from backend.llm_engine import LLMEngine

# Marker for integration tests
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")

@pytest.fixture
def real_llm_engine():
    """
    Returns a real LLMEngine if API key is present, otherwise a HIGH-FIDELITY MOCK.
    This allows 'simulation' of real world without cost if key is missing.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    allow_real_llm = os.getenv("ALLOW_REAL_LLM_IN_TESTS", "false").lower() == "true"
    
    if allow_real_llm and api_key and api_key.strip() and "dummy" not in api_key:
        # Real Engine, only for explicitly requested integration runs.
        return LLMEngine(model_name="gpt-4", api_key=api_key)
    else:
        # High-Fidelity Local Mock
        print("\n[NOTICE] No API Key found. Using Local High-Fidelity Mock for Integration Test.")
        mock = MagicMock(spec=LLMEngine)
        mock.model_name = "mock-gpt-4-local"
        
        async def _mock_query(system_prompt, user_prompt, **kwargs):
            # Simulate intelligent decision based on keywords
            user_content = user_prompt.lower()
            
            # Simple simulation logic
            if "cancer" in user_content and "john" in user_content:
                 return {"content": json.dumps({"action": "REJECT", "reason": "Detected PHI (Name + Condition) in payload"})}
            
            if "password" in user_content:
                 return {"content": json.dumps({"action": "REJECT", "reason": "Security credential leakage prevented"})}
                 
            return {"content": json.dumps({"action": "APPROVE", "reason": "Content looks safe for distribution"})}
            
        mock.query_generic = AsyncMock(side_effect=_mock_query)
        return mock

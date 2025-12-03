import pytest
from unittest.mock import patch, MagicMock
from backend.llm_engine import LLMEngine

@pytest.fixture
def mock_compliance():
    with patch("backend.llm_engine.get_region", return_value="US"), \
         patch("backend.llm_engine.is_external_llm_allowed", return_value=True), \
         patch("backend.llm_engine.is_local_llm_required", return_value=False):
        yield

def test_initialization_openai_allowed(mock_compliance):
    # Should succeed with default settings (external allowed)
    engine = LLMEngine(model_name="gpt-4", api_key="sk-test")
    assert engine.provider == "openai"

def test_initialization_compliance_failure():
    # Force compliance failure
    with patch("backend.llm_engine.get_region", return_value="EU"), \
         patch("backend.llm_engine.is_external_llm_allowed", return_value=False), \
         patch("backend.llm_engine.is_local_llm_required", return_value=True):
        
        with pytest.raises(ValueError) as exc:
            LLMEngine(model_name="gpt-4")
        
        assert "not allowed" in str(exc.value) or "requires local LLM" in str(exc.value)

def test_detect_provider(mock_compliance):
    engine = LLMEngine(model_name="gpt-4")
    assert engine._detect_provider("gpt-4") == "openai"
    assert engine._detect_provider("claude-2") == "anthropic"
    assert engine._detect_provider("llama-2") == "local"

def test_build_system_prompt(mock_compliance):
    engine = LLMEngine(model_name="gpt-4")
    prompt = engine._build_system_prompt(language="en")
    assert "Assistant" in prompt or "assistant" in prompt
    assert "expert clinical decision support" in prompt

    # Test language injection
    prompt_es = engine._build_system_prompt(language="es")
    assert "Español" in prompt_es

def test_build_user_prompt_anonymization(mock_compliance):
    engine = LLMEngine(model_name="gpt-4", api_key="dummy")
    
    with patch("backend.llm_engine.is_anonymization_required", return_value=True), \
         patch("backend.llm_engine.prepare_data_for_external_service") as mock_anon:
        
        mock_anon.return_value = {"patient": {"name": "REDACTED"}}
        
        context = {"patient": {"name": "John Doe"}}
        engine._build_user_prompt("Query", patient_context=context)
        
        mock_anon.assert_called_once()

"""
Mock LLM Engine
Provides mock LLM responses for testing without calling real AI APIs.
"""

from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, AsyncMock
import random


# Pre-defined responses for different query types
MOCK_RESPONSES = {
    "patient_analysis": {
        "summary": "Based on the patient's clinical data, there are several areas of concern that warrant attention.",
        "risk_assessment": "The patient presents with moderate to high cardiovascular risk factors.",
        "recommendations": [
            "Consider cardiology consultation for comprehensive cardiovascular evaluation",
            "Review current medication regimen for potential optimizations",
            "Schedule follow-up in 2-4 weeks to reassess condition",
        ],
    },
    "medication_review": {
        "summary": "Medication review completed. No critical drug-drug interactions identified.",
        "findings": [
            "Current medication regimen appears appropriate for conditions",
            "Consider monitoring renal function given current medications",
        ],
        "recommendations": [
            "Continue current medications as prescribed",
            "Schedule routine lab work in 3 months",
        ],
    },
    "clinical_query": {
        "answer": "Based on current clinical guidelines and the patient's presentation, the recommended approach would be to...",
        "confidence": 0.85,
        "sources": [
            {"title": "Clinical Practice Guidelines 2024", "relevance": 0.92},
            {"title": "Evidence-Based Medicine Review", "relevance": 0.87},
        ],
    },
    "risk_prediction": {
        "cardiovascular_risk": 0.35,
        "readmission_risk": 0.22,
        "fall_risk": 0.15,
        "overall_risk_score": 0.28,
        "confidence": 0.88,
    },
}


class MockLLMEngine:
    """
    Mock LLM engine that returns pre-defined responses.
    
    Usage:
        llm = MockLLMEngine()
        response = await llm.generate("Analyze this patient...")
    """
    
    def __init__(
        self,
        default_response: Optional[str] = None,
        response_type: str = "clinical_query",
        latency_ms: int = 0,
    ):
        self.default_response = default_response
        self.response_type = response_type
        self.latency_ms = latency_ms
        self.call_history: List[Dict[str, Any]] = []
        self._custom_responses: Dict[str, Any] = {}
    
    def set_response(self, prompt_pattern: str, response: Any):
        """Set a custom response for prompts matching a pattern."""
        self._custom_responses[prompt_pattern] = response
        return self
    
    def set_response_type(self, response_type: str):
        """Set the type of mock response to return."""
        self.response_type = response_type
        return self
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate a mock response."""
        # Record the call
        self.call_history.append({
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        })
        
        # Check for custom responses
        for pattern, response in self._custom_responses.items():
            if pattern.lower() in prompt.lower():
                if callable(response):
                    return response(prompt)
                return str(response)
        
        # Return default response if set
        if self.default_response:
            return self.default_response
        
        # Return mock response based on type
        response_data = MOCK_RESPONSES.get(self.response_type, MOCK_RESPONSES["clinical_query"])
        
        if isinstance(response_data, dict):
            if "answer" in response_data:
                return response_data["answer"]
            elif "summary" in response_data:
                return response_data["summary"]
            else:
                import json
                return json.dumps(response_data)
        
        return str(response_data)
    
    async def analyze_patient(
        self,
        patient_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Mock patient analysis."""
        self.call_history.append({
            "method": "analyze_patient",
            "patient_data": patient_data,
            **kwargs
        })
        
        base_response = MOCK_RESPONSES["patient_analysis"].copy()
        
        # Add some dynamic elements based on patient data
        risk_score = patient_data.get("risk_score", random.uniform(0.2, 0.8))
        base_response["risk_score"] = risk_score
        base_response["patient_id"] = patient_data.get("patient_id", "unknown")
        
        if risk_score > 0.7:
            base_response["alert_severity"] = "high"
        elif risk_score > 0.4:
            base_response["alert_severity"] = "medium"
        else:
            base_response["alert_severity"] = "low"
        
        return base_response
    
    async def predict_risk(
        self,
        patient_data: Dict[str, Any],
        risk_type: str = "overall",
        **kwargs
    ) -> Dict[str, Any]:
        """Mock risk prediction."""
        self.call_history.append({
            "method": "predict_risk",
            "patient_data": patient_data,
            "risk_type": risk_type,
            **kwargs
        })
        
        return MOCK_RESPONSES["risk_prediction"].copy()
    
    def get_call_count(self) -> int:
        """Get number of calls made to this mock."""
        return len(self.call_history)
    
    def reset(self):
        """Reset call history."""
        self.call_history = []
        self._custom_responses = {}


def mock_llm_response(response: Union[str, Dict[str, Any], callable]):
    """
    Decorator/context manager to mock LLM responses.
    
    Usage:
        @mock_llm_response("Fixed response text")
        async def test_something():
            ...
        
        # Or as context manager:
        with mock_llm_response({"answer": "test"}):
            ...
    """
    mock_engine = MockLLMEngine()
    
    if isinstance(response, str):
        mock_engine.default_response = response
    elif isinstance(response, dict):
        import json
        mock_engine.default_response = json.dumps(response)
    elif callable(response):
        mock_engine.set_response("", response)
    
    @contextmanager
    def _mock_context():
        with patch("backend.llm_engine.LLMEngine", return_value=mock_engine):
            with patch("backend.llm_engine.LLMEngine.generate", new=mock_engine.generate):
                yield mock_engine
    
    return _mock_context()

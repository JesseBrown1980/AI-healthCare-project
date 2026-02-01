
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_version_endpoint_compliance():
    """
    REQ-00-VERSION: Verify /version endpoint returns build_id and compliant structure.
    """
    with TestClient(app) as client:
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required regulatory fields
        assert "version" in data
        assert "build_id" in data
        assert "environment" in data
        assert "timestamp" in data
        
        # Verify version format (semantic versioning check could go here)
        assert data["version"] == "1.0.0"

@pytest.mark.asyncio
async def test_regulatory_disclaimer_injection():
    """
    REQ-09: Verify regulatory disclaimer is injected into patient analysis.
    """
    # Mock dependencies to isolate the analyzer logic
    from backend.patient_analyzer import PatientAnalyzer
    
    mock_fhir = MagicMock()
    # Ensure fetch_patient_data is an AsyncMock that returns valid structure
    mock_fhir.fetch_patient_data = AsyncMock(return_value={"id": "test-pat", "resourceType": "Patient"})
    
    mock_s_lora = MagicMock()
    mock_s_lora.select_adapters = AsyncMock(return_value=[])
    mock_s_lora.activate_adapter = AsyncMock()
    mock_s_lora.adapters = {}
    
    # Instantiate analyzer with mocks
    analyzer = PatientAnalyzer(
        fhir_connector=mock_fhir,
        llm_engine=MagicMock(),
        rag_fusion=MagicMock(),
        s_lora_manager=mock_s_lora,
        aot_reasoner=MagicMock(),
        mlc_learning=MagicMock(), # This needs to be mockable for record_feedback
        notifier=MagicMock(),
    )
    
    # Ensure mlc_learning.record_feedback is async
    analyzer.mlc_learning.record_feedback = AsyncMock()
    # Ensure notification_service.notify_if_needed is async
    analyzer.notification_service.notify_if_needed = AsyncMock()
    # Ensure history_service.add_to_history is async
    analyzer.history_service.add_to_history = AsyncMock()
    
    # Override helpers to avoid complex logic
    # Make sure we mock both the method on the analyzer AND the underlying service method if called directly
    analyzer._generate_summary = AsyncMock(return_value={})
    analyzer._identify_alerts = AsyncMock(return_value=[])
    analyzer._calculate_risk_scores = AsyncMock(return_value={})
    analyzer._medication_review = AsyncMock(return_value={})
    
    # Mock the internal services designated by the Analyzer
    analyzer.patient_data_service.fetch_patient_data = AsyncMock(return_value={"id": "test-pat"})
    analyzer.patient_data_service.generate_summary = AsyncMock(return_value={})
    analyzer.alert_service.identify_alerts = AsyncMock(return_value=[])
    analyzer.risk_scoring_service.calculate_risk_scores = AsyncMock(return_value={})
    analyzer.risk_scoring_service.review_medications = AsyncMock(return_value={})
    
    # Run analysis
    result = await analyzer.analyze("test-pat", include_recommendations=False)
    
    # Verify Disclaimer Presence
    assert "regulatory_disclaimer" in result
    disclaimer = result["regulatory_disclaimer"]
    
    # Verify Disclaimer Content
    assert "NOT for primary diagnostic use" in disclaimer["text"]
    assert "FDA SaMD Guidance" in disclaimer["references"]

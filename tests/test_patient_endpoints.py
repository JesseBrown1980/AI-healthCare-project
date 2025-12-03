"""
Comprehensive HTTP endpoint tests for patient-related endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from backend.main import app
from backend.security import TokenContext
from backend.di import (
    get_patient_analyzer,
    get_fhir_connector,
    get_analysis_job_manager,
    get_audit_service,
    get_patient_summary_cache,
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def dependency_overrides_guard():
    """Save and restore FastAPI dependency overrides for each test."""
    original_overrides = dict(app.dependency_overrides)
    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides = original_overrides


@pytest.fixture
def auth_token():
    """Generate a demo auth token for testing."""
    from backend.api.v1.endpoints.auth import _issue_demo_token
    response = _issue_demo_token("test@example.com")
    return response.access_token


def test_list_patients_success(client, dependency_overrides_guard, auth_token):
    """Test successful patient list retrieval."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    from backend.audit_service import AuditService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.patient_data_service = MagicMock()
    mock_analyzer.patient_data_service.fetch_patient_data = AsyncMock(return_value={
        "patient": {"id": "patient-123", "resourceType": "Patient"},
        "medications": [],
        "conditions": [],
        "observations": [],
    })
    mock_analyzer.get_latest_analysis = AsyncMock(return_value=None)
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    with patch('backend.api.v1.endpoints.patients._dashboard_patient_list', return_value=[
        {"patient_id": "patient-123", "name": "Test Patient"}
    ]), \
    patch('backend.api.v1.endpoints.patients._build_patient_list_entry', new_callable=AsyncMock) as mock_build:
        mock_build.return_value = {
            "id": "patient-123",
            "patient_id": "patient-123",
            "name": "Test Patient",
            "full_name": "Test Patient",
            "age": 45,
            "latest_risk_score": 0.5,
        }
        
        response = client.get(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "patients" in data
        assert isinstance(data["patients"], list)


def test_list_patients_missing_auth(client, dependency_overrides_guard):
    """Test patient list retrieval without authentication."""
    response = client.get("/api/v1/patients")
    
    # Should require authentication
    assert response.status_code in [401, 403, 500, 503]


def test_list_patients_service_unavailable(client, dependency_overrides_guard, auth_token):
    """Test patient list when services are unavailable."""
    app.dependency_overrides[get_patient_analyzer] = lambda: None
    app.dependency_overrides[get_fhir_connector] = lambda: None
    
    response = client.get(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "not initialized" in error_msg.lower() or "unavailable" in error_msg.lower()


def test_get_dashboard_patients_success(client, dependency_overrides_guard, auth_token):
    """Test successful dashboard patients retrieval."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    from backend.analysis_cache import AnalysisJobManager
    from backend.audit_service import AuditService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.get_latest_analysis = AsyncMock(return_value={
        "risk_score": 0.5,
        "alerts": [],
    })
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    
    mock_job_manager = MagicMock(spec=AnalysisJobManager)
    mock_cache = {}
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_analysis_job_manager] = lambda: mock_job_manager
    app.dependency_overrides[get_patient_summary_cache] = lambda: mock_cache
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    with patch('backend.api.v1.endpoints.patients._dashboard_patient_list', return_value=[
        {"patient_id": "patient-123", "name": "Test Patient"}
    ]), \
    patch('backend.api.v1.endpoints.patients._get_patient_summary', new_callable=AsyncMock) as mock_get_summary:
        mock_get_summary.return_value = {
            "patient_id": "patient-123",
            "patient_name": "Test Patient",
            "overall_risk_score": 0.5,
            "highest_alert_severity": "low",
            "last_analysis": "2024-01-01T00:00:00Z",
        }
        
        response = client.get(
            "/api/v1/patients/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def test_get_alerts_success(client, dependency_overrides_guard, auth_token):
    """Test successful alerts retrieval."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    from backend.audit_service import AuditService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.get_latest_analysis = AsyncMock(return_value={
        "alerts": [
            {"severity": "high", "title": "Test Alert", "description": "Test description"}
        ],
        "risk_score": 0.8,
    })
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    with patch('backend.api.v1.endpoints.patients._dashboard_patient_list', return_value=[
        {"patient_id": "patient-123", "name": "Test Patient"}
    ]):
        response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)


def test_analyze_patient_success(client, dependency_overrides_guard, auth_token):
    """Test successful patient analysis."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    from backend.analysis_cache import AnalysisJobManager
    from backend.audit_service import AuditService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.analyze = AsyncMock(return_value={
        "risk_score": 0.6,
        "alerts": [],
        "recommendations": [],
        "summary": "Test analysis",
    })
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    
    mock_job_manager = MagicMock(spec=AnalysisJobManager)
    mock_job_manager.get_job_status = AsyncMock(return_value=None)
    mock_job_manager.submit_analysis = AsyncMock(return_value="job-123")
    mock_job_manager.cache_key = MagicMock(return_value="test-key")
    
    # get_or_create returns (result, from_cache) tuple
    analysis_result = {
        "risk_score": 0.6,
        "alerts": [],
        "recommendations": [],
        "summary": {"patient_name": "Test Patient"},
        "patient_id": "patient-123",
        "overall_risk_score": 0.6,
    }
    mock_job_manager.get_or_create = AsyncMock(return_value=(analysis_result, False))
    
    mock_cache = {}
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_analysis_job_manager] = lambda: mock_job_manager
    app.dependency_overrides[get_patient_summary_cache] = lambda: mock_cache
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    response = client.post(
        "/api/v1/analyze-patient?fhir_patient_id=patient-123&include_recommendations=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    # AnalyzePatientResponse requires patient_id field
    assert "patient_id" in data
    assert data["patient_id"] == "patient-123"


def test_analyze_patient_missing_auth(client, dependency_overrides_guard):
    """Test patient analysis without authentication."""
    response = client.post(
        "/api/v1/analyze-patient?fhir_patient_id=patient-123",
    )
    
    # Should require authentication
    assert response.status_code in [401, 403, 500, 503]


def test_get_patient_fhir_success(client, dependency_overrides_guard, auth_token):
    """Test successful FHIR patient data retrieval."""
    from backend.fhir_connector import FhirResourceService
    from backend.audit_service import AuditService
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        def __init__(self):
            self.patient_data = {
                "id": "patient-123",
                "resourceType": "Patient",
                "name": [{"given": ["John"], "family": "Doe"}],
            }
        
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
        
        async def get_patient(self, patient_id):
            return self.patient_data
    
    mock_fhir = MockFHIRConnector()
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    mock_audit.record_event = AsyncMock()
    
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    response = client.get(
        "/api/v1/patient/patient-123/fhir",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["patient_id"] == "patient-123"
    assert "data" in data


def test_get_patient_fhir_invalid_patient_id(client, dependency_overrides_guard, auth_token):
    """Test FHIR patient retrieval with invalid patient ID."""
    from backend.fhir_connector import FhirResourceService
    from backend.audit_service import AuditService
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    mock_audit = MagicMock(spec=AuditService)
    
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    # Invalid patient ID format (path traversal attempt)
    response = client.get(
        "/api/v1/patient/../invalid/fhir",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    # Should return validation error or 404 if path is parsed incorrectly
    assert response.status_code in [400, 404, 422, 500]


def test_get_patient_fhir_service_unavailable(client, dependency_overrides_guard, auth_token):
    """Test FHIR patient retrieval when service is unavailable."""
    from backend.audit_service import AuditService
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    app.dependency_overrides[get_fhir_connector] = lambda: None
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    response = client.get(
        "/api/v1/patient/patient-123/fhir",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "not initialized" in error_msg.lower() or "unavailable" in error_msg.lower()


def test_get_patient_explain_success(client, dependency_overrides_guard, auth_token):
    """Test successful patient explainability retrieval."""
    from backend.fhir_connector import FhirResourceService
    from backend.audit_service import AuditService
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    from backend.patient_analyzer import PatientAnalyzer
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.analyze = AsyncMock(return_value={
        "risk_score": 0.6,
        "patient_id": "patient-123",
        "alerts": [],
    })
    
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    with patch('backend.api.v1.endpoints.patients.explain_risk') as mock_explain:
        mock_explain.return_value = {
            "risk_score": 0.6,
            "feature_names": ["age", "conditions", "medications"],
            "shap_values": [0.2, 0.3, 0.1],
            "base_value": 0.5,
            "model_type": "gradient_boosting",
        }
        
        response = client.get(
            "/api/v1/patient/patient-123/explain",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data or "shap_values" in data or "status" in data


def test_get_dashboard_summary_success(client, dependency_overrides_guard, auth_token):
    """Test successful dashboard summary retrieval."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    from backend.analysis_cache import AnalysisJobManager
    from backend.audit_service import AuditService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.get_latest_analysis = AsyncMock(return_value={
        "risk_score": 0.5,
        "alerts": [],
    })
    
    from contextlib import asynccontextmanager
    
    class MockFHIRConnector:
        @asynccontextmanager
        async def request_context(self, access_token, scopes, patient):
            yield
    
    mock_fhir = MockFHIRConnector()
    
    mock_job_manager = MagicMock(spec=AnalysisJobManager)
    mock_cache = {}
    
    mock_audit = MagicMock(spec=AuditService)
    mock_audit.new_correlation_id = MagicMock(return_value="test-correlation-id")
    
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    app.dependency_overrides[get_analysis_job_manager] = lambda: mock_job_manager
    app.dependency_overrides[get_patient_summary_cache] = lambda: mock_cache
    app.dependency_overrides[get_audit_service] = lambda: mock_audit
    
    with patch('backend.api.v1.endpoints.patients._dashboard_patient_list', return_value=[
        {"patient_id": "patient-123", "name": "Test Patient"}
    ]), \
    patch('backend.api.v1.endpoints.patients._get_patient_summary', new_callable=AsyncMock) as mock_get_summary:
        mock_get_summary.return_value = {
            "patient_id": "patient-123",
            "patient_name": "Test Patient",
            "overall_risk_score": 0.5,
            "highest_alert_severity": "low",
            "last_analysis": "2024-01-01T00:00:00Z",
        }
        
        response = client.get(
            "/api/v1/dashboard-summary",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

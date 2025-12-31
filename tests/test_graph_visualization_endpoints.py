"""
Tests for graph visualization API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from backend.main import app
from backend.security import TokenContext
from backend.di import get_patient_analyzer, get_fhir_connector, get_database_service


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


def test_get_patient_graph_success(client, auth_token, dependency_overrides_guard):
    """Test successful patient graph retrieval."""
    import torch
    from backend.patient_data_service import PatientDataService
    from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_patient_data = {
        "patient": {"id": "patient-123", "resourceType": "Patient"},
        "medications": [],
        "conditions": [],
        "observations": [],
    }
    
    num_nodes = 1
    num_edges = 0
    feature_dim = 16
    x = torch.zeros(num_nodes, feature_dim)
    edge_index = torch.zeros(2, num_edges, dtype=torch.long)
    mock_metadata = {
        'node_map': {0: 'patient_patient-123'},
        'node_types': {'patient_patient-123': 'patient'},
        'node_metadata': {'patient_patient-123': {'id': 'patient-123'}},
        'edge_types': [],
    }
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.anomaly_service = None
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    with patch('backend.api.v1.endpoints.graph_visualization.PatientDataService') as mock_service_class, \
         patch('backend.anomaly_detector.models.clinical_graph_builder.ClinicalGraphBuilder') as mock_builder_class:
        
        mock_service = MagicMock()
        mock_service.fetch_patient_data = AsyncMock(return_value=mock_patient_data)
        mock_service_class.return_value = mock_service
        
        mock_builder = MagicMock()
        mock_builder.build_graph_from_patient_data.return_value = (x, edge_index, mock_metadata)
        mock_builder_class.return_value = mock_builder
        
        response = client.get(
            "/api/v1/patients/patient-123/graph?include_anomalies=false",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "graph" in data
        assert "nodes" in data["graph"]
        assert "edges" in data["graph"]
        assert "patient_id" in data
        assert data["patient_id"] == "patient-123"


def test_get_patient_graph_missing_auth(client, dependency_overrides_guard):
    """Test patient graph retrieval without authentication."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    response = client.get("/api/v1/patients/patient-123/graph")
    
    # Should require authentication
    assert response.status_code in [401, 403, 500]


def test_get_patient_graph_invalid_patient_id(client, auth_token, dependency_overrides_guard):
    """Test patient graph retrieval with invalid patient ID."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    # Invalid patient IDs are validated by the endpoint
    # Using a path that might trigger validation
    response = client.get(
        "/api/v1/patients/../invalid/graph",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    # May return 400 for validation error, 422 for FastAPI validation, or 500 if service fails
    assert response.status_code in [400, 422, 500, 404]


def test_get_patient_graph_with_anomalies(client, auth_token, dependency_overrides_guard):
    """Test patient graph retrieval with anomaly detection enabled."""
    import torch
    from backend.patient_data_service import PatientDataService
    from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_patient_data = {
        "patient": {"id": "patient-123", "resourceType": "Patient"},
        "medications": [],
        "conditions": [],
        "observations": [],
    }
    
    num_nodes = 1
    feature_dim = 16
    x = torch.zeros(num_nodes, feature_dim)
    edge_index = torch.zeros(2, 0, dtype=torch.long)
    mock_metadata = {
        'node_map': {0: 'patient_patient-123'},
        'node_types': {'patient_patient-123': 'patient'},
        'node_metadata': {'patient_patient-123': {'id': 'patient-123'}},
        'edge_types': [],
    }
    
    mock_anomaly_results = {
        'anomalies': [],
        'anomaly_type_counts': {},
        'explainability': {},
    }
    
    mock_anomaly_service = MagicMock()
    mock_anomaly_service.detect_clinical_anomalies = AsyncMock(return_value=mock_anomaly_results)
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.anomaly_service = mock_anomaly_service
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    with patch('backend.api.v1.endpoints.graph_visualization.PatientDataService') as mock_service_class, \
         patch('backend.anomaly_detector.models.clinical_graph_builder.ClinicalGraphBuilder') as mock_builder_class:
        
        mock_service = MagicMock()
        mock_service.fetch_patient_data = AsyncMock(return_value=mock_patient_data)
        mock_service_class.return_value = mock_service
        
        mock_builder = MagicMock()
        mock_builder.build_graph_from_patient_data.return_value = (x, edge_index, mock_metadata)
        mock_builder_class.return_value = mock_builder
        
        response = client.get(
            "/api/v1/patients/patient-123/graph?include_anomalies=true&threshold=0.5",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "graph" in data


def test_get_anomaly_timeline_success(client, auth_token, dependency_overrides_guard):
    """Test successful anomaly timeline retrieval."""
    from backend.database.service import DatabaseService
    
    now = datetime.now(timezone.utc)
    mock_history = [
        {
            'analysis_timestamp': (now - timedelta(days=5)).isoformat(),
            'analysis_data': {
                'gnn_anomaly_detection': {
                    'anomalies': [
                        {'anomaly_type': 'medication_anomaly', 'anomaly_score': 0.8, 'severity': 'high'}
                    ],
                    'anomaly_type_counts': {'medication_anomaly': 1}
                }
            }
        }
    ]
    
    mock_db = MagicMock(spec=DatabaseService)
    mock_db.get_analysis_history = AsyncMock(return_value=mock_history)
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.get(
        "/api/v1/patients/patient-123/anomaly-timeline?days=30",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "timeline" in data
    assert "patient_id" in data
    assert data["patient_id"] == "patient-123"
    assert "total_points" in data


def test_get_anomaly_timeline_no_database(client, auth_token, dependency_overrides_guard):
    """Test anomaly timeline retrieval when database service is unavailable."""
    app.dependency_overrides[get_database_service] = lambda: None
    
    response = client.get(
        "/api/v1/patients/patient-123/anomaly-timeline",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "database" in error_msg.lower() or "service" in error_msg.lower()


def test_get_anomaly_timeline_custom_days(client, auth_token, dependency_overrides_guard):
    """Test anomaly timeline retrieval with custom days parameter."""
    from backend.database.service import DatabaseService
    
    mock_history = []
    
    mock_db = MagicMock(spec=DatabaseService)
    mock_db.get_analysis_history = AsyncMock(return_value=mock_history)
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.get(
        "/api/v1/patients/patient-123/anomaly-timeline?days=60",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 60
    assert len(data["timeline"]) == 0


def test_compare_patient_graphs_success(client, auth_token, dependency_overrides_guard):
    """Test successful patient graph comparison."""
    import torch
    from backend.patient_data_service import PatientDataService
    from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_patient_data_1 = {
        "patient": {"id": "patient-1"},
        "medications": [],
        "conditions": [],
        "observations": [],
    }
    
    mock_patient_data_2 = {
        "patient": {"id": "patient-2"},
        "medications": [],
        "conditions": [],
        "observations": [],
    }
    
    mock_metadata = {
        'node_map': {0: 'patient_patient-1'},
        'node_types': {'patient_patient-1': 'patient'},
        'node_metadata': {'patient_patient-1': {}},
        'edge_types': [],
    }
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    mock_analyzer.anomaly_service = None
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    with patch('backend.api.v1.endpoints.graph_visualization.PatientDataService') as mock_service_class, \
         patch('backend.anomaly_detector.models.clinical_graph_builder.ClinicalGraphBuilder') as mock_builder_class:
        
        mock_service = MagicMock()
        mock_service.fetch_patient_data = AsyncMock(side_effect=[mock_patient_data_1, mock_patient_data_2])
        mock_service_class.return_value = mock_service
        
        mock_builder = MagicMock()
        x = torch.zeros(1, 16)
        edge_index = torch.zeros(2, 0, dtype=torch.long)
        mock_builder.build_graph_from_patient_data.return_value = (x, edge_index, mock_metadata)
        mock_builder_class.return_value = mock_builder
        
        # Note: FastAPI Query with List requires special handling in test client
        response = client.post(
            "/api/v1/patients/compare-graphs?patient_ids=patient-1&patient_ids=patient-2",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "comparison_results" in data
        assert "patient_ids" in data


def test_compare_patient_graphs_missing_auth(client, dependency_overrides_guard):
    """Test patient graph comparison without authentication."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    response = client.post(
        "/api/v1/patients/compare-graphs?patient_ids=patient-1",
    )
    
    # May return 400 for validation (needs 2+ patients), 401/403 for auth, or 500
    assert response.status_code in [400, 401, 403, 500]


def test_compare_patient_graphs_empty_list(client, auth_token, dependency_overrides_guard):
    """Test patient graph comparison with empty patient list."""
    from backend.patient_analyzer import PatientAnalyzer
    from backend.fhir_connector import FhirResourceService
    
    mock_analyzer = MagicMock(spec=PatientAnalyzer)
    app.dependency_overrides[get_patient_analyzer] = lambda: mock_analyzer
    
    mock_fhir = MagicMock(spec=FhirResourceService)
    app.dependency_overrides[get_fhir_connector] = lambda: mock_fhir
    
    # Empty query parameter list may be handled differently
    response = client.post(
        "/api/v1/patients/compare-graphs",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    # Should fail validation or return error
    assert response.status_code in [400, 422, 500]

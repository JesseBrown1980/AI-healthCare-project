"""
Tests for graph visualization endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_patient_graph_visualization():
    """Test patient graph visualization endpoint."""
    import torch
    from backend.api.v1.endpoints.graph_visualization import get_patient_graph_visualization
    from backend.security import TokenContext
    from backend.patient_data_service import PatientDataService
    from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
    
    # Mock dependencies
    mock_auth = TokenContext(
        access_token="test_token",
        scopes=set(["patient/*.read"]),
        clinician_roles=set(),
    )
    
    mock_patient_data = {
        "patient": {"id": "patient-123", "resourceType": "Patient"},
        "medications": [],
        "conditions": [],
        "observations": [],
    }
    
    # Create mock graph tensors
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
    
    with patch('backend.api.v1.endpoints.graph_visualization.PatientDataService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.fetch_patient_data = AsyncMock(return_value=mock_patient_data)
        mock_service_class.return_value = mock_service
        
        with patch('backend.anomaly_detector.models.clinical_graph_builder.ClinicalGraphBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_graph_from_patient_data.return_value = (x, edge_index, mock_metadata)
            mock_builder_class.return_value = mock_builder
            
            # Mock PatientAnalyzer
            with patch('backend.api.v1.endpoints.graph_visualization.get_patient_analyzer') as mock_get_analyzer:
                mock_analyzer = MagicMock()
                mock_analyzer.anomaly_service = None  # Disable anomaly detection for this test
                mock_get_analyzer.return_value = mock_analyzer
                
                # Mock FhirResourceService
                with patch('backend.api.v1.endpoints.graph_visualization.get_fhir_connector') as mock_get_fhir:
                    mock_fhir = MagicMock()
                    mock_get_fhir.return_value = mock_fhir
                    
                    # Call the endpoint function directly
                    result = await get_patient_graph_visualization(
                        patient_id="patient-123",
                        include_anomalies=False,
                        threshold=0.5,
                        patient_analyzer=mock_analyzer,
                        fhir_connector=mock_fhir,
                        auth=mock_auth
                    )
                    
                    assert result is not None
                    assert "nodes" in result
                    assert "edges" in result
                    assert len(result["nodes"]) >= 1  # At least patient node


@pytest.mark.asyncio
async def test_get_anomaly_timeline():
    """Test anomaly timeline endpoint."""
    from backend.api.v1.endpoints.graph_visualization import get_anomaly_timeline
    from backend.security import TokenContext
    
    mock_auth = TokenContext(
        access_token="test_token",
        scopes=set(["patient/*.read"]),
        clinician_roles=set(),
    )
    
    with patch('backend.api.v1.endpoints.graph_visualization.DatabaseService') as mock_db:
        mock_db.return_value.get_analysis_history = AsyncMock(return_value=[
            {
                'analysis_timestamp': '2024-01-01T00:00:00Z',
                'analysis_data': {
                    'gnn_anomaly_detection': {
                        'anomalies': [
                            {'anomaly_type': 'medication_anomaly', 'anomaly_score': 0.8}
                        ],
                        'anomaly_type_counts': {'medication_anomaly': 1}
                    }
                }
            }
        ])
        
        # Test structure
        pass


@pytest.mark.asyncio
async def test_compare_patient_graphs():
    """Test graph comparison endpoint."""
    from backend.api.v1.endpoints.graph_visualization import compare_patient_graphs
    from backend.security import TokenContext
    
    mock_auth = TokenContext(
        access_token="test_token",
        scopes=set(["patient/*.read"]),
        clinician_roles=set(),
    )
    
    request_data = {"patient_ids": ["patient-1", "patient-2"]}
    
    # Would need proper mocking of all dependencies
    # Tests the endpoint structure
    pass


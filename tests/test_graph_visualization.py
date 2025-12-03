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
                    mock_request = MagicMock()
                    result = await get_patient_graph_visualization(
                        request=mock_request,
                        patient_id="patient-123",
                        include_anomalies=False,
                        threshold=0.5,
                        patient_analyzer=mock_analyzer,
                        fhir_connector=mock_fhir,
                        auth=mock_auth
                    )
                    
                    assert result is not None
                    assert "graph" in result
                    assert "nodes" in result["graph"]
                    assert "edges" in result["graph"]
                    assert len(result["graph"]["nodes"]) >= 1  # At least patient node
                    assert "patient_id" in result
                    assert "statistics" in result


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
    
    from datetime import datetime, timezone, timedelta
    
    # Use recent timestamps (within last 30 days)
    now = datetime.now(timezone.utc)
    mock_history = [
        {
            'analysis_timestamp': (now - timedelta(days=5)).isoformat(),
            'analysis_data': {
                'gnn_anomaly_detection': {
                    'anomalies': [
                        {'anomaly_type': 'medication_anomaly', 'anomaly_score': 0.8}
                    ],
                    'anomaly_type_counts': {'medication_anomaly': 1}
                }
            }
        },
        {
            'analysis_timestamp': (now - timedelta(days=2)).isoformat(),
            'analysis_data': {
                'gnn_anomaly_detection': {
                    'anomalies': [
                        {'anomaly_type': 'lab_value_anomaly', 'anomaly_score': 0.7}
                    ],
                    'anomaly_type_counts': {'lab_value_anomaly': 1}
                }
            }
        }
    ]
    
    with patch('backend.api.v1.endpoints.graph_visualization.get_database_service') as mock_get_db:
        mock_db = MagicMock()
        mock_db.get_analysis_history = AsyncMock(return_value=mock_history)
        mock_get_db.return_value = mock_db
        
        mock_request = MagicMock()
        result = await get_anomaly_timeline(
            request=mock_request,
            patient_id="patient-123",
            days=30,
            db_service=mock_db,
            auth=mock_auth
        )
        
        assert result is not None
        assert "timeline" in result
        assert "patient_id" in result
        assert len(result["timeline"]) == 2


@pytest.mark.asyncio
async def test_compare_patient_graphs():
    """Test graph comparison endpoint."""
    import torch
    from backend.api.v1.endpoints.graph_visualization import compare_patient_graphs
    from backend.security import TokenContext
    
    mock_auth = TokenContext(
        access_token="test_token",
        scopes=set(["patient/*.read"]),
        clinician_roles=set(),
    )
    
    patient_ids = ["patient-1", "patient-2"]
    
    # Mock patient data
    mock_patient_data_1 = {
        "patient": {"id": "patient-1"},
        "medications": [{"id": "med-1", "medicationCodeableConcept": {"coding": [{"display": "Metformin"}]}}],
        "conditions": [],
        "observations": [],
    }
    
    mock_patient_data_2 = {
        "patient": {"id": "patient-2"},
        "medications": [],
        "conditions": [{"id": "cond-1", "code": {"coding": [{"display": "Diabetes"}]}}],
        "observations": [],
    }
    
    # Mock graph metadata
    mock_metadata_1 = {
        'node_map': {0: 'patient_patient-1', 1: 'medication_med-1'},
        'node_types': {'patient_patient-1': 'patient', 'medication_med-1': 'medication'},
        'node_metadata': {'patient_patient-1': {}, 'medication_med-1': {'name': 'Metformin'}},
        'edge_types': ['prescribed'],
    }
    
    mock_metadata_2 = {
        'node_map': {0: 'patient_patient-2', 1: 'condition_cond-1'},
        'node_types': {'patient_patient-2': 'patient', 'condition_cond-1': 'condition'},
        'node_metadata': {'patient_patient-2': {}, 'condition_cond-1': {'name': 'Diabetes'}},
        'edge_types': ['diagnosed'],
    }
    
    with patch('backend.api.v1.endpoints.graph_visualization.PatientDataService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.fetch_patient_data = AsyncMock(side_effect=[mock_patient_data_1, mock_patient_data_2])
        mock_service_class.return_value = mock_service
        
        with patch('backend.anomaly_detector.models.clinical_graph_builder.ClinicalGraphBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_graph_from_patient_data.side_effect = [
                (torch.zeros(2, 16), torch.zeros(2, 1, dtype=torch.long), mock_metadata_1),
                (torch.zeros(2, 16), torch.zeros(2, 1, dtype=torch.long), mock_metadata_2),
            ]
            mock_builder_class.return_value = mock_builder
            
            with patch('backend.api.v1.endpoints.graph_visualization.get_patient_analyzer') as mock_get_analyzer:
                mock_analyzer = MagicMock()
                mock_analyzer.anomaly_service = None
                mock_get_analyzer.return_value = mock_analyzer
                
                with patch('backend.api.v1.endpoints.graph_visualization.get_fhir_connector') as mock_get_fhir:
                    mock_fhir = MagicMock()
                    mock_get_fhir.return_value = mock_fhir
                    
                    mock_request = MagicMock()
                    result = await compare_patient_graphs(
                        request=mock_request,
                        patient_ids=patient_ids,
                        include_anomalies=False,
                        threshold=0.5,
                        patient_analyzer=mock_analyzer,
                        fhir_connector=mock_fhir,
                        auth=mock_auth
                    )
                    
                    assert result is not None
                    assert "comparison_results" in result
                    assert len(result["comparison_results"]) == 2
                    assert "comparison_metrics" in result
                    assert "patient_ids" in result


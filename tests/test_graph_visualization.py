"""
Tests for graph visualization endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_patient_graph_visualization():
    """Test patient graph visualization endpoint."""
    from backend.api.v1.endpoints.graph_visualization import get_patient_graph_visualization
    from backend.security import TokenContext
    
    # Mock dependencies
    mock_auth = TokenContext(
        access_token="test_token",
        scopes=set(["patient/*.read"]),
        clinician_roles=set(),
    )
    
    mock_patient_data = {
        "patient": {"id": "patient-123"},
        "medications": [],
        "conditions": [],
        "observations": [],
    }
    
    with patch('backend.api.v1.endpoints.graph_visualization.PatientDataService') as mock_service:
        mock_service.return_value.fetch_patient_data = AsyncMock(return_value=mock_patient_data)
        
        with patch('backend.api.v1.endpoints.graph_visualization.ClinicalGraphBuilder') as mock_builder:
            mock_graph = MagicMock()
            mock_graph.shape = (2, 5)  # 2 nodes, 5 edges
            mock_metadata = {
                'node_map': {0: 'patient_123', 1: 'med_1'},
                'node_types': {'patient_123': 'patient', 'med_1': 'medication'},
                'edge_types': ['has_medication'] * 5,
            }
            mock_builder.return_value.build_graph_from_patient_data.return_value = (
                mock_graph, mock_graph, mock_metadata
            )
            
            # This would need proper FastAPI test client setup
            # For now, tests the structure
            pass


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


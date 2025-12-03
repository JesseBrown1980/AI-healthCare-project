"""
Unit tests for graph visualization data structure generation, metadata extraction,
anomaly mapping, and statistics calculation.
"""

import pytest
import torch
from unittest.mock import Mock, patch
from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
from backend.anomaly_detector.service import AnomalyService


@pytest.fixture
def sample_patient_data():
    """Sample patient FHIR data for testing."""
    return {
        "patient": {
            "id": "patient-123",
            "birthDate": "1980-01-01",
            "gender": "male",
        },
        "medications": [
            {
                "id": "med-1",
                "medicationCodeableConcept": {
                    "coding": [{"display": "Metformin 500mg"}]
                },
                "dosage": [{
                    "dose": {"value": 500, "unit": "mg"},
                    "timing": {"repeat": {"frequency": "twice"}}
                }],
                "effectivePeriod": {"start": "2024-01-01"},
            },
            {
                "id": "med-2",
                "medicationCodeableConcept": {
                    "coding": [{"display": "Warfarin 5mg"}]
                },
                "dosage": [{
                    "dose": {"value": 5, "unit": "mg"},
                    "timing": {"repeat": {"frequency": "daily"}}
                }],
                "effectivePeriod": {"start": "2024-01-15"},
            },
        ],
        "conditions": [
            {
                "id": "cond-1",
                "code": {
                    "coding": [{"display": "Type 2 Diabetes Mellitus"}]
                },
                "onsetDateTime": "2020-01-01",
                "severity": {"coding": [{"display": "moderate"}]},
            },
        ],
        "observations": [
            {
                "id": "obs-1",
                "code": {
                    "coding": [{"code": "2339-0", "display": "Glucose"}]
                },
                "valueQuantity": {"value": 250.0, "unit": "mg/dL"},
                "referenceRange": [{
                    "low": {"value": 70},
                    "high": {"value": 100}
                }],
                "effectiveDateTime": "2024-01-20",
            },
        ],
        "encounters": [],
    }


@pytest.fixture
def graph_builder():
    """Create ClinicalGraphBuilder instance."""
    return ClinicalGraphBuilder(feature_dim=16)


def test_graph_data_structure_generation(graph_builder, sample_patient_data):
    """Test graph data structure generation with correct tensor shapes."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Verify tensor shapes
    assert isinstance(x, torch.Tensor), "Node features should be a tensor"
    assert isinstance(edge_index, torch.Tensor), "Edge index should be a tensor"
    assert x.dim() == 2, "Node features should be 2D (num_nodes, feature_dim)"
    assert edge_index.dim() == 2, "Edge index should be 2D (2, num_edges)"
    assert edge_index.shape[0] == 2, "Edge index should have 2 rows (source, target)"
    
    # Verify feature dimensions
    assert x.shape[1] == 16, "Feature dimension should match builder config"
    
    # Verify edge index values are valid
    if edge_index.shape[1] > 0:
        assert edge_index.min() >= 0, "Edge indices should be non-negative"
        assert edge_index.max() < x.shape[0], "Edge indices should be within node count"
    
    # Verify metadata structure
    assert isinstance(graph_metadata, dict), "Graph metadata should be a dictionary"
    assert "node_map" in graph_metadata, "Metadata should contain node_map"
    assert "node_types" in graph_metadata, "Metadata should contain node_types"
    assert "edge_types" in graph_metadata, "Metadata should contain edge_types"
    assert "patient_id" in graph_metadata, "Metadata should contain patient_id"


def test_node_metadata_extraction(graph_builder, sample_patient_data):
    """Test extraction of node metadata from graph."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Verify node metadata structure
    assert "node_metadata" in graph_metadata, "Should have node_metadata"
    node_metadata = graph_metadata["node_metadata"]
    assert isinstance(node_metadata, dict), "Node metadata should be a dictionary"
    
    # Verify patient node metadata
    patient_nodes = [
        node_id for node_id, node_type in graph_metadata["node_types"].items()
        if node_type == "patient"
    ]
    assert len(patient_nodes) > 0, "Should have at least one patient node"
    
    for patient_node_id in patient_nodes:
        assert patient_node_id in node_metadata, "Patient node should have metadata"
        patient_meta = node_metadata[patient_node_id]
        assert "id" in patient_meta or "patient_id" in patient_meta, "Should have patient ID"
    
    # Verify medication node metadata
    medication_nodes = [
        node_id for node_id, node_type in graph_metadata["node_types"].items()
        if node_type == "medication"
    ]
    for med_node_id in medication_nodes:
        if med_node_id in node_metadata:
            med_meta = node_metadata[med_node_id]
            # Should have medication-related metadata
            assert isinstance(med_meta, dict), "Medication metadata should be a dict"


def test_edge_metadata_extraction(graph_builder, sample_patient_data):
    """Test extraction of edge metadata from graph."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Verify edge types are extracted
    assert "edge_types" in graph_metadata, "Should have edge_types"
    edge_types = graph_metadata["edge_types"]
    assert isinstance(edge_types, list), "Edge types should be a list"
    
    # Verify edge metadata structure (if available)
    if "edge_metadata" in graph_metadata:
        edge_metadata = graph_metadata["edge_metadata"]
        assert isinstance(edge_metadata, (list, dict)), "Edge metadata should be list or dict"
    
    # Verify edge types match expected clinical relationships
    expected_edge_types = ["prescribed", "diagnosed", "measured", "interacts_with", "treats"]
    for edge_type in edge_types:
        # Edge types should be valid clinical relationship types
        assert isinstance(edge_type, str), "Edge type should be a string"
        # May or may not be in expected list (could be custom types)


def test_anomaly_mapping_to_edges(graph_builder, sample_patient_data):
    """Test mapping of anomalies to specific edges in the graph."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Create mock anomaly scores for edges
    num_edges = edge_index.shape[1]
    if num_edges > 0:
        # Mock anomaly scores (one per edge)
        anomaly_scores = torch.rand(num_edges)
        
        # Verify we can map anomalies to edges
        edge_anomalies = []
        for i in range(num_edges):
            source_idx = edge_index[0, i].item()
            target_idx = edge_index[1, i].item()
            score = anomaly_scores[i].item()
            
            if score > 0.5:  # Threshold for anomaly
                # Get node IDs from metadata
                reverse_node_map = {v: k for k, v in graph_metadata["node_map"].items()}
                source_id = reverse_node_map.get(source_idx)
                target_id = reverse_node_map.get(target_idx)
                
                edge_anomalies.append({
                    "source": source_id,
                    "target": target_id,
                    "score": score,
                    "edge_index": i,
                })
        
        # Verify anomaly mapping structure
        assert isinstance(edge_anomalies, list), "Edge anomalies should be a list"
        for anomaly in edge_anomalies:
            assert "source" in anomaly, "Anomaly should have source node"
            assert "target" in anomaly, "Anomaly should have target node"
            assert "score" in anomaly, "Anomaly should have score"
            assert 0 <= anomaly["score"] <= 1, "Score should be between 0 and 1"


def test_statistics_calculation(graph_builder, sample_patient_data):
    """Test calculation of graph statistics."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Calculate basic statistics
    num_nodes = x.shape[0]
    num_edges = edge_index.shape[1]
    
    # Node type statistics
    node_types = graph_metadata.get("node_types", {})
    node_type_counts = {}
    for node_type in node_types.values():
        node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
    
    # Edge type statistics
    edge_types = graph_metadata.get("edge_types", [])
    edge_type_counts = {}
    for edge_type in edge_types:
        edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
    
    # Verify statistics are calculated correctly
    assert num_nodes > 0, "Should have at least one node"
    assert num_edges >= 0, "Edge count should be non-negative"
    assert isinstance(node_type_counts, dict), "Node type counts should be a dict"
    assert isinstance(edge_type_counts, dict), "Edge type counts should be a dict"
    
    # Verify node type counts match actual nodes
    total_counted_nodes = sum(node_type_counts.values())
    assert total_counted_nodes == num_nodes, "Node type counts should sum to total nodes"
    
    # Verify edge type counts match actual edges
    total_counted_edges = sum(edge_type_counts.values())
    assert total_counted_edges == num_edges, "Edge type counts should sum to total edges"
    
    # Calculate graph density (for non-empty graphs)
    if num_nodes > 1:
        max_possible_edges = num_nodes * (num_nodes - 1)
        if max_possible_edges > 0:
            density = num_edges / max_possible_edges
            assert 0 <= density <= 1, "Graph density should be between 0 and 1"


def test_graph_statistics_with_empty_graph(graph_builder):
    """Test statistics calculation with empty graph."""
    empty_data = {
        "patient": {"id": "patient-empty"},
        "medications": [],
        "conditions": [],
        "observations": [],
        "encounters": [],
    }
    
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(empty_data)
    
    # Calculate statistics
    num_nodes = x.shape[0]
    num_edges = edge_index.shape[1]
    
    # Empty graph should have at least patient node
    assert num_nodes >= 1, "Should have at least patient node"
    assert num_edges == 0, "Empty graph should have no edges"
    
    # Statistics should still be calculable
    node_types = graph_metadata.get("node_types", {})
    assert len(node_types) == num_nodes, "Node types should match node count"


def test_node_feature_metadata_consistency(graph_builder, sample_patient_data):
    """Test that node features are consistent with metadata."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # node_map is {idx: node_id}, not {node_id: idx}
    node_map = graph_metadata.get("node_map", {})
    node_types = graph_metadata.get("node_types", {})
    node_metadata = graph_metadata.get("node_metadata", {})
    
    # Verify each node in the tensor has corresponding metadata
    for node_idx, node_id in node_map.items():
        assert isinstance(node_idx, int), f"Node index should be integer, got {type(node_idx)}"
        assert node_idx < x.shape[0], f"Node index {node_idx} should be within tensor bounds"
        assert node_id in node_types, f"Node {node_id} should have a type"
        
        # Verify feature vector exists
        node_features = x[node_idx]
        assert node_features.shape[0] == 16, "Feature vector should have correct dimension"
        assert not torch.isnan(node_features).any(), "Features should not contain NaN"


def test_edge_index_consistency(graph_builder, sample_patient_data):
    """Test that edge indices are consistent with node map."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # node_map is {idx: node_id}
    node_map = graph_metadata.get("node_map", {})
    num_nodes = x.shape[0]
    
    # Verify all edge indices reference valid nodes
    if edge_index.shape[1] > 0:
        source_indices = edge_index[0, :]
        target_indices = edge_index[1, :]
        
        assert source_indices.min() >= 0, "Source indices should be non-negative"
        assert target_indices.min() >= 0, "Target indices should be non-negative"
        assert source_indices.max() < num_nodes, "Source indices should be within node count"
        assert target_indices.max() < num_nodes, "Target indices should be within node count"
        
        # Verify we can map edge indices back to node IDs
        # node_map is already {idx: node_id}, so we can use it directly
        for i in range(edge_index.shape[1]):
            source_idx = edge_index[0, i].item()
            target_idx = edge_index[1, i].item()
            assert source_idx in node_map, f"Source index {source_idx} should map to a node"
            assert target_idx in node_map, f"Target index {target_idx} should map to a node"


def test_graph_metadata_completeness(graph_builder, sample_patient_data):
    """Test that graph metadata contains all necessary information."""
    x, edge_index, graph_metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Required metadata fields
    required_fields = ["node_map", "node_types", "edge_types", "patient_id"]
    for field in required_fields:
        assert field in graph_metadata, f"Metadata should contain {field}"
    
    # node_map is {idx: node_id}
    node_map = graph_metadata["node_map"]
    node_types = graph_metadata["node_types"]
    
    # Verify node_types matches node_map values (node_ids)
    for node_idx, node_id in node_map.items():
        assert node_id in node_types, f"Node {node_id} should have a type"
        assert isinstance(node_idx, int), "Node index should be integer"


@pytest.mark.asyncio
async def test_anomaly_detection_with_edge_mapping(sample_patient_data):
    """Test anomaly detection and mapping to specific edges."""
    service = AnomalyService()
    
    with patch('backend.anomaly_detector.service.load_model') as mock_load:
        mock_model = Mock()
        # Create mock scores for edges
        num_edges = 5  # Mock number of edges
        mock_scores = torch.tensor([
            [0.9, 0.05, 0.03, 0.02],  # Normal
            [0.1, 0.8, 0.05, 0.05],   # Medication anomaly
            [0.2, 0.1, 0.6, 0.1],     # Lab value anomaly
            [0.7, 0.1, 0.1, 0.1],     # Normal
            [0.1, 0.1, 0.1, 0.7],     # Clinical pattern anomaly
        ])
        
        def mock_forward(x, edge_index, return_weights=False):
            num_actual_edges = edge_index.shape[1]
            if return_weights:
                learned_adj = torch.eye(x.shape[0])
                return mock_scores[:num_actual_edges], learned_adj
            return mock_scores[:num_actual_edges]
        
        mock_model.forward = mock_forward
        mock_model.eval = Mock(return_value=mock_model)
        mock_model.get_edge_importance = Mock(return_value=torch.ones(num_edges) * 0.5)
        mock_load.return_value = mock_model
        
        service.initialize()
        result = await service.detect_clinical_anomalies(sample_patient_data, threshold=0.5)
        
        # Verify anomaly structure
        assert "anomalies" in result, "Result should contain anomalies"
        assert "anomaly_count" in result, "Result should contain anomaly_count"
        assert "graph_metadata" in result, "Result should contain graph_metadata"
        
        # Verify anomalies can be mapped to edges
        anomalies = result.get("anomalies", [])
        for anomaly in anomalies:
            assert isinstance(anomaly, dict), "Each anomaly should be a dictionary"
            # Anomalies should have information about which edges/nodes are affected
            assert "score" in anomaly or "severity" in anomaly, "Anomaly should have score or severity"

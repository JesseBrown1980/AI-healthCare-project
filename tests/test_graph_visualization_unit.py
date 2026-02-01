
import pytest
from unittest.mock import MagicMock, patch
import torch
from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder

@pytest.fixture
def graph_builder():
    """Fixture for ClinicalGraphBuilder"""
    return ClinicalGraphBuilder(feature_dim=16)

@pytest.fixture
def sample_patient_data():
    """Fixture for sample patient FHIR data"""
    return {
        "patient": {
            "id": "123",
            "gender": "male",
            "birthDate": "1980-01-01"
        },
        "medications": [
            {
                "id": "med1",
                "medicationCodeableConcept": {
                    "coding": [{"display": "Lisinopril"}]
                },
                "dosage": [{"dose": {"value": 10, "unit": "mg"}}],
                "effectivePeriod": {"start": "2023-01-01"}
            },
            {
                "id": "med2",
                "medicationCodeableConcept": {
                    "coding": [{"display": "Potassium Chloride"}]
                },
                "effectivePeriod": {"start": "2023-01-05"}
            }
        ],
        "conditions": [
            {
                "id": "cond1",
                "code": {"coding": [{"display": "Hypertension"}]},
                "severity": {"coding": [{"display": "Moderate"}]},
                "onsetDateTime": "2022-01-01"
            }
        ],
        "observations": [
            {
                "id": "obs1",
                "code": {"coding": [{"code": "potassium"}]},
                "valueQuantity": {"value": 4.5},
                "effectiveDateTime": "2023-02-01",
                "referenceRange": [{"low": {"value": 3.5}, "high": {"value": 5.0}}]
            }
        ],
        "encounters": [
            {
                "participant": [
                    {
                        "individual": {
                            "reference": "Practitioner/doc1",
                            "display": "Dr. Smith"
                        }
                    }
                ],
                "period": {"start": "2023-01-10"}
            }
        ]
    }

def test_graph_data_structure_generation(graph_builder, sample_patient_data):
    """Verify that nodes and edges are correctly generated from patient data."""
    x, edge_index, metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    # Check return types
    assert isinstance(x, torch.Tensor)
    assert isinstance(edge_index, torch.Tensor)
    assert isinstance(metadata, dict)
    
    # Check dimensions
    # Expected nodes: Patient(1) + Meds(2) + Cond(1) + Obs(1) + Provider(1) = 6
    assert x.shape[0] == 6
    assert x.shape[1] == 16  # feature_dim
    
    # Expected edges:
    # 1. Patient -> Med1 (prescribed)
    # 2. Patient -> Med2 (prescribed)
    # 3. Patient -> Cond1 (diagnosed)
    # 4. Patient -> Obs1 (measured)
    # 5. Patient -> Doc1 (visited)
    # 6. Med1 -> Med2 (interaction: lisinopril + potassium = medium)
    # 7. Cond1 -> Med1 (treatment: hypertension -> lisinopril)
    # 8. Med1 -> Obs1 (affects: ace_inhibitor -> potassium)
    # 9. Med2 -> Obs1 (affects: potassium -> potassium - implicit logic)
    # Total edges check might vary slightly based on logic, but at least 5 main connections should exist
    assert edge_index.shape[0] == 2
    assert edge_index.shape[1] >= 5

def test_node_metadata_extraction(graph_builder, sample_patient_data):
    """Verify correct metadata extraction for nodes."""
    _, _, metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    node_map = metadata['node_map']  # This is int -> str (idx -> node_id)
    # Create reverse map for easy testing (str -> int)
    reverse_node_map = {v: k for k, v in node_map.items()}
    
    node_metadata = metadata['node_metadata']
    node_types = metadata['node_types']
    
    # 1. Patient Node
    patient_node_id = "patient_123"
    assert patient_node_id in reverse_node_map
    assert node_types[patient_node_id] == 'patient'
    assert node_metadata[patient_node_id]['gender'] == 'male'
    
    # 2. Medication Node
    med_node_id = "medication_med1"
    assert med_node_id in reverse_node_map
    assert node_types[med_node_id] == 'medication'
    assert node_metadata[med_node_id]['name'] == 'Lisinopril'
    assert node_metadata[med_node_id]['dosage_value'] == 10
    
    # 3. Condition Node
    cond_node_id = "condition_cond1"
    assert cond_node_id in reverse_node_map
    assert node_types[cond_node_id] == 'condition'
    assert node_metadata[cond_node_id]['severity'] == 'moderate'

def test_edge_metadata_extraction(graph_builder, sample_patient_data):
    """Verify edge weights and types."""
    _, edge_index, metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    edge_types = metadata['edge_types']
    edge_weights = metadata['edge_weights']
    edge_metadata_list = metadata['edge_metadata']
    
    # Verify we have expected edge types
    assert 'prescribed' in edge_types
    assert 'diagnosed' in edge_types
    assert 'measured' in edge_types
    
    # Find the prescribed edge for Med1
    prescribed_indices = [i for i, t in enumerate(edge_types) if t == 'prescribed']
    assert len(prescribed_indices) >= 2
    
    # Check weight logic (should be non-zero and <= 1.0)
    for w in edge_weights:
        assert 0.0 < w <= 1.0

def test_drug_interaction_logic(graph_builder):
    """Test specifically for drug-drug interaction detection logic."""
    # Lisinopril + Potassium = Medium Interaction (Hyperkalemia risk)
    interactions = graph_builder._get_known_drug_interactions()
    severity = graph_builder._check_drug_interaction("lisinopril", "potassium_chloride", interactions)
    assert severity == "medium"
    
    # Warfarin + Aspirin = High Interaction
    severity = graph_builder._check_drug_interaction("warfarin", "aspirin", interactions)
    assert severity == "high"
    
    # Safe combo
    severity = graph_builder._check_drug_interaction("tylenol", "water", interactions)
    assert severity is None

def test_treatment_matching_logic(graph_builder):
    """Test treatment matching logic."""
    # Hypertension -> Lisinopril
    assert graph_builder._is_treatment_match("hypertension", "lisinopril") is True
    # Hypertension -> Metformin (Diabetes drug) -> False
    assert graph_builder._is_treatment_match("hypertension", "metformin") is False

def test_medication_affects_lab_logic(graph_builder):
    """Test medication-lab effect logic."""
    # ACE Inhibitor -> Potassium
    assert graph_builder._medication_affects_lab("lisinopril", "potassium") is True
    # Statin -> Liver (ALT)
    assert graph_builder._medication_affects_lab("atorvastatin", "alt") is True
    # Tylenol -> Potassium (False)
    assert graph_builder._medication_affects_lab("acetaminophen", "potassium") is False

def test_statistics_calculation(graph_builder, sample_patient_data):
    """Verify statistics can be derived from the graph metadata."""
    _, _, metadata = graph_builder.build_graph_from_patient_data(sample_patient_data)
    
    node_types = metadata['node_types']
    type_counts = {}
    for _, ntype in node_types.items():
        type_counts[ntype] = type_counts.get(ntype, 0) + 1
        
    assert type_counts['patient'] == 1
    assert type_counts['medication'] == 2
    assert type_counts['condition'] == 1

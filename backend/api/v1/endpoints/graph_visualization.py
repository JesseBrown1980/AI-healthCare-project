"""
Graph Visualization API Endpoints
Provides endpoints for visualizing patient clinical graphs from GNN anomaly detection
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from backend.security import TokenContext, auth_dependency
from backend.di import get_patient_analyzer, get_fhir_connector
from backend.patient_analyzer import PatientAnalyzer
from backend.fhir_connector import FhirResourceService
from backend.patient_data_service import PatientDataService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/patients/{patient_id}/graph")
async def get_patient_graph_visualization(
    patient_id: str,
    include_anomalies: bool = Query(True, description="Include anomaly detection results"),
    threshold: float = Query(0.5, description="Anomaly detection threshold"),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
):
    """
    Get patient clinical graph in visualization-friendly format.
    
    Returns graph structure with nodes and edges formatted for network visualization libraries.
    Includes anomaly detection results if enabled.
    """
    try:
        # Fetch patient data
        patient_data_service = PatientDataService(fhir_connector)
        patient_data = await patient_data_service.fetch_patient_data(patient_id)
        
        # Build graph using clinical graph builder
        from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
        from backend.anomaly_detector.config import settings
        
        builder = ClinicalGraphBuilder(feature_dim=settings.MODEL_INPUT_DIM)
        x, edge_index, graph_metadata = builder.build_graph_from_patient_data(patient_data)
        
        # Get anomaly detection results if requested
        anomaly_results = None
        if include_anomalies and patient_analyzer.anomaly_service:
            try:
                anomaly_results = await patient_analyzer.anomaly_service.detect_clinical_anomalies(
                    patient_data,
                    threshold=threshold
                )
            except Exception as e:
                logger.warning(f"Anomaly detection failed for graph visualization: {e}")
        
        # Build visualization-friendly graph structure
        nodes = []
        edges = []
        
        # Extract nodes
        node_map = graph_metadata.get('node_map', {})
        node_types = graph_metadata.get('node_types', {})
        node_metadata = graph_metadata.get('node_metadata', {})
        
        for node_idx, node_id in node_map.items():
            node_type = node_types.get(node_id, 'unknown')
            metadata = node_metadata.get(node_id, {})
            
            # Determine node label
            if node_type == 'patient':
                label = f"Patient\n{patient_id}"
            elif node_type == 'medication':
                label = metadata.get('name', 'Medication')
            elif node_type == 'condition':
                label = metadata.get('name', 'Condition')
            elif node_type == 'provider':
                label = metadata.get('name', 'Provider')
            elif node_type == 'lab_value':
                code = metadata.get('code', 'Lab')
                value = metadata.get('value', '')
                label = f"{code}\n{value}" if value else code
            else:
                label = node_id.split('_')[-1]
            
            # Node color based on type
            node_colors = {
                'patient': '#4A90E2',      # Blue
                'medication': '#E94B3C',    # Red
                'condition': '#F5A623',   # Orange
                'provider': '#7ED321',     # Green
                'lab_value': '#9013FE',    # Purple
            }
            
            nodes.append({
                'id': node_id,
                'label': label,
                'type': node_type,
                'metadata': metadata,
                'color': node_colors.get(node_type, '#CCCCCC'),
                'size': 20 if node_type == 'patient' else 15,
            })
        
        # Extract edges
        edge_types = graph_metadata.get('edge_types', [])
        edge_metadata_list = graph_metadata.get('edge_metadata', [])
        edge_weights = graph_metadata.get('edge_weights', [])
        
        # Create anomaly map for edge coloring
        anomaly_map = {}
        if anomaly_results:
            for anomaly in anomaly_results.get('anomalies', []):
                edge_idx = anomaly.get('edge_index')
                if edge_idx is not None:
                    anomaly_map[edge_idx] = {
                        'anomaly_type': anomaly.get('anomaly_type', 'unknown'),
                        'score': anomaly.get('anomaly_score', 0.0),
                        'severity': anomaly.get('severity', 'low'),
                    }
        
        # Edge colors based on anomaly type
        anomaly_colors = {
            'medication_anomaly': '#FF0000',      # Red
            'lab_value_anomaly': '#FF8C00',      # Dark Orange
            'clinical_pattern_anomaly': '#FFD700', # Gold
            'normal': '#CCCCCC',                  # Gray
        }
        
        for i in range(edge_index.shape[1] if edge_index.shape[1] > 0 else 0):
            src_idx = edge_index[0, i].item()
            dst_idx = edge_index[1, i].item()
            
            src_node_id = node_map.get(src_idx, f'node_{src_idx}')
            dst_node_id = node_map.get(dst_idx, f'node_{dst_idx}')
            
            edge_type = edge_types[i] if i < len(edge_types) else 'unknown'
            edge_meta = edge_metadata_list[i] if i < len(edge_metadata_list) else {}
            edge_weight = edge_weights[i] if i < len(edge_weights) else 1.0
            
            # Check if this edge is an anomaly
            anomaly_info = anomaly_map.get(i)
            if anomaly_info:
                color = anomaly_colors.get(anomaly_info['anomaly_type'], '#FF0000')
                width = 3.0 + (anomaly_info['score'] * 2.0)  # Thicker for higher scores
                is_anomaly = True
            else:
                color = '#CCCCCC'  # Gray for normal edges
                width = 1.0
                is_anomaly = False
            
            edges.append({
                'source': src_node_id,
                'target': dst_node_id,
                'type': edge_type,
                'weight': float(edge_weight),
                'metadata': edge_meta,
                'color': color,
                'width': width,
                'is_anomaly': is_anomaly,
                'anomaly_info': anomaly_info,
            })
        
        # Build response
        response = {
            'patient_id': patient_id,
            'graph': {
                'nodes': nodes,
                'edges': edges,
            },
            'statistics': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'node_types': {
                    node_type: sum(1 for n in nodes if n['type'] == node_type)
                    for node_type in set(n['type'] for n in nodes)
                },
                'edge_types': {
                    edge_type: sum(1 for e in edges if e['type'] == edge_type)
                    for edge_type in set(e['type'] for e in edges)
                },
            },
        }
        
        if anomaly_results:
            response['anomaly_detection'] = {
                'anomaly_count': anomaly_results.get('anomaly_count', 0),
                'anomaly_type_counts': anomaly_results.get('anomaly_type_counts', {}),
                'threshold': threshold,
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate graph visualization: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate graph visualization: {str(e)}"
        )


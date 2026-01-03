"""
Graph Visualization API Endpoints
Provides endpoints for visualizing patient clinical graphs from GNN anomaly detection
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import logging

from backend.security import TokenContext, auth_dependency
from backend.di import get_patient_analyzer, get_fhir_connector, get_database_service, get_audit_service
from backend.patient_analyzer import PatientAnalyzer
from backend.fhir_connector import FhirResourceService
from backend.patient_data_service import PatientDataService
from backend.database.service import DatabaseService
from backend.audit_service import AuditService
from backend.utils.validation import validate_patient_id, validate_patient_id_list
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler

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
    # Validate patient_id
    patient_id = validate_patient_id(patient_id)
    
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
                log_structured(
                    level="warning",
                    message="Anomaly detection failed for graph visualization (continuing without anomalies)",
                    correlation_id=correlation_id,
                    request=request,
                    patient_id=patient_id,
                    error=str(e)
                )
        
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
        
        log_structured(
            level="info",
            message="Patient graph visualization generated successfully",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id,
            node_count=len(nodes),
            edge_count=len(edges),
            has_anomalies=bool(anomaly_results)
        )
        
        return response
        
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_patient_graph_visualization", "patient_id": patient_id},
            correlation_id,
            request
        )


@router.get("/patients/{patient_id}/anomaly-timeline")
async def get_anomaly_timeline(
    request: Request,
    patient_id: str,
    days: int = Query(30, description="Number of days to look back"),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Get anomaly timeline data for a patient showing anomalies over time.
    
    Extracts anomaly detection results from analysis history to show trends.
    """
    correlation_id = get_correlation_id(request)
    
    # Validate patient_id
    try:
        patient_id = validate_patient_id(patient_id)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    # Validate days parameter
    if days < 1 or days > 365:
        raise create_http_exception(
            message="Days parameter must be between 1 and 365",
            status_code=400,
            error_type="ValidationError"
        )
    
    if not db_service:
        raise create_http_exception(
            message="Database service required for anomaly timeline",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    try:
        log_structured(
            level="info",
            message="Generating anomaly timeline",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id,
            days=days
        )
        # Get analysis history for the patient
        history = await db_service.get_analysis_history(patient_id, limit=1000)
        
        # Filter to requested time range
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        timeline_data = []
        
        for analysis in history:
            try:
                timestamp_str = analysis['analysis_timestamp'].replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(timestamp_str)
                # Ensure timestamp is timezone-aware
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                if timestamp < cutoff_date:
                    continue
                
                # Extract anomaly data from analysis_data
                analysis_data = analysis.get('analysis_data') or {}
                gnn_anomaly = analysis_data.get('gnn_anomaly_detection', {})
                
                if gnn_anomaly and gnn_anomaly.get('anomalies'):
                    anomalies = gnn_anomaly.get('anomalies', [])
                    anomaly_type_counts = gnn_anomaly.get('anomaly_type_counts', {})
                    
                    timeline_data.append({
                        'timestamp': timestamp.isoformat(),
                        'anomaly_count': len(anomalies),
                        'anomaly_type_counts': anomaly_type_counts,
                        'anomalies': [
                            {
                                'type': a.get('anomaly_type', 'unknown'),
                                'score': a.get('anomaly_score', 0.0),
                                'severity': a.get('severity', 'low'),
                            }
                            for a in anomalies
                        ],
                    })
            except Exception as e:
                log_structured(
                    level="warning",
                    message="Failed to parse analysis entry (skipping)",
                    correlation_id=correlation_id,
                    request=request,
                    error=str(e)
                )
                continue
        
        # Sort by timestamp
        timeline_data.sort(key=lambda x: x['timestamp'])
        
        log_structured(
            level="info",
            message="Anomaly timeline generated successfully",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id,
            timeline_points=len(timeline_data)
        )
        
        return {
            'patient_id': patient_id,
            'days': days,
            'timeline': timeline_data,
            'total_points': len(timeline_data),
        }
        
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_anomaly_timeline", "patient_id": patient_id, "days": days},
            correlation_id,
            request
        )


@router.post("/patients/compare-graphs")
async def compare_patient_graphs(
    request: Request,
    patient_ids: List[str] = Query(..., description="List of patient IDs to compare"),
    include_anomalies: bool = Query(True, description="Include anomaly detection"),
    threshold: float = Query(0.5, description="Anomaly detection threshold"),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Compare clinical graphs across multiple patients.
    
    Returns graph statistics and anomaly comparisons for the provided patient IDs.
    """
    correlation_id = get_correlation_id(request)
    
    # Validate patient_ids
    try:
        patient_ids = validate_patient_id_list(patient_ids, max_count=5)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    if len(patient_ids) < 2:
        raise create_http_exception(
            message="At least 2 patient IDs required for comparison",
            status_code=400,
            error_type="ValidationError"
        )
    
    if len(patient_ids) > 5:
        raise create_http_exception(
            message="Maximum 5 patients can be compared at once",
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Comparing patient graphs",
            correlation_id=correlation_id,
            request=request,
            patient_count=len(patient_ids),
            include_anomalies=include_anomalies
        )
        comparison_results = []
        patient_data_service = PatientDataService(fhir_connector)
        
        from backend.anomaly_detector.models.clinical_graph_builder import ClinicalGraphBuilder
        from backend.anomaly_detector.config import settings
        
        for patient_id in patient_ids:
            try:
                # Fetch patient data
                patient_data = await patient_data_service.fetch_patient_data(patient_id)
                
                # Build graph
                builder = ClinicalGraphBuilder(feature_dim=settings.MODEL_INPUT_DIM)
                x, edge_index, graph_metadata = builder.build_graph_from_patient_data(patient_data)
                
                # Get anomaly detection if requested
                anomaly_results = None
                if include_anomalies and patient_analyzer.anomaly_service:
                    try:
                        anomaly_results = await patient_analyzer.anomaly_service.detect_clinical_anomalies(
                            patient_data,
                            threshold=threshold
                        )
                    except Exception as e:
                        logger.warning(f"Anomaly detection failed for {patient_id}: {e}")
                
                # Extract statistics
                node_map = graph_metadata.get('node_map', {})
                node_types = graph_metadata.get('node_types', {})
                edge_types = graph_metadata.get('edge_types', [])
                
                node_type_counts = {}
                for node_id, node_type in node_types.items():
                    node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
                
                edge_type_counts = {}
                for edge_type in edge_types:
                    edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
                
                comparison_results.append({
                    'patient_id': patient_id,
                    'statistics': {
                        'total_nodes': len(node_map),
                        'total_edges': len(edge_types),
                        'node_types': node_type_counts,
                        'edge_types': edge_type_counts,
                    },
                    'anomaly_detection': {
                        'anomaly_count': anomaly_results.get('anomaly_count', 0) if anomaly_results else 0,
                        'anomaly_type_counts': anomaly_results.get('anomaly_type_counts', {}) if anomaly_results else {},
                    } if anomaly_results else None,
                })
                
            except Exception as e:
                log_structured(
                    level="error",
                    message="Failed to process patient for graph comparison",
                    correlation_id=correlation_id,
                    request=request,
                    patient_id=patient_id,
                    error=str(e)
                )
                comparison_results.append({
                    'patient_id': patient_id,
                    'error': str(e),
                })
        
        # Calculate comparison metrics
        all_node_types = set()
        all_edge_types = set()
        for result in comparison_results:
            if 'statistics' in result:
                all_node_types.update(result['statistics'].get('node_types', {}).keys())
                all_edge_types.update(result['statistics'].get('edge_types', {}).keys())
        
        comparison_metrics = {
            'node_type_distribution': {
                node_type: [
                    r['statistics'].get('node_types', {}).get(node_type, 0)
                    for r in comparison_results
                    if 'statistics' in r
                ]
                for node_type in all_node_types
            },
            'edge_type_distribution': {
                edge_type: [
                    r['statistics'].get('edge_types', {}).get(edge_type, 0)
                    for r in comparison_results
                    if 'statistics' in r
                ]
                for edge_type in all_edge_types
            },
            'anomaly_comparison': {
                'total_anomalies': [
                    r.get('anomaly_detection', {}).get('anomaly_count', 0) if r.get('anomaly_detection') else 0
                    for r in comparison_results
                ],
                'anomaly_types': {}
            }
        }
        
        # Aggregate anomaly types
        all_anomaly_types = set()
        for result in comparison_results:
            if result.get('anomaly_detection'):
                all_anomaly_types.update(result['anomaly_detection'].get('anomaly_type_counts', {}).keys())
        
        for anomaly_type in all_anomaly_types:
            comparison_metrics['anomaly_comparison']['anomaly_types'][anomaly_type] = [
                r.get('anomaly_detection', {}).get('anomaly_type_counts', {}).get(anomaly_type, 0)
                if r.get('anomaly_detection') else 0
                for r in comparison_results
            ]
        
        log_structured(
            level="info",
            message="Patient graph comparison completed successfully",
            correlation_id=correlation_id,
            request=request,
            patient_count=len(patient_ids),
            successful_comparisons=len([r for r in comparison_results if 'statistics' in r])
        )
        
        return {
            'patient_ids': patient_ids,
            'comparison_results': comparison_results,
            'comparison_metrics': comparison_metrics,
        }
        
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "compare_patient_graphs", "patient_count": len(patient_ids)},
            correlation_id,
            request
        )


"""
Anomaly Detection Service - Model Orchestration

This service manages the GNN model lifecycle with support for multiple architectures:
- baseline: EdgeLevelGCN (91.87% accuracy)
- prototype: PrototypeGNN (94.24% accuracy)
- contrastive: ContrastiveGNN (94.71% accuracy)
- gsl: GSLGNN (96.66% accuracy) - RECOMMENDED

Also supports clinical anomaly detection using patient data graphs.
"""

import os
import torch
import logging
from typing import Dict, Any, Tuple, Optional
from .config import settings
from .exceptions import ModelInitializationError, ConfigurationError


def load_model(model_type: str = None):
    """
    Factory function to load the appropriate model based on configuration.
    
    Args:
        model_type: Override for settings.MODEL_TYPE
        
    Returns:
        Initialized model instance
    """
    model_type = model_type or settings.MODEL_TYPE
    
    if model_type == "baseline":
        from .models.gnn_baseline import EdgeLevelGNN
        return EdgeLevelGNN(
            node_input_dim=settings.MODEL_INPUT_DIM,
            hidden_dim=settings.MODEL_HIDDEN_DIM,
            output_dim=settings.MODEL_OUTPUT_DIM
        )
    
    elif model_type == "prototype":
        from .models.prototype_gnn import PrototypeGNN
        return PrototypeGNN(
            node_input_dim=settings.MODEL_INPUT_DIM,
            hidden_dim=settings.MODEL_HIDDEN_DIM,
            num_classes=2,
            num_prototypes_per_class=settings.NUM_PROTOTYPES_PER_CLASS,
            temperature=settings.PROTOTYPE_TEMPERATURE
        )
    
    elif model_type == "contrastive":
        from .models.contrastive_gnn import ContrastiveGNN
        return ContrastiveGNN(
            node_input_dim=settings.MODEL_INPUT_DIM,
            hidden_dim=settings.MODEL_HIDDEN_DIM,
            projection_dim=settings.PROJECTION_DIM,
            num_classes=2
        )
    
    elif model_type == "gsl":
        from .models.gsl_gnn import GSLGNN
        return GSLGNN(
            node_input_dim=settings.MODEL_INPUT_DIM,
            hidden_dim=settings.MODEL_HIDDEN_DIM,
            num_classes=2,
            gsl_hidden_dim=settings.GSL_HIDDEN_DIM
        )
    
    else:
        settings.logger.error(f"Unsupported model type requested: {model_type}")
        raise ConfigurationError(
            message=f"Unknown model type: {model_type}",
            detail=f"Valid options are: baseline, prototype, contrastive, gsl"
        )


class AnomalyService:
    """
    Singleton service to manage the Anomaly Detector lifecycle.
    Supports dynamic model selection via MODEL_TYPE environment variable.
    """
    
    def __init__(self):
        self.model = None
        self.model_type = None
        self.is_initialized = False

    def initialize(self, model_type: str = None):
        """
        Loads the model architecture and weights (if available).
        
        Args:
            model_type: Override for default model type from config
        """
        if self.is_initialized:
            return

        self.model_type = model_type or settings.MODEL_TYPE
        settings.logger.info(f"Initializing {self.model_type.upper()} model...")
        
        try:
            self.model = load_model(self.model_type)
            
            # In production, load pre-trained weights here
            # weights_path = f"weights/{self.model_type}_model.pt"
            # if os.path.exists(weights_path):
            #     self.model.load_state_dict(torch.load(weights_path))
            
            self.model.eval()
            self.is_initialized = True
            settings.logger.info(f"{self.model_type.upper()} model initialized successfully.")
        except Exception as e:
            settings.logger.error(f"Failed to initialize {self.model_type}: {e}")
            raise ModelInitializationError(
                message=f"Model {self.model_type} initialization failed",
                detail=str(e)
            )

    def get_model(self):
        if not self.is_initialized:
            self.initialize()
        return self.model
    
    def get_model_info(self) -> dict:
        """Return information about the current model."""
        accuracy_map = {
            "baseline": 91.87,
            "prototype": 94.24,
            "contrastive": 94.71,
            "gsl": 96.66
        }
        return {
            "model_type": self.model_type,
            "expected_accuracy": accuracy_map.get(self.model_type, "unknown"),
            "is_initialized": self.is_initialized
        }
    
    async def detect_clinical_anomalies(
        self,
        patient_data: Dict[str, Any],
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Detect clinical anomalies in patient data using GNN.
        
        Args:
            patient_data: Patient FHIR data dictionary
            threshold: Anomaly score threshold (0-1)
        
        Returns:
            Dictionary with anomaly detection results:
            - anomalies: List of detected anomalies
            - scores: Edge-level anomaly scores
            - graph_metadata: Graph structure metadata
        """
        if not self.is_initialized:
            self.initialize()
        
        try:
            from .models.clinical_graph_builder import ClinicalGraphBuilder
            
            # Build clinical graph from patient data
            builder = ClinicalGraphBuilder(feature_dim=settings.MODEL_INPUT_DIM)
            x, edge_index, graph_metadata = builder.build_graph_from_patient_data(patient_data)
            
            if edge_index.shape[1] == 0:
                # Empty graph - no relationships to analyze
                return {
                    'anomalies': [],
                    'scores': [],
                    'graph_metadata': graph_metadata,
                    'anomaly_count': 0,
                    'message': 'No clinical relationships found to analyze'
                }
            
            # Run inference with explainability
            self.model.eval()
            with torch.no_grad():
                # Check if model supports explainability (GSL model)
                if self.model_type == "gsl" and hasattr(self.model, 'forward'):
                    # GSL model can return learned adjacency weights
                    try:
                        scores, learned_adj = self.model(x, edge_index, return_weights=True)
                        # Get edge importance using model's built-in method
                        if hasattr(self.model, 'get_edge_importance'):
                            edge_importance = self.model.get_edge_importance(learned_adj, edge_index)
                        else:
                            edge_importance = self._get_edge_importance(learned_adj, edge_index)
                    except Exception:
                        # Fallback if return_weights not supported
                        scores = self.model(x, edge_index)
                        edge_importance = None
                else:
                    scores = self.model(x, edge_index)
                    edge_importance = None
                
                # Convert to list for JSON serialization
                scores_list = scores.cpu().tolist() if isinstance(scores, torch.Tensor) else scores
                if edge_importance is not None:
                    importance_list = edge_importance.cpu().tolist()
                else:
                    importance_list = [None] * len(scores_list)
            
            # Identify anomalies (edges with score > threshold)
            anomalies = []
            edge_types = graph_metadata.get('edge_types', [])
            edge_metadata_list = graph_metadata.get('edge_metadata', [])
            node_map = graph_metadata.get('node_map', {})
            node_types = graph_metadata.get('node_types', {})
            node_metadata = graph_metadata.get('node_metadata', {})
            
            for i, score in enumerate(scores_list):
                if score > threshold:
                    edge_type = edge_types[i] if i < len(edge_types) else 'unknown'
                    edge_meta = edge_metadata_list[i] if i < len(edge_metadata_list) else {}
                    
                    # Get explainability information
                    explanation = self._explain_anomaly(
                        i, edge_type, edge_meta, score, 
                        node_map, node_types, node_metadata,
                        edge_index, importance_list[i] if i < len(importance_list) else None
                    )
                    
                    anomalies.append({
                        'edge_index': i,
                        'edge_type': edge_type,
                        'anomaly_score': float(score),
                        'metadata': edge_meta,
                        'severity': 'high' if score > 0.8 else 'medium' if score > 0.6 else 'low',
                        'explanation': explanation,
                        'importance': float(importance_list[i]) if importance_list[i] is not None else None
                    })
            
            # Sort by score (highest first)
            anomalies.sort(key=lambda x: x['anomaly_score'], reverse=True)
            
            return {
                'anomalies': anomalies,
                'scores': scores_list,
                'graph_metadata': graph_metadata,
                'anomaly_count': len(anomalies),
                'threshold': threshold,
                'total_edges': len(scores_list)
            }
            
        except Exception as e:
            settings.logger.error(f"Clinical anomaly detection failed: {e}", exc_info=True)
            return {
                'anomalies': [],
                'scores': [],
                'graph_metadata': {},
                'anomaly_count': 0,
                'error': str(e),
                'message': 'Anomaly detection failed'
            }
    
    def _get_edge_importance(self, learned_adj: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Calculate edge importance from learned adjacency matrix.
        Higher values indicate edges that the model learned are more important.
        """
        num_edges = edge_index.shape[1]
        importance = torch.zeros(num_edges, device=learned_adj.device)
        
        for i in range(num_edges):
            src = edge_index[0, i].item()
            dst = edge_index[1, i].item()
            # Importance is the learned adjacency weight
            importance[i] = learned_adj[src, dst]
        
        return importance
    
    def _explain_anomaly(
        self,
        edge_idx: int,
        edge_type: str,
        edge_meta: Dict[str, Any],
        score: float,
        node_map: Dict[int, str],
        node_types: Dict[str, str],
        node_metadata: Dict[str, Dict[str, Any]],
        edge_index: torch.Tensor,
        importance: Optional[float]
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation for why an anomaly was flagged.
        """
        explanation = {
            'reason': '',
            'contributing_factors': [],
            'clinical_context': '',
            'recommendation': ''
        }
        
        # Get source and target nodes
        if edge_index.shape[1] > edge_idx:
            src_idx = edge_index[0, edge_idx].item()
            dst_idx = edge_index[1, edge_idx].item()
            src_node_id = node_map.get(src_idx, 'unknown')
            dst_node_id = node_map.get(dst_idx, 'unknown')
            src_type = node_types.get(src_node_id, 'unknown')
            dst_type = node_types.get(dst_node_id, 'unknown')
        else:
            src_node_id = dst_node_id = 'unknown'
            src_type = dst_type = 'unknown'
        
        # Generate explanation based on edge type
        if edge_type == 'interacts_with':
            med1_meta = node_metadata.get(src_node_id, {})
            med2_meta = node_metadata.get(dst_node_id, {})
            med1_name = med1_meta.get('name', 'medication 1')
            med2_name = med2_meta.get('name', 'medication 2')
            
            if edge_meta.get('known_interaction'):
                explanation['reason'] = f"Known drug interaction between {med1_name} and {med2_name}"
                explanation['contributing_factors'].append({
                    'factor': 'Known interaction',
                    'severity': edge_meta.get('interaction_severity', 'unknown'),
                    'weight': 0.9
                })
                explanation['clinical_context'] = (
                    f"These medications have a documented interaction with "
                    f"{edge_meta.get('interaction_severity', 'unknown')} severity. "
                    f"Concurrent use may require dose adjustment or monitoring."
                )
                explanation['recommendation'] = (
                    "Review medication list and consider: "
                    "1) Alternative medications, 2) Dose adjustment, "
                    "3) Enhanced monitoring for adverse effects"
                )
            else:
                explanation['reason'] = f"Potential polypharmacy: {med1_name} + {med2_name}"
                explanation['contributing_factors'].append({
                    'factor': 'Polypharmacy',
                    'medication_count': 2,
                    'weight': 0.5
                })
                explanation['clinical_context'] = (
                    "Multiple medications increase risk of interactions, "
                    "adverse effects, and medication errors."
                )
                explanation['recommendation'] = (
                    "Review all medications for potential interactions. "
                    "Consider medication reconciliation and deprescribing if appropriate."
                )
        
        elif edge_type == 'prescribed':
            med_meta = node_metadata.get(dst_node_id, {})
            med_name = med_meta.get('name', 'medication')
            is_high_risk = med_meta.get('name', '').lower() in [
                'warfarin', 'digoxin', 'lithium', 'methotrexate'
            ]
            
            explanation['reason'] = f"Unusual medication pattern: {med_name}"
            if is_high_risk:
                explanation['contributing_factors'].append({
                    'factor': 'High-risk medication',
                    'medication': med_name,
                    'weight': 0.7
                })
                explanation['clinical_context'] = (
                    f"{med_name} is a high-risk medication requiring careful monitoring. "
                    "Unusual patterns may indicate dosing issues or contraindications."
                )
            else:
                explanation['contributing_factors'].append({
                    'factor': 'Medication pattern',
                    'weight': 0.5
                })
                explanation['clinical_context'] = (
                    "The pattern of this medication prescription appears unusual "
                    "compared to typical clinical patterns."
                )
            explanation['recommendation'] = "Review medication indication, dosing, and monitoring requirements."
        
        elif edge_type == 'diagnosed':
            cond_meta = node_metadata.get(dst_node_id, {})
            cond_name = cond_meta.get('name', 'condition')
            severity = cond_meta.get('severity', '')
            
            explanation['reason'] = f"Unusual condition pattern: {cond_name}"
            if severity in ['severe', 'critical']:
                explanation['contributing_factors'].append({
                    'factor': 'High-severity condition',
                    'severity': severity,
                    'weight': 0.8
                })
                explanation['clinical_context'] = (
                    f"{cond_name} is a {severity} condition that may require "
                    "immediate attention or specialized care."
                )
            else:
                explanation['contributing_factors'].append({
                    'factor': 'Condition pattern',
                    'weight': 0.5
                })
                explanation['clinical_context'] = (
                    "The pattern of this condition diagnosis appears unusual."
                )
            explanation['recommendation'] = "Review condition status, treatment plan, and follow-up requirements."
        
        elif edge_type == 'measured':
            lab_meta = node_metadata.get(dst_node_id, {})
            lab_code = lab_meta.get('code', 'lab value')
            is_abnormal = lab_meta.get('abnormal', False)
            
            explanation['reason'] = f"Unusual lab value pattern: {lab_code}"
            if is_abnormal:
                explanation['contributing_factors'].append({
                    'factor': 'Abnormal lab value',
                    'lab_code': lab_code,
                    'weight': 0.8
                })
                explanation['clinical_context'] = (
                    f"Lab value {lab_code} is outside the normal reference range. "
                    "This may indicate a clinical issue requiring attention."
                )
            else:
                explanation['contributing_factors'].append({
                    'factor': 'Lab value pattern',
                    'weight': 0.5
                })
                explanation['clinical_context'] = (
                    "The pattern of this lab value measurement appears unusual."
                )
            explanation['recommendation'] = (
                "Review lab value in clinical context. "
                "Consider repeat testing or clinical correlation if abnormal."
            )
        
        elif edge_type == 'affects':
            med_meta = node_metadata.get(src_node_id, {})
            lab_meta = node_metadata.get(dst_node_id, {})
            med_name = med_meta.get('name', 'medication')
            lab_code = lab_meta.get('code', 'lab value')
            
            explanation['reason'] = f"Medication {med_name} affecting {lab_code}"
            explanation['contributing_factors'].append({
                'factor': 'Medication-lab interaction',
                'medication': med_name,
                'lab_value': lab_code,
                'weight': 0.6
            })
            explanation['clinical_context'] = (
                f"{med_name} is known to affect {lab_code} values. "
                "This relationship may explain abnormal lab results."
            )
            explanation['recommendation'] = (
                "Monitor lab values while on this medication. "
                "Consider dose adjustment if lab values are significantly affected."
            )
        
        else:
            explanation['reason'] = f"Unusual {edge_type} relationship detected"
            explanation['contributing_factors'].append({
                'factor': 'Graph pattern',
                'edge_type': edge_type,
                'weight': 0.5
            })
            explanation['clinical_context'] = (
                f"The {edge_type} relationship shows an unusual pattern "
                "compared to typical clinical data."
            )
            explanation['recommendation'] = "Review this relationship in clinical context."
        
        # Add model confidence information
        if importance is not None:
            explanation['model_confidence'] = {
                'importance_score': float(importance),
                'interpretation': 'high' if importance > 0.7 else 'medium' if importance > 0.4 else 'low'
            }
        
        explanation['anomaly_score'] = float(score)
        explanation['confidence_level'] = 'high' if score > 0.8 else 'medium' if score > 0.6 else 'low'
        
        return explanation

# Singleton instance
anomaly_service = AnomalyService()

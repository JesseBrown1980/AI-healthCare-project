"""
Anomaly Detection Service - Model Orchestration

This service manages the GNN model lifecycle with support for multiple architectures:
- baseline: EdgeLevelGCN (91.87% accuracy)
- prototype: PrototypeGNN (94.24% accuracy)
- contrastive: ContrastiveGNN (94.71% accuracy)
- gsl: GSLGNN (96.66% accuracy) - RECOMMENDED
"""

import os
import torch
from .config import settings


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
        raise ValueError(f"Unknown model type: {model_type}. "
                        f"Valid options: baseline, prototype, contrastive, gsl")


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
        print(f"[{settings.PROJECT_NAME}] Initializing {self.model_type.upper()} model...")
        
        self.model = load_model(self.model_type)
        
        # In production, load pre-trained weights here:
        # weights_path = f"weights/{self.model_type}_model.pt"
        # if os.path.exists(weights_path):
        #     self.model.load_state_dict(torch.load(weights_path))
        
        self.model.eval()
        self.is_initialized = True
        print(f"[{settings.PROJECT_NAME}] {self.model_type.upper()} model initialized successfully.")

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

# Singleton instance
anomaly_service = AnomalyService()

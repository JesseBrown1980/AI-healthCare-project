
import os
import torch
from .config import settings
from .models.gnn_baseline import EdgeLevelGNN

class AnomalyService:
    """
    Singleton service to manage the Anomaly Detector lifecycle.
    """
    def __init__(self):
        self.model = None
        self.is_initialized = False

    def initialize(self):
        """
        Loads the model architecture and weights (if available).
        For now, initializes a fresh model for online learning/inference.
        """
        if self.is_initialized:
            return

        print(f"[{settings.PROJECT_NAME}] Initializing GNN Model...")
        self.model = EdgeLevelGNN(
            node_input_dim=settings.MODEL_INPUT_DIM,
            hidden_dim=settings.MODEL_HIDDEN_DIM,
            output_dim=settings.MODEL_OUTPUT_DIM
        )
        
        # In a real scenario, we would load state_dict here
        # self.model.load_state_dict(torch.load("path/to/weights.pt"))
        
        self.model.eval()
        self.is_initialized = True
        print(f"[{settings.PROJECT_NAME}] Model initialized successfully.")

    def get_model(self):
        if not self.is_initialized:
            self.initialize()
        return self.model

# Singleton instance
anomaly_service = AnomalyService()

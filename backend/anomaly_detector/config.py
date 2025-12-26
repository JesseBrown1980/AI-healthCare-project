import os
from typing import Literal

class Settings:
    PROJECT_NAME: str = "Anomaly Detection Service"
    VERSION: str = "2.0.0"  # Updated for advanced models
    API_V1_STR: str = "/security/anomaly"
    
    # Model Selection: "baseline" | "prototype" | "contrastive" | "gsl"
    # - baseline: EdgeLevelGCN (91.87% accuracy)
    # - prototype: PrototypeGNN (94.24% accuracy)
    # - contrastive: ContrastiveGNN (94.71% accuracy)
    # - gsl: GSLGNN (96.66% accuracy) - RECOMMENDED
    MODEL_TYPE: str = os.getenv("MODEL_TYPE", "gsl")
    
    # Model Configuration
    MODEL_INPUT_DIM: int = 16  # Dimension of node features
    MODEL_HIDDEN_DIM: int = 32
    MODEL_OUTPUT_DIM: int = 1  # Binary classification (0: benign, 1: suspicious)
    
    # Prototype-GNN specific
    NUM_PROTOTYPES_PER_CLASS: int = 3
    PROTOTYPE_TEMPERATURE: float = 0.1
    
    # Contrastive-GNN specific
    PROJECTION_DIM: int = 64
    CONTRASTIVE_TEMPERATURE: float = 0.07
    
    # GSL-GNN specific
    GSL_HIDDEN_DIM: int = 32
    
    # Thresholds
    ANOMALY_THRESHOLD: float = 0.8
    
    # Health Check
    IS_INITIALIZED: bool = False

settings = Settings()


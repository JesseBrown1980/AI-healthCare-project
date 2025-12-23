import os

class Settings:
    PROJECT_NAME: str = "Anomaly Detection Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/security/anomaly"
    
    # Model Configuration
    MODEL_INPUT_DIM: int = 16  # Dimension of node features
    MODEL_HIDDEN_DIM: int = 32
    MODEL_OUTPUT_DIM: int = 1  # Binary classification (0: benign, 1: suspicious)
    
    # Thresholds
    ANOMALY_THRESHOLD: float = 0.8
    
    # Health Check
    IS_INITIALIZED: bool = False

settings = Settings()

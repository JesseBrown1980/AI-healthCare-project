import os
import logging
from typing import Literal

# Configure baseline logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class Settings:
    PROJECT_NAME: str = "Anomaly Detection Service"
    PROJECT_ID: str = "anomaly-detector"
    VERSION: str = "2.1.0"  # Enterprise Sweep Version
    API_V1_STR: str = "/security/anomaly"
    
    # Model Selection: "baseline" | "prototype" | "contrastive" | "gsl"
    MODEL_TYPE: str = os.getenv("MODEL_TYPE", "gsl")
    
    # Model Configuration
    MODEL_INPUT_DIM: int = 16  # Dimension of node features
    MODEL_HIDDEN_DIM: int = 32
    MODEL_OUTPUT_DIM: int = 1  # Binary classification
    
    # Advanced Model Configs
    NUM_PROTOTYPES_PER_CLASS: int = 3
    PROTOTYPE_TEMPERATURE: float = 0.1
    PROJECTION_DIM: int = 64
    CONTRASTIVE_TEMPERATURE: float = 0.07
    GSL_HIDDEN_DIM: int = 32
    
    # Infrastructure
    ANOMALY_THRESHOLD: float = os.getenv("ANOMALY_THRESHOLD", 0.8)
    
    @property
    def logger(self):
        return logging.getLogger(self.PROJECT_ID)

settings = Settings()


"""
Custom Domain Exceptions for the Anomaly Detection Service.
"""

class AnomalyDetectionError(Exception):
    """Base exception for all anomaly detection service errors."""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

class ModelInitializationError(AnomalyDetectionError):
    """Raised when the GNN model fails to load or initialize."""
    pass

class GraphBuildingError(AnomalyDetectionError):
    """Raised when converting log events to graph data fails."""
    pass

class ModelInferenceError(AnomalyDetectionError):
    """Raised when the forward pass on the model fails."""
    pass

class ConfigurationError(AnomalyDetectionError):
    """Raised when service configuration is missing or invalid."""
    pass

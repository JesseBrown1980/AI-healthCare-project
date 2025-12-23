from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class LogEvent(BaseModel):
    """
    Represents a single raw audit log or network event.
    """
    event_id: str
    timestamp: datetime
    source_entity: str  # e.g., User ID, IP
    destination_entity: str  # e.g., Patient ID, Resource
    action: str  # e.g., "READ", "WRITE", "LOGIN"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class EventBatch(BaseModel):
    """
    A batch of events to be processed.
    """
    events: List[LogEvent]

class ScoredEvent(BaseModel):
    """
    The result of the anomaly detection for a specific event/edge.
    """
    event_id: str
    anomaly_score: float  # 0.0 to 1.0
    is_anomaly: bool
    explanation: Optional[str] = None

class ScoreResponse(BaseModel):
    """
    Response containing scores for the submitted batch.
    """
    results: List[ScoredEvent]
    processed_at: datetime

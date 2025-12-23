from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import torch

from .models.schemas import EventBatch, ScoreResponse, ScoredEvent
from .models.graph_builder import GraphBuilder
from .config import settings

router = APIRouter()

@router.post("/score", response_model=ScoreResponse)
async def score_events(batch: EventBatch, request: Request):
    """
    Ingests a batch of log events, constructs a temporary graph,
    and returns anomaly scores for each event (edge).
    """
    model = getattr(request.app.state, "model", None)
    if not model:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    # 1. Build Graph from Events
    builder = GraphBuilder(feature_dim=settings.MODEL_INPUT_DIM)
    x, edge_index, event_ids = builder.build_graph(batch.events)
    
    # 2. Run Inference
    # We need to act as if we are in eval mode
    model.eval()
    with torch.no_grad():
        try:
            scores = model(x, edge_index)
            # If only 1 edge, scores might be 0-d tensor
            if scores.ndim == 0:
                scores = scores.unsqueeze(0)
            scores_list = scores.tolist()
        except Exception as e:
            # Fallback or error handling
            print(f"Inference error: {e}")
            # Return 0.0 scores or error
            scores_list = [0.0] * len(batch.events)

    # 3. Format Response
    results = []
    for i, event_id in enumerate(event_ids):
        score = scores_list[i] if i < len(scores_list) else 0.0
        is_anomaly = score > settings.ANOMALY_THRESHOLD
        
        results.append(ScoredEvent(
            event_id=event_id,
            anomaly_score=score,
            is_anomaly=is_anomaly,
            explanation="Baseline GCN score"
        ))
        
    return ScoreResponse(
        results=results,
        processed_at=datetime.utcnow()
    )

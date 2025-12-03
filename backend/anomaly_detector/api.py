from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
import torch

from .models.schemas import EventBatch, ScoreResponse, ScoredEvent
from .models.graph_builder import GraphBuilder
from .config import settings
from .service import anomaly_service
from .exceptions import ModelInferenceError, GraphBuildingError

router = APIRouter()

@router.post("/score", response_model=ScoreResponse)
async def score_events(batch: EventBatch, request: Request):
    """
    Ingests a batch of log events, constructs a temporary graph,
    and returns anomaly scores for each event (edge).
    """
    model = getattr(request.app.state, "model", None)
    if not model:
        settings.logger.error("Attempted inference before model initialization")
        raise HTTPException(
            status_code=503, 
            detail="Model not initialized. Service may still be starting up."
        )
    
    # 1. Build Graph from Events
    try:
        builder = GraphBuilder(feature_dim=settings.MODEL_INPUT_DIM)
        x, edge_index, event_ids = builder.build_graph(batch.events)
    except Exception as e:
        settings.logger.error(f"Graph construction failed: {e}")
        raise GraphBuildingError(message="Failed to build graph from events", detail=str(e))
    
    # 2. Run Inference
    model.eval()
    with torch.no_grad():
        try:
            # Check if model supports explainability (currently only GSL)
            model_info = anomaly_service.get_model_info()
            model_type = model_info.get("model_type", "unknown")
            
            importance_list = [None] * len(batch.events)
            
            if model_type == "gsl":
                scores, learned_adj = model(x, edge_index, return_weights=True)
                importance = model.get_edge_importance(learned_adj, edge_index)
                importance_list = importance.tolist()
            else:
                scores = model(x, edge_index)
                
            if scores.ndim == 0:
                scores = scores.unsqueeze(0)
            scores_list = scores.tolist()
        except Exception as e:
            settings.logger.error("Inference engine error: %s", e)
            raise ModelInferenceError(message="Anomaly detection inference failed", detail=str(e))

    # 3. Format Response
    results = []
    model_name = model_type.upper()
    
    for i, event_id in enumerate(event_ids):
        score = scores_list[i] if i < len(scores_list) else 0.0
        is_anomaly = score > settings.ANOMALY_THRESHOLD
        importance = importance_list[i] if i < len(importance_list) else None
        
        # Build technical explanation
        explanation = f"{model_name} GNN score: {score:.4f}"
        if importance is not None:
            explanation += f" | Connection strength: {importance:.4f}"
            if importance < 0.3:
                explanation += " (Weak structural support)"
            elif importance > 0.7:
                explanation += " (Strong structural support)"
        
        results.append(ScoredEvent(
            event_id=event_id,
            anomaly_score=score,
            is_anomaly=is_anomaly,
            importance_score=importance,
            explanation=explanation,
            contributing_factors={
                "structural_importance": importance if importance is not None else 0.0,
                "model_confidence": 1.0 - abs(score - 0.5) * 2
            }
        ))
        
    return ScoreResponse(
        results=results,
        processed_at=datetime.now(timezone.utc)
    )

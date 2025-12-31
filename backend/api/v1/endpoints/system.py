from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
from backend.models import (
    HealthCheckResponse,
    CacheClearResponse,
    DeviceRegistration,
    DeviceRegistrationResponse,
    StatsResponse,
)
from backend.security import TokenContext, auth_dependency
from backend.di import (
    get_optional_llm_engine,
    get_optional_rag_fusion,
    get_optional_s_lora_manager,
    get_optional_mlc_learning,
    get_audit_service,
    get_analysis_job_manager,
    get_patient_analyzer,
    get_patient_summary_cache,
    get_notifier,
)
from backend.notifier import Notifier
from backend.patient_analyzer import PatientAnalyzer
from backend.analysis_cache import AnalysisJobManager
from backend.llm_engine import LLMEngine
from backend.rag_fusion import RAGFusion
from backend.s_lora_manager import SLoRAManager
from backend.mlc_learning import MLCLearning
from backend.audit_service import AuditService
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Helper for registration
def _register_device_token(
    registration: DeviceRegistration,
    request: Request,
    notifier: Notifier,
) -> Dict[str, Any]:
    """
    Register a device token for push notifications.
    
    Args:
        registration: Device registration data
        request: FastAPI request object
        notifier: Notifier service instance
        
    Returns:
        Registration status and device information
        
    Raises:
        HTTPException: If notifier is not initialized
    """
    if not notifier:
        raise HTTPException(status_code=503, detail="Notifier not initialized")

    registered = notifier.register_device(
        registration.device_token, registration.platform
    )

    correlation_id = getattr(request.state, "correlation_id", "")
    logger.info(
        "Registered device for notifications", extra={"correlation_id": correlation_id}
    )

    return {"status": "registered", "device": registered}

@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    request: Request,
    llm_engine: Optional[LLMEngine] = Depends(get_optional_llm_engine),
    rag_fusion: Optional[RAGFusion] = Depends(get_optional_rag_fusion),
    s_lora_manager: Optional[SLoRAManager] = Depends(get_optional_s_lora_manager),
    mlc_learning: Optional[MLCLearning] = Depends(get_optional_mlc_learning),
):
    """
    System health check endpoint with detailed component status.
    
    Returns overall health status and individual component availability.
    """
    from backend.database import get_db_session
    from backend.database.connection import get_redis_client
    import os
    
    health_status = {
        "status": "healthy",
        "service": "Healthcare AI Assistant",
        "version": "1.0.0",
        "vendor": "generic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        from sqlalchemy import text
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        health_status["components"]["database"] = {"status": "healthy", "available": True}
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "available": False,
            "error": str(e) if os.getenv("DEBUG", "False").lower() == "true" else "Database unavailable"
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        if redis_client:
            await redis_client.ping()
            health_status["components"]["redis"] = {"status": "healthy", "available": True}
        else:
            health_status["components"]["redis"] = {"status": "disabled", "available": False}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "available": False,
            "error": str(e) if os.getenv("DEBUG", "False").lower() == "true" else "Redis unavailable"
        }
        # Redis is optional, so don't mark overall status as degraded
    
    # Check LLM Engine
    health_status["components"]["llm_engine"] = {
        "status": "healthy" if llm_engine else "disabled",
        "available": llm_engine is not None
    }
    if not llm_engine:
        health_status["status"] = "degraded"
    
    # Check RAG Fusion
    health_status["components"]["rag_fusion"] = {
        "status": "healthy" if rag_fusion else "disabled",
        "available": rag_fusion is not None
    }
    if not rag_fusion:
        health_status["status"] = "degraded"
    
    # Check S-LoRA Manager
    health_status["components"]["s_lora_manager"] = {
        "status": "healthy" if s_lora_manager else "disabled",
        "available": s_lora_manager is not None
    }
    
    # Check MLC Learning
    health_status["components"]["mlc_learning"] = {
        "status": "healthy" if mlc_learning else "disabled",
        "available": mlc_learning is not None
    }
    
    return health_status

@router.post("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(
    auth: TokenContext = Depends(auth_dependency({"system/*.manage"})),
    analysis_job_manager: AnalysisJobManager = Depends(get_analysis_job_manager),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    patient_summary_cache: Dict[str, Dict[str, Any]] = Depends(get_patient_summary_cache),
):
    """Clear all application caches."""
    cleared_summaries = len(patient_summary_cache)
    patient_summary_cache.clear()
    
    if analysis_job_manager:
        analysis_job_manager.clear()
    
    cleared_analyses = 0
    if patient_analyzer:
        cleared_analyses = patient_analyzer.total_history_count()
        patient_analyzer.clear_history()

    return {
        "status": "cleared",
        "analysis_history_cleared": cleared_analyses,
        "summary_cache_entries_cleared": cleared_summaries,
        "analysis_cache_cleared": analysis_job_manager is not None,
    }

@router.post("/device/register", response_model=DeviceRegistrationResponse)
@router.post("/register-device", response_model=DeviceRegistrationResponse)
@router.post("/notifications/register", response_model=DeviceRegistrationResponse)
async def register_device(
    registration: DeviceRegistration,
    request: Request,
    auth: TokenContext = Depends(auth_dependency()),
    notifier: Notifier = Depends(get_notifier),
): 
    """Register a device token for push notifications."""
    return _register_device_token(registration, request, notifier)


@router.get("/stats", response_model=StatsResponse)
async def get_system_stats(
    request: Request,
    llm_engine: Optional[LLMEngine] = Depends(get_optional_llm_engine),
    rag_fusion: Optional[RAGFusion] = Depends(get_optional_rag_fusion),
    s_lora_manager: Optional[SLoRAManager] = Depends(get_optional_s_lora_manager),
    mlc_learning: Optional[MLCLearning] = Depends(get_optional_mlc_learning),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Get system statistics and performance metrics
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        stats = {
            "llm": llm_engine.get_stats() if llm_engine else None,
            "rag": rag_fusion.get_stats() if rag_fusion else None,
            "s_lora": s_lora_manager.get_stats() if s_lora_manager else None,
            "mlc": mlc_learning.get_stats() if mlc_learning else None,
            "rl": mlc_learning.get_rl_stats() if mlc_learning else None,
        }
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error("Error fetching stats [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adapters", response_model=Dict[str, Any])
async def get_adapters_status(
    s_lora_manager: Optional[SLoRAManager] = Depends(get_optional_s_lora_manager),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Get status of S-LoRA adapters (active vs available).
    """
    if not s_lora_manager:
        return {
            "status": "disabled",
            "active_adapters": [],
            "available_adapters": [],
            "memory_usage": {},
            "specialties": {},
        }

    status = await s_lora_manager.get_status()
    
    return {
        "status": "success",
        "active_adapters": status.get("active", []),
        "available_adapters": status.get("available", []),
        "memory_usage": status.get("memory", {}),
        "specialties": status.get("specialties", {}),
    }

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request

from backend.analysis_cache import AnalysisJobManager
from backend.audit_service import AuditService
from backend.fhir_resource_service import FhirResourceService
from backend.llm_engine import LLMEngine
from backend.rag_fusion import RAGFusion
from backend.s_lora_manager import SLoRAManager
from backend.mlc_learning import MLCLearning
from backend.aot_reasoner import AoTReasoner
from backend.notifier import Notifier
from backend.patient_analyzer import PatientAnalyzer
from backend.security import TokenContext
from backend.state.user_store import UserStateStore
from backend.database import DatabaseService
from .container import ServiceContainer


def get_container(request: Request) -> ServiceContainer:
    container = getattr(request.app.state, "container", None)
    if not container:
        raise HTTPException(status_code=503, detail="Service container not initialized")
    return container


def get_fhir_connector(
    container: ServiceContainer = Depends(get_container),
) -> FhirResourceService:
    connector = container.fhir_connector
    if connector is None:
        raise HTTPException(status_code=503, detail="FHIR connector not initialized")
    return connector


def get_patient_analyzer(
    container: ServiceContainer = Depends(get_container),
) -> PatientAnalyzer:
    analyzer = container.patient_analyzer
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Patient analyzer not initialized")
    return analyzer


def get_llm_engine(container: ServiceContainer = Depends(get_container)) -> LLMEngine:
    engine = container.llm_engine
    if engine is None:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    return engine


def get_optional_llm_engine(
    container: ServiceContainer = Depends(get_container),
) -> Optional[LLMEngine]:
    return container.llm_engine


def get_rag_fusion(container: ServiceContainer = Depends(get_container)) -> RAGFusion:
    rag_fusion = container.rag_fusion
    if rag_fusion is None:
        raise HTTPException(status_code=503, detail="RAG Fusion not initialized")
    return rag_fusion


def get_optional_rag_fusion(
    container: ServiceContainer = Depends(get_container),
) -> Optional[RAGFusion]:
    return container.rag_fusion


def get_s_lora_manager(
    container: ServiceContainer = Depends(get_container),
) -> SLoRAManager:
    s_lora_manager = container.s_lora_manager
    if s_lora_manager is None:
        raise HTTPException(status_code=503, detail="S-LoRA manager not initialized")
    return s_lora_manager


def get_optional_s_lora_manager(
    container: ServiceContainer = Depends(get_container),
) -> Optional[SLoRAManager]:
    return container.s_lora_manager


def get_mlc_learning(
    container: ServiceContainer = Depends(get_container),
) -> MLCLearning:
    mlc_learning = container.mlc_learning
    if mlc_learning is None:
        raise HTTPException(status_code=503, detail="MLC Learning not initialized")
    return mlc_learning


def get_optional_mlc_learning(
    container: ServiceContainer = Depends(get_container),
) -> Optional[MLCLearning]:
    return container.mlc_learning


def get_aot_reasoner(
    container: ServiceContainer = Depends(get_container),
) -> AoTReasoner:
    aot_reasoner = container.aot_reasoner
    if aot_reasoner is None:
        raise HTTPException(status_code=503, detail="AoT Reasoner not initialized")
    return aot_reasoner


def get_notifier(container: ServiceContainer = Depends(get_container)) -> Notifier:
    notifier = container.notifier
    if notifier is None:
        raise HTTPException(status_code=503, detail="Notifier not initialized")
    return notifier


def get_analysis_job_manager(
    container: ServiceContainer = Depends(get_container),
) -> AnalysisJobManager:
    manager = container.analysis_job_manager
    if manager is None:
        raise HTTPException(status_code=503, detail="Analysis job manager not initialized")
    return manager


def get_audit_service(
    container: ServiceContainer = Depends(get_container),
) -> AuditService:
    audit_service = container.audit_service
    if audit_service is None:
        raise HTTPException(status_code=503, detail="Audit service not initialized")
    return audit_service


def get_optional_audit_service(request: Request) -> Optional[AuditService]:
    """Return the audit service if available without raising."""

    container = getattr(request.app.state, "container", None)
    if not container:
        return None
    return container.audit_service


def get_user_state_store(
    container: ServiceContainer = Depends(get_container),
) -> UserStateStore:
    store = container.user_state_store
    if store is None:
        raise HTTPException(status_code=503, detail="User state store not initialized")
    return store


def get_patient_summary_cache(
    container: ServiceContainer = Depends(get_container),
) -> Dict[str, Any]:
    return container.patient_summary_cache


def derive_user_key(auth: TokenContext) -> str:
    """Return a stable identifier for user-specific state."""

    return auth.subject or "anonymous"


def get_database_service(request: Request) -> Optional[DatabaseService]:
    """Get database service from app state."""
    return getattr(request.app.state, "db_service", None)

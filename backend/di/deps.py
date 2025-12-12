from fastapi import Depends, Request

from backend.analysis_cache import AnalysisJobManager
from backend.audit_service import AuditService
from backend.fhir_resource_service import FhirResourceService
from backend.llm_engine import LLMEngine
from backend.patient_analyzer import PatientAnalyzer
from .container import ServiceContainer


def get_container(request: Request) -> ServiceContainer:
    container = getattr(request.app.state, "container", None)
    if not container:
        raise RuntimeError("Service container not initialized")
    return container


def get_fhir_connector(
    container: ServiceContainer = Depends(get_container),
) -> FhirResourceService:
    connector = container.fhir_connector
    if connector is None:
        raise RuntimeError("FHIR connector not initialized")
    return connector


def get_patient_analyzer(
    container: ServiceContainer = Depends(get_container),
) -> PatientAnalyzer:
    analyzer = container.patient_analyzer
    if analyzer is None:
        raise RuntimeError("Patient analyzer not initialized")
    return analyzer


def get_llm_engine(container: ServiceContainer = Depends(get_container)) -> LLMEngine:
    engine = container.llm_engine
    if engine is None:
        raise RuntimeError("LLM engine not initialized")
    return engine


def get_analysis_job_manager(
    container: ServiceContainer = Depends(get_container),
) -> AnalysisJobManager:
    manager = container.analysis_job_manager
    if manager is None:
        raise RuntimeError("Analysis job manager not initialized")
    return manager


def get_audit_service(
    container: ServiceContainer = Depends(get_container),
) -> AuditService:
    audit_service = container.audit_service
    if audit_service is None:
        raise RuntimeError("Audit service not initialized")
    return audit_service

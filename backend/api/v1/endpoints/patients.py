from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional
import os
import asyncio
import logging
from datetime import datetime, timezone

from backend.models import (
    PatientListResponse,
    DashboardEntry,
    AlertsResponse,
    AnalyzePatientResponse,
    AnalyzePatientRequest,
    DashboardSummaryEntry,
    PatientFHIRResponse,
    ExplainResponse,
)
from backend.security import TokenContext, auth_dependency
from backend.di import (
    get_patient_analyzer,
    get_fhir_connector,
    get_analysis_job_manager,
    get_audit_service,
    get_patient_summary_cache,
)
from backend.patient_analyzer import PatientAnalyzer
from backend.fhir_connector import FHIRConnectorError, FhirResourceService
from backend.analysis_cache import AnalysisJobManager
from backend.audit_service import AuditService
from backend.explainability import explain_risk
from backend.patient_data_service import PatientDataService
from backend.utils.validation import validate_patient_id, validate_patient_id_list
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler

logger = logging.getLogger(__name__)

router = APIRouter()

notifications_enabled: bool = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"

# Helpers (kept in this file as private domain logic for these endpoints)

async def _latest_analysis_for_patient(
    patient_id: str, patient_analyzer: Optional[PatientAnalyzer]
) -> Optional[Dict[str, Any]]:
    """
    Get the latest analysis for a patient from the patient analyzer.
    Returns None if analyzer is not available or no analysis exists.
    """
    if not patient_analyzer:
        return None
    return await patient_analyzer.get_latest_analysis(patient_id)


def _dashboard_patient_list() -> List[Dict[str, Optional[str]]]:
    """
    Get the list of patient IDs to display on the dashboard.
    Reads from DASHBOARD_PATIENT_IDS environment variable or returns default demo patients.
    """
    env_value = os.getenv("DASHBOARD_PATIENT_IDS", "").strip()
    patients: List[Dict[str, Optional[str]]] = []

    if env_value:
        for raw_value in env_value.split(","):
            patient_id = raw_value.strip()
            if not patient_id:
                continue
            patients.append({"patient_id": patient_id, "name": None})

    if not patients:
        patients = [
            {"patient_id": "demo-patient-1", "name": "Alex Johnson", "specialty": "Cardiology"},
            {"patient_id": "demo-patient-2", "name": "Priya Singh", "specialty": "Oncology"},
            {"patient_id": "demo-patient-3", "name": "Miguel Rodriguez", "specialty": "Endocrinology"},
        ]

    return patients


async def _build_patient_list_entry(
    patient: Dict[str, Optional[str]],
    patient_data: Optional[Dict[str, Any]],
    patient_analyzer: Optional[PatientAnalyzer],
) -> Dict[str, Any]:
    """
    Build a patient list entry dictionary from patient info, data, and analysis.
    Combines patient demographics with latest analysis results.
    """
    latest_analysis = await _latest_analysis_for_patient(
        patient.get("patient_id", ""), patient_analyzer
    )
    analysis_patient_data = (latest_analysis or {}).get("patient_data") or {}

    patient_info = (
        (patient_data or {}).get("patient")
        or analysis_patient_data.get("patient")
        or {}
    )
    patient_id = patient_info.get("id") or patient.get("patient_id")
    name = patient_info.get("name") or patient.get("name") or patient_id

    age = PatientDataService._calculate_age(patient_info.get("birthDate"))

    alerts = (latest_analysis or {}).get("alerts") or []
    highest_alert_severity = (
        (latest_analysis or {}).get("highest_alert_severity")
        or PatientAnalyzer._highest_alert_severity(alerts)
    )

    risk_scores = (latest_analysis or {}).get("risk_scores") or {}
    overall_risk_score = (latest_analysis or {}).get("overall_risk_score")
    if overall_risk_score is None and risk_scores:
        overall_risk_score = PatientAnalyzer._derive_overall_risk_score(risk_scores)

    last_analyzed_at = (latest_analysis or {}).get("last_analyzed_at") or (
        latest_analysis or {}
    ).get("analysis_timestamp")

    return {
        "id": patient_id,
        "patient_id": patient_id,
        "name": name,
        "full_name": name,
        "age": age,
        "mrn": patient_info.get("mrn"),
        "last_updated": (patient_data or {}).get("fetched_at"),
        "highest_alert_severity": highest_alert_severity,
        "latest_risk_score": overall_risk_score,
        "last_analyzed_at": last_analyzed_at,
    }


def _extract_summary_from_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a summary dictionary from a full analysis result.
    Normalizes alerts and extracts key metrics for dashboard display.
    """
    alerts = analysis.get("alerts") or []
    normalized_alerts = []

    for alert in alerts:
        if isinstance(alert, str):
            normalized_alerts.append({"message": alert, "severity": "info"})
        else:
            normalized_alerts.append(alert)

    critical_alerts = len(
        [a for a in normalized_alerts if a.get("severity") == "critical"]
    )
    highest_alert_severity = analysis.get("highest_alert_severity") or PatientAnalyzer._highest_alert_severity(alerts)
    risk_scores = analysis.get("risk_scores") or {}
    overall_risk_score = analysis.get("overall_risk_score")
    if overall_risk_score is None and risk_scores:
        overall_risk_score = PatientAnalyzer._derive_overall_risk_score(risk_scores)
    
    patient_summary = analysis.get("summary") or {}
    patient_data = analysis.get("patient_data") or {}
    patient_name = (
        patient_summary.get("patient_name")
        or patient_data.get("patient", {}).get("name")
        or analysis.get("patient_id")
    )
    last_analysis = (
        analysis.get("analysis_timestamp")
        or analysis.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    last_updated = datetime.now(timezone.utc).isoformat()

    return {
        "patient_id": analysis.get("patient_id"),
        "patient_name": patient_name,
        "overall_risk_score": overall_risk_score,
        "highest_alert_severity": highest_alert_severity,
        "critical_alerts": critical_alerts,
        "cardiovascular_risk": risk_scores.get("cardiovascular_risk"),
        "readmission_risk": risk_scores.get("readmission_risk"),
        "last_analysis": last_analysis,
        "last_updated": last_updated,
    }


async def _get_patient_summary(
    patient_id: str,
    auth: TokenContext,
    *,
    patient_analyzer: Optional[PatientAnalyzer],
    fhir_connector: Optional[FhirResourceService],
    analysis_job_manager: Optional[AnalysisJobManager],
    patient_summary_cache: Dict[str, Dict[str, Any]],
    use_request_context: bool = True,
) -> Dict[str, Any]:
    cached = patient_summary_cache.get(patient_id)
    latest_analysis = await _latest_analysis_for_patient(patient_id, patient_analyzer)

    if cached and (
        not latest_analysis
        or cached.get("analysis_timestamp") == latest_analysis.get("analysis_timestamp")
    ):
        return cached["summary"]

    if not patient_analyzer or not fhir_connector:
        raise create_http_exception(
            message="Patient analyzer not initialized",
            status_code=503,
            error_type="ServiceUnavailable"
        )

    if latest_analysis:
        summary = _extract_summary_from_analysis(latest_analysis)
        patient_summary_cache[patient_id] = {
            "analysis_timestamp": summary["last_analysis"],
            "summary": summary,
        }
        return summary

    analysis_key = None
    if analysis_job_manager:
        analysis_key = analysis_job_manager.cache_key(
            patient_id=patient_id,
            include_recommendations=False,
            specialty=None,
            analysis_focus="dashboard_summary",
        )

    async def _run_analysis() -> Dict[str, Any]:
        return await patient_analyzer.analyze(
            patient_id=patient_id,
            include_recommendations=False,
            analysis_focus="dashboard_summary",
        )

    async def _run_with_context() -> Dict[str, Any]:
        if use_request_context:
            async with fhir_connector.request_context(
                auth.access_token, auth.scopes, auth.patient
            ):
                return await _run_analysis()
        return await _run_analysis()

    if analysis_key and analysis_job_manager:
        latest_analysis, _ = await analysis_job_manager.get_or_create(
            analysis_key, _run_with_context
        )
    else:
        latest_analysis = await _run_with_context()

    summary = _extract_summary_from_analysis(latest_analysis)

    patient_summary_cache[patient_id] = {
        "analysis_timestamp": summary["last_analysis"],
        "summary": summary,
    }
    return summary


def _build_dashboard_entry_from_summary(
    summary: Dict[str, Any], fallback_name: Optional[str]
) -> Dict[str, Any]:
    patient_name = summary.get("patient_name") or fallback_name or summary.get("patient_id")
    latest_risk_score = summary.get("overall_risk_score") or summary.get("cardiovascular_risk")

    return {
        "patient_id": summary.get("patient_id"),
        "name": patient_name,
        "latest_risk_score": latest_risk_score,
        "highest_alert_severity": summary.get("highest_alert_severity"),
        "last_analyzed_at": summary.get("last_analysis"),
        "specialty": summary.get("specialty"),
    }

async def _queue_analysis_update(summary: Dict[str, Any], app: Any) -> None:
    container = getattr(app.state, "container", None)
    if container and container.analysis_update_queue:
        await container.analysis_update_queue.put(summary)


# Endpoints with corrected paths to match original /api/v1/ structure

@router.get("/patients", response_model=PatientListResponse)
async def list_patients(
    request: Request,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    audit_service: AuditService = Depends(get_audit_service),
):
    correlation_id = get_correlation_id(request)
    
    if not patient_analyzer or not fhir_connector:
        raise create_http_exception(
            message="Patient analyzer not initialized",
            status_code=503,
            error_type="ServiceUnavailable"
        )

    patients = _dashboard_patient_list()

    if auth.patient:
        patients = [p for p in patients if p.get("patient_id") == auth.patient]
        if not patients:
            raise create_http_exception(
                message="Token is scoped to a patient outside the configured roster",
                status_code=403,
                error_type="Forbidden"
            )

    try:
        log_structured(
            level="info",
            message="Fetching patient roster",
            correlation_id=correlation_id,
            request=request,
            patient_count=len(patients)
        )
        
        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            roster = []
            for patient in patients:
                patient_data = None
                try:
                    patient_data = await patient_analyzer.patient_data_service.fetch_patient_data(
                        patient["patient_id"]
                    )
                except Exception as exc:
                    log_structured(
                        level="warning",
                        message="Unable to fetch demographics for patient",
                        correlation_id=correlation_id,
                        request=request,
                        patient_id=patient.get("patient_id"),
                        error=str(exc)
                    )

                roster.append(
                    await _build_patient_list_entry(patient, patient_data, patient_analyzer)
                )

        log_structured(
            level="info",
            message="Patient roster fetched successfully",
            correlation_id=correlation_id,
            request=request,
            roster_size=len(roster)
        )
        
        return {"patients": roster}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "list_patients", "patient_count": len(patients)},
            correlation_id,
            request
        )


@router.get("/patients/dashboard", response_model=List[DashboardEntry])
async def get_dashboard_patients(
    request: Request,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    analysis_job_manager: AnalysisJobManager = Depends(get_analysis_job_manager),
    audit_service: AuditService = Depends(get_audit_service),
    patient_summary_cache: Dict[str, Dict[str, Any]] = Depends(
        get_patient_summary_cache
    ),
):
    correlation_id = get_correlation_id(request)
    
    if not patient_analyzer or not fhir_connector:
        raise create_http_exception(
            message="Patient analyzer not initialized",
            status_code=503,
            error_type="ServiceUnavailable"
        )

    patients = _dashboard_patient_list()
    patient_ids = [patient["patient_id"] for patient in patients]

    try:
        log_structured(
            level="info",
            message="Building dashboard overview",
            correlation_id=correlation_id,
            request=request,
            patient_count=len(patient_ids)
        )
        
        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            summary_tasks = [
                _get_patient_summary(
                    patient_id=patient_id,
                    auth=auth,
                    patient_analyzer=patient_analyzer,
                    fhir_connector=fhir_connector,
                    analysis_job_manager=analysis_job_manager,
                    patient_summary_cache=patient_summary_cache,
                    use_request_context=False,
                )
                for patient_id in patient_ids
            ]

            summaries = await asyncio.gather(*summary_tasks)

        dashboard_entries = []
        for summary, patient in zip(summaries, patients):
            if patient.get("specialty"):
                summary["specialty"] = patient.get("specialty")
            dashboard_entries.append(_build_dashboard_entry_from_summary(summary, fallback_name=patient.get("name")))

        log_structured(
            level="info",
            message="Dashboard overview built successfully",
            correlation_id=correlation_id,
            request=request,
            entry_count=len(dashboard_entries)
        )
        
        return dashboard_entries
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_dashboard_patients", "patient_count": len(patient_ids)},
            correlation_id,
            request
        )


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    request: Request,
    limit: int = Query(25, ge=1, le=200),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    audit_service: AuditService = Depends(get_audit_service),
):
    correlation_id = get_correlation_id(request)
    
    if not patient_analyzer:
        raise create_http_exception(
            message="Patient analyzer not initialized",
            status_code=503,
            error_type="ServiceUnavailable"
        )

    try:
        log_structured(
            level="info",
            message="Collecting alert feed",
            correlation_id=correlation_id,
            request=request,
            limit=limit,
            patient_id=auth.patient
        )
        
        roster_lookup = {p["patient_id"]: p.get("name") for p in _dashboard_patient_list()}
        alerts = patient_analyzer.collect_recent_alerts(
            limit,
            patient_id=auth.patient,
            roster_lookup=roster_lookup,
        )
        
        log_structured(
            level="info",
            message="Alert feed collected successfully",
            correlation_id=correlation_id,
            request=request,
            alert_count=len(alerts)
        )
        
        return {"alerts": alerts}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_alerts", "limit": limit, "patient_id": auth.patient},
            correlation_id,
            request
        )


@router.post(
    "/analyze-patient",
    response_model=AnalyzePatientResponse,
    response_model_exclude_none=True,
)
async def analyze_patient(
    request: Request,
    fhir_patient_id: Optional[str] = None,
    include_recommendations: bool = True,
    specialty: Optional[str] = None,
    notify: Optional[bool] = False,
    analysis: Optional[AnalyzePatientRequest] = None,
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    analysis_job_manager: AnalysisJobManager = Depends(get_analysis_job_manager),
    audit_service: AuditService = Depends(get_audit_service),
    patient_summary_cache: Dict[str, Dict[str, Any]] = Depends(
        get_patient_summary_cache
    ),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    correlation_id = getattr(
        request.state,
        "correlation_id",
        audit_service.new_correlation_id() if audit_service else "",
    )
    patient_id: Optional[str] = fhir_patient_id

    try:
        if not patient_analyzer or not fhir_connector:
            raise create_http_exception(
                message="Patient analyzer not initialized",
                status_code=503,
                error_type="ServiceUnavailable"
            )

        payload_patient_id = None
        if analysis:
            payload_patient_id = analysis.fhir_patient_id or analysis.patient_id

        patient_id = payload_patient_id or patient_id
        if not patient_id:
            raise HTTPException(status_code=422, detail="patient_id is required")
        
        # Validate patient_id
        patient_id = validate_patient_id(patient_id)

        logger.info(f"Analyzing patient: {patient_id}")

        if auth.patient and auth.patient != patient_id:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a different patient context",
            )

        include_recs = (
            analysis.include_recommendations
            if analysis and getattr(analysis, 'include_recommendations', None) is not None
            else include_recommendations
        )
        requested_specialty = getattr(analysis, 'specialty', None) if analysis else specialty
        should_notify = getattr(analysis, 'notify', False) if analysis else notify

        force_refresh = bool(notifications_enabled and should_notify)
        analysis_key = None

        if analysis_job_manager:
            analysis_key = analysis_job_manager.cache_key(
                patient_id=patient_id,
                include_recommendations=include_recs,
                specialty=requested_specialty,
                analysis_focus=None,
            )

        async def _run_analysis() -> Dict[str, Any]:
            async with fhir_connector.request_context(
                auth.access_token, auth.scopes, auth.patient
            ):
                return await patient_analyzer.analyze(
                    patient_id=patient_id,
                    include_recommendations=include_recs,
                    specialty=requested_specialty,
                    notify=bool(notifications_enabled and should_notify),
                    correlation_id=correlation_id,
                )

        if analysis_job_manager and analysis_key:
            result, from_cache = await analysis_job_manager.get_or_create(
                analysis_key, _run_analysis, force_refresh=force_refresh
            )
        else:
            result = await _run_analysis()
            from_cache = False

        # Cache and broadcast the latest dashboard summary for real-time updates
        summary = _extract_summary_from_analysis(result)
        patient_summary_cache[patient_id] = {
            "analysis_timestamp": summary["last_analysis"],
            "summary": summary,
        }
        if not from_cache:
            await _queue_analysis_update(summary, app=request.app)

        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Patient analysis completed",
                event_type="analyze",
                include_provenance=True,
                provenance_activity="patient-analysis",
            )
        return result

    except FHIRConnectorError as exc:
        log_service_error(
            exc,
            {"operation": "analyze_patient", "patient_id": patient_id},
            correlation_id,
            request
        )
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=exc.message,
                event_type="analyze",
            )
        error_payload = {
            "status": "error",
            "error_type": exc.error_type,
            "message": exc.message,
            "correlation_id": exc.correlation_id or correlation_id,
        }
        return JSONResponse(status_code=502, content=error_payload)
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "analyze_patient", "patient_id": patient_id},
            correlation_id,
            request
        )


@router.get("/patient/{patient_id}/fhir", response_model=PatientFHIRResponse)
async def get_patient_fhir(
    request: Request,
    patient_id: str,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Fetch raw FHIR patient data for a given patient ID.
    """
    # Validate patient_id
    patient_id = validate_patient_id(patient_id)
    
    correlation_id = get_correlation_id(request)

    try:
        log_structured(
            level="info",
            message="Fetching FHIR patient data",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id
        )
        
        if not fhir_connector:
            raise create_http_exception(
                message="FHIR connector not initialized",
                status_code=503,
                error_type="ServiceUnavailable"
            )

        if auth.patient and auth.patient != patient_id:
            raise create_http_exception(
                message="Token is scoped to a different patient context",
                status_code=403,
                error_type="Forbidden"
            )

        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            patient_data = await fhir_connector.get_patient(patient_id)

        if audit_service:
            await audit_service.record_event(
                action="R",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="FHIR patient read",
                event_type="read",
            )

        return {
            "status": "success",
            "patient_id": patient_id,
            "data": patient_data
        }

    except FHIRConnectorError as exc:
        logger.error(
            "FHIR connector error fetching patient [%s]: %s", correlation_id, exc.message
        )
        error_payload = {
            "status": "error",
            "error_type": exc.error_type,
            "message": exc.message,
            "correlation_id": exc.correlation_id or correlation_id,
        }
        return JSONResponse(status_code=502, content=error_payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching patient FHIR data [%s]: %s", correlation_id, str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}/explain", response_model=ExplainResponse)
@router.get("/explain/{patient_id}", response_model=ExplainResponse)
async def explain_patient_risk(
    request: Request,
    patient_id: str,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    audit_service: AuditService = Depends(get_audit_service),
):
    # Validate patient_id
    patient_id = validate_patient_id(patient_id)
    
    correlation_id = get_correlation_id(request)

    try:
        log_structured(
            level="info",
            message="Generating SHAP explanations for patient risk",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id
        )
        
        if not patient_analyzer:
            raise create_http_exception(
                message="Patient analyzer not initialized",
                status_code=503,
                error_type="ServiceUnavailable"
            )

        if auth.patient and auth.patient != patient_id:
            raise create_http_exception(
                message="Token is scoped to a different patient context",
                status_code=403,
                error_type="Forbidden"
            )

        analysis = await patient_analyzer.analyze(
            patient_id,
            include_recommendations=False,
            analysis_focus="risk_assessment",
        )
        explanation = explain_risk(analysis)

        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Generated SHAP explanations",
                event_type="explain",
            )

        return {
            "status": "success",
            "patient_id": patient_id,
            "feature_names": explanation.get("feature_names", []),
            "shap_values": explanation.get("shap_values", []),
            "base_value": explanation.get("base_value"),
            "risk_score": explanation.get("risk_score"),
            "model_type": explanation.get("model_type"),
            "correlation_id": correlation_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error generating SHAP explanations [%s]: %s", correlation_id, str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard-summary", response_model=List[DashboardSummaryEntry])
async def dashboard_summary(
    request: Request,
    patient_ids: Optional[List[str]] = Query(
        None, description="Specific patient IDs to include in the dashboard"
    ),
    limit: Optional[int] = Query(
        None, ge=1, description="Maximum number of patients to return"
    ),
    sort_by: str = Query(
        "cardiovascular_risk",
        description="Sort order for patients (cardiovascular_risk, readmission_risk, critical_alerts, last_analysis)",
    ),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    analysis_job_manager: AnalysisJobManager = Depends(get_analysis_job_manager),
    patient_summary_cache: Dict[str, Dict[str, Any]] = Depends(
        get_patient_summary_cache
    ),
):
    correlation_id = get_correlation_id(request)
    
    if not patient_analyzer:
        raise create_http_exception(
            message="Patient analyzer not initialized",
            status_code=503,
            error_type="ServiceUnavailable"
        )

    if not patient_ids:
        seen: set = set()
        patient_ids = []
        for analysis in reversed(patient_analyzer.get_history()):
            pid = analysis.get("patient_id")
            if pid and pid not in seen:
                seen.add(pid)
                patient_ids.append(pid)

    if not patient_ids:
        return []

    try:
        log_structured(
            level="info",
            message="Building dashboard summary",
            correlation_id=correlation_id,
            request=request,
            patient_count=len(patient_ids),
            sort_by=sort_by,
            limit=limit
        )
        
        # Optimize: Use asyncio.gather for parallel processing
        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            summary_tasks = [
                _get_patient_summary(
                    patient_id,
                    auth,
                    patient_analyzer=patient_analyzer,
                    fhir_connector=fhir_connector,
                    analysis_job_manager=analysis_job_manager,
                    patient_summary_cache=patient_summary_cache,
                    use_request_context=False,
                )
                for patient_id in patient_ids
            ]
            summaries = await asyncio.gather(*summary_tasks)

        def _timestamp_value(value: Optional[str]) -> datetime:
            try:
                return datetime.fromisoformat(value) if value else datetime.min.replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.min.replace(tzinfo=timezone.utc)

        sort_options = {
            "cardiovascular_risk": lambda s: s.get("cardiovascular_risk") or 0,
            "readmission_risk": lambda s: s.get("readmission_risk") or 0,
            "critical_alerts": lambda s: s.get("critical_alerts") or 0,
            "last_analysis": lambda s: _timestamp_value(s.get("last_analysis")),
        }

        sort_key = sort_options.get(sort_by, sort_options["cardiovascular_risk"])
        summaries.sort(key=sort_key, reverse=True)

        if limit is not None:
            summaries = summaries[:limit]

        log_structured(
            level="info",
            message="Dashboard summary built successfully",
            correlation_id=correlation_id,
            request=request,
            summary_count=len(summaries)
        )

        return summaries
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "dashboard_summary", "patient_count": len(patient_ids) if patient_ids else 0},
            correlation_id,
            request
        )

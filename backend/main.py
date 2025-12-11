"""
Healthcare AI Assistant - Main Application Entry Point
Integrates FHIR data with advanced AI techniques (S-LoRA, MLC, RAG, AoT)
"""

import asyncio
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import uvicorn
import os
from dotenv import load_dotenv
from security import TokenContext, auth_dependency, close_shared_async_client
from audit_service import AuditService
from pydantic import BaseModel, root_validator, validator
from jose import jwt

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core modules (to be implemented)
from fhir_connector import FHIRConnectorError, FhirHttpClient, FhirResourceService
from llm_engine import LLMEngine
from rag_fusion import RAGFusion
from s_lora_manager import SLoRAManager
from mlc_learning import MLCLearning
from aot_reasoner import AoTReasoner
from patient_analyzer import PatientAnalyzer
from patient_data_service import PatientDataService
from notifier import Notifier
from explainability import explain_risk

# Global instances
fhir_client = None
fhir_connector = None
llm_engine = None
rag_fusion = None
s_lora_manager = None
mlc_learning = None
aot_reasoner = None
patient_analyzer = None
notifier = None
audit_service = None
analysis_update_queue: Optional[asyncio.Queue] = None
active_websockets: Dict[WebSocket, TokenContext] = {}
broadcast_task: Optional[asyncio.Task] = None
notifications_enabled: bool = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
demo_login_enabled: bool = os.getenv("ENABLE_DEMO_LOGIN", "false").lower() == "true"
demo_login_secret: str = os.getenv("DEMO_JWT_SECRET", "dev-secret-change-me")
demo_login_expires_minutes: int = int(os.getenv("DEMO_JWT_EXPIRES", "15"))

# In-memory cache for patient dashboard summaries
patient_summary_cache: Dict[str, Dict[str, Any]] = {}


class DeviceRegistration(BaseModel):
    device_token: str
    platform: str = "unknown"

    @root_validator(pre=True)
    def populate_device_token(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Allow payloads that send push_token instead of device_token."""

        if not values.get("device_token") and values.get("push_token"):
            values["device_token"] = values["push_token"]
        return values

    @validator("platform")
    def validate_platform(cls, value: str) -> str:
        normalized = value.strip().lower() if value else "unknown"
        if normalized in {"ios", "android"}:
            return "iOS" if normalized == "ios" else "Android"
        if normalized in {"expo", "unknown", ""}:
            return "Expo" if normalized == "expo" else "Unknown"
        raise ValueError("platform must be iOS, Android, or Expo")


class AnalyzePatientRequest(BaseModel):
    fhir_patient_id: Optional[str] = None
    patient_id: Optional[str] = None
    include_recommendations: Optional[bool] = True
    specialty: Optional[str] = None
    notify: Optional[bool] = None


class DemoLoginRequest(BaseModel):
    email: str
    password: str
    patient: Optional[str] = None


class DemoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management - startup and shutdown
    """
    # Startup
    logger.info("Initializing Healthcare AI Assistant...")
    try:
        global fhir_client, fhir_connector, llm_engine, rag_fusion, s_lora_manager, mlc_learning, aot_reasoner, patient_analyzer
        global audit_service, notifier
        
        # Initialize core components
        logger.info("Loading FHIR HTTP client and resource service...")
        fhir_client = FhirHttpClient(
            server_url=os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir"),
            vendor=os.getenv("EHR_VENDOR", "generic"),
            client_id=os.getenv("SMART_CLIENT_ID", ""),
            client_secret=os.getenv("SMART_CLIENT_SECRET", ""),
            scope=os.getenv(
                "SMART_SCOPE", "system/*.read patient/*.read user/*.read"
            ),
            auth_url=os.getenv("SMART_AUTH_URL") or None,
            token_url=os.getenv("SMART_TOKEN_URL") or None,
            well_known_url=os.getenv("SMART_WELL_KNOWN") or None,
            audience=os.getenv("SMART_AUDIENCE") or None,
            refresh_token=os.getenv("SMART_REFRESH_TOKEN") or None,
        )
        fhir_connector = FhirResourceService(fhir_client)
        
        logger.info("Loading LLM Engine...")
        llm_engine = LLMEngine(
            model_name=os.getenv("LLM_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        
        logger.info("Loading RAG-Fusion Component...")
        rag_fusion = RAGFusion(
            knowledge_base_path=os.getenv("KB_PATH", "./data/medical_kb"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
        
        logger.info("Loading S-LoRA Manager...")
        s_lora_manager = SLoRAManager(
            adapter_path=os.getenv("ADAPTER_PATH", "./models/adapters"),
            base_model=os.getenv("BASE_MODEL", "meta-llama/Llama-2-7b-hf")
        )
        
        logger.info("Loading MLC Learning System...")
        mlc_learning = MLCLearning(
            learning_rate=float(os.getenv("MLC_LEARNING_RATE", "0.001")),
            feedback_history_path=os.getenv("FEEDBACK_PATH", "./data/feedback")
        )
        
        logger.info("Loading Algorithm of Thought Reasoner...")
        aot_reasoner = AoTReasoner(
            reasoning_depth=int(os.getenv("REASONING_DEPTH", "3"))
        )
        
        logger.info("Loading Notifier...")
        notifier = Notifier()

        logger.info("Initializing Patient Analyzer...")
        patient_analyzer = PatientAnalyzer(
            fhir_connector=fhir_connector,
            llm_engine=llm_engine,
            rag_fusion=rag_fusion,
            s_lora_manager=s_lora_manager,
            aot_reasoner=aot_reasoner,
            mlc_learning=mlc_learning,
            notifier=notifier,
            notifications_enabled=notifications_enabled,
        )

        logger.info("Initializing Audit Service...")
        audit_service = AuditService(fhir_connector=fhir_connector)

        # Initialize real-time update infrastructure
        global analysis_update_queue, active_websockets, broadcast_task
        analysis_update_queue = asyncio.Queue()
        active_websockets = {}
        broadcast_task = asyncio.create_task(_broadcast_analysis_updates())
        
        logger.info("✓ Healthcare AI Assistant initialized successfully")
        
    except Exception as e:
        logger.error(f"Initialization error: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Healthcare AI Assistant...")
    # Add cleanup code here if needed
    if broadcast_task:
        broadcast_task.cancel()
        try:
            await broadcast_task
        except asyncio.CancelledError:
            pass

    for websocket in list(active_websockets.keys()):
        try:
            await websocket.close(code=1001)
        except Exception:
            pass

    await close_shared_async_client()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Healthcare AI Assistant",
    description="AI-powered healthcare application with FHIR integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or (
        audit_service.new_correlation_id() if audit_service else uuid.uuid4().hex
    )
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# ==================== AUTHENTICATION ====================


@app.post("/api/v1/auth/login", response_model=DemoLoginResponse)
async def demo_login(payload: DemoLoginRequest):
    """
    Issue a short-lived JWT for local development and demos.

    This endpoint is disabled by default and should not be used in production.
    In production deployments, obtain SMART-on-FHIR access tokens from your
    configured IAM/authorization server instead of calling this route.
    """

    if not demo_login_enabled:
        raise HTTPException(status_code=404, detail="Demo login is disabled")

    allowed_email = os.getenv("DEMO_LOGIN_EMAIL")
    allowed_password = os.getenv("DEMO_LOGIN_PASSWORD")

    if allowed_email and payload.email.lower() != allowed_email.lower():
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if allowed_password and payload.password != allowed_password:
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if not allowed_email and not allowed_password and not payload.password:
        raise HTTPException(status_code=400, detail="Password is required for demo login")

    return _issue_demo_token(payload.email, payload.patient)


# ==================== API ENDPOINTS ====================

def get_vendor_override(request: Request, default: str = "generic") -> str:
    """Resolve vendor preference from query parameters or a default value."""

    vendor_param = request.query_params.get("vendor")
    if vendor_param:
        return vendor_param.lower()
    return default


def _latest_analysis_for_patient(patient_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent cached analysis for the patient."""

    if not patient_analyzer:
        return None

    for analysis in reversed(patient_analyzer.analysis_history):
        if analysis.get("patient_id") == patient_id:
            return analysis
    return None


def _dashboard_patient_list() -> List[Dict[str, Optional[str]]]:
    """Return configured patient IDs (and optional labels) for the dashboard."""

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
            {"patient_id": "demo-patient-1", "name": "Alex Johnson"},
            {"patient_id": "demo-patient-2", "name": "Priya Singh"},
            {"patient_id": "demo-patient-3", "name": "Miguel Rodriguez"},
        ]

    return patients


def _build_patient_list_entry(
    patient: Dict[str, Optional[str]], patient_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Normalize patient details for mobile patient list consumption."""

    patient_info = (patient_data or {}).get("patient") or {}
    patient_id = patient_info.get("id") or patient.get("patient_id")
    name = patient_info.get("name") or patient.get("name") or patient_id
    age = PatientDataService._calculate_age(patient_info.get("birthDate"))

    return {
        "id": patient_id,
        "patient_id": patient_id,
        "name": name,
        "full_name": name,
        "age": age,
        "mrn": patient_info.get("mrn"),
        "last_updated": (patient_data or {}).get("fetched_at"),
    }


def _issue_demo_token(email: str, patient: Optional[str]) -> DemoLoginResponse:
    """Create a short-lived JWT for demo use when SMART tokens are unavailable."""

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=demo_login_expires_minutes)
    scopes = "patient/*.read user/*.read system/*.read"

    payload = {
        "sub": email,
        "scope": scopes,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "demo-login",
    }

    if patient:
        payload["patient"] = patient

    token = jwt.encode(payload, demo_login_secret, algorithm="HS256")

    return DemoLoginResponse(
        access_token=token,
        expires_in=int((expires_at - issued_at).total_seconds()),
    )


def _build_dashboard_entry(analysis: Dict[str, Any], fallback_name: Optional[str]) -> Dict[str, Any]:
    """Extract dashboard-friendly fields from an analysis result."""

    risk_scores = analysis.get("risk_scores") or {}
    overall_risk_score = analysis.get("overall_risk_score")
    if overall_risk_score is None and risk_scores:
        overall_risk_score = PatientAnalyzer._derive_overall_risk_score(risk_scores)

    alerts = analysis.get("alerts") or []
    highest_alert_severity = analysis.get("highest_alert_severity") or PatientAnalyzer._highest_alert_severity(alerts)

    summary = analysis.get("summary") or {}
    patient_data = analysis.get("patient_data") or {}
    patient_name = (
        summary.get("patient_name")
        or patient_data.get("patient", {}).get("name")
        or fallback_name
        or analysis.get("patient_id")
    )

    last_analyzed = analysis.get("last_analyzed_at") or analysis.get("analysis_timestamp")

    return {
        "patient_id": analysis.get("patient_id"),
        "name": patient_name,
        "latest_risk_score": overall_risk_score,
        "highest_alert_severity": highest_alert_severity,
        "last_analyzed_at": last_analyzed,
    }


def _extract_summary_from_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Build a dashboard summary payload from a patient analysis."""

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
    risk_scores = analysis.get("risk_scores") or {}
    last_analysis = (
        analysis.get("analysis_timestamp")
        or analysis.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    last_updated = datetime.now(timezone.utc).isoformat()

    return {
        "patient_id": analysis.get("patient_id"),
        "critical_alerts": critical_alerts,
        "cardiovascular_risk": risk_scores.get("cardiovascular_risk"),
        "readmission_risk": risk_scores.get("readmission_risk"),
        "last_analysis": last_analysis,
        "last_updated": last_updated,
    }


async def _get_patient_summary(
    patient_id: str,
    auth: TokenContext,
) -> Dict[str, Any]:
    """Retrieve (and cache) dashboard summary data for a patient."""

    cached = patient_summary_cache.get(patient_id)
    latest_analysis = _latest_analysis_for_patient(patient_id)

    if cached and (
        not latest_analysis
        or cached.get("analysis_timestamp") == latest_analysis.get("analysis_timestamp")
    ):
        return cached["summary"]

    if not latest_analysis:
        if not patient_analyzer or not fhir_connector:
            raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            latest_analysis = await patient_analyzer.analyze(
                patient_id=patient_id,
                include_recommendations=False,
                analysis_focus="dashboard_summary",
            )

    summary = _extract_summary_from_analysis(latest_analysis)

    patient_summary_cache[patient_id] = {
        "analysis_timestamp": summary["last_analysis"],
        "summary": summary,
    }
    return summary


def _collect_recent_alerts(limit: int, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Aggregate recent critical alerts across analysis history."""

    alerts: List[Dict[str, Any]] = []

    if not patient_analyzer:
        return alerts[:limit]

    for analysis in reversed(patient_analyzer.analysis_history):
        timestamp = analysis.get("analysis_timestamp") or analysis.get("timestamp")
        analysis_patient_id = analysis.get("patient_id")

        if patient_id and analysis_patient_id and patient_id != analysis_patient_id:
            continue

        for idx, alert in enumerate(analysis.get("alerts") or []):
            normalized = alert if isinstance(alert, dict) else {"summary": str(alert)}
            severity = (normalized.get("severity") or "").lower()

            if severity not in {"critical", "high"}:
                continue

            alerts.append(
                {
                    "id": normalized.get("id")
                    or f"{analysis_patient_id}-{idx}-{timestamp or len(alerts)}",
                    "patient_id": analysis_patient_id,
                    "title": normalized.get("title")
                    or normalized.get("type")
                    or "Clinical Alert",
                    "summary": normalized.get("summary")
                    or normalized.get("description")
                    or normalized.get("message")
                    or str(alert),
                    "severity": normalized.get("severity") or "critical",
                    "timestamp": normalized.get("timestamp")
                    or normalized.get("created_at")
                    or timestamp
                    or datetime.now(timezone.utc).isoformat(),
                }
            )

            if len(alerts) >= limit:
                break

        if len(alerts) >= limit:
            break

    return sorted(alerts, key=lambda a: a.get("timestamp", ""), reverse=True)[:limit]


async def _broadcast_analysis_updates():
    """Broadcast queued analysis updates to all connected WebSocket clients."""

    while True:
        update = await analysis_update_queue.get()
        stale_connections = []

        update_patient_id = None
        if isinstance(update, dict):
            data = update.get("data") or {}
            update_patient_id = data.get("patient_id") or update.get("patient_id")

        for websocket, token_context in list(active_websockets.items()):
            if update_patient_id and token_context.patient and token_context.patient != update_patient_id:
                continue
            try:
                await websocket.send_json(update)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            try:
                active_websockets.pop(websocket, None)
            except KeyError:
                pass


async def _queue_analysis_update(summary: Dict[str, Any]) -> None:
    """Enqueue a dashboard summary update for WebSocket broadcast."""

    if analysis_update_queue:
        await analysis_update_queue.put({"event": "dashboard_update", "data": summary})


def _websocket_credentials_from_request(websocket: WebSocket) -> Optional[HTTPAuthorizationCredentials]:
    """Extract bearer credentials from WebSocket headers or query parameters."""

    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    query_token = websocket.query_params.get("token")
    if query_token:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=query_token)

    return None


async def _authenticate_websocket(websocket: WebSocket) -> TokenContext:
    """Validate a WebSocket connection before accepting it."""

    dependency = auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    credentials = _websocket_credentials_from_request(websocket)

    try:
        return await dependency(credentials=credentials)
    except HTTPException as exc:
        close_code = 4401 if exc.status_code == 401 else 4403
        try:
            await websocket.close(code=close_code, reason=exc.detail)
        finally:
            pass
        raise WebSocketDisconnect(code=close_code)


@app.get("/api/v1/health")
async def health_check(
    request: Request,
    vendor: Optional[str] = Query(None, description="Target EHR vendor"),
    auth: TokenContext = Depends(auth_dependency())
):
    """
    Health check endpoint
    """
    selected_vendor = get_vendor_override(
        request, default=vendor or os.getenv("EHR_VENDOR", "generic")
    )
    return {
        "status": "healthy",
        "service": "Healthcare AI Assistant",
        "version": "1.0.0",
        "vendor": selected_vendor,
    }


def _register_device_token(
    registration: DeviceRegistration, request: Request
) -> Dict[str, Any]:
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


@app.post("/api/v1/register-device")
async def register_device(
    registration: DeviceRegistration,
    request: Request,
    auth: TokenContext = Depends(auth_dependency()),
):
    """Register a device token for push notifications."""

    return _register_device_token(registration, request)


@app.post("/api/v1/notifications/register")
async def register_push_token(
    registration: DeviceRegistration,
    request: Request,
    auth: TokenContext = Depends(auth_dependency()),
):
    """Compatibility endpoint for registering Expo push tokens."""

    return _register_device_token(registration, request)


@app.get("/api/v1/patients")
async def list_patients(
    request: Request,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """Return patient roster formatted for the mobile client."""

    if not patient_analyzer or not fhir_connector:
        raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

    patients = _dashboard_patient_list()

    if auth.patient:
        patients = [p for p in patients if p.get("patient_id") == auth.patient]
        if not patients:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a patient outside the configured roster",
            )

    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
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
                    logger.warning(
                        "Unable to fetch demographics for %s: %s",
                        patient.get("patient_id"),
                        exc,
                    )

                roster.append(_build_patient_list_entry(patient, patient_data))

        return {"patients": roster}
    except Exception as exc:
        logger.error("Error fetching patient roster [%s]: %s", correlation_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/v1/patients/dashboard")
async def get_dashboard_patients(
    request: Request,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """Return a list of patients with risk and alert summaries for the dashboard."""

    if not patient_analyzer or not fhir_connector:
        raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

    patients = _dashboard_patient_list()
    patient_ids = [patient["patient_id"] for patient in patients]

    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )


    try:
        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            analysis_tasks = [
                patient_analyzer.analyze(
                    patient_id=patient_id,
                    include_recommendations=False,
                    analysis_focus="dashboard_overview",
                )
                for patient_id in patient_ids
            ]

            analyses = await asyncio.gather(*analysis_tasks)

        dashboard_entries = [
            _build_dashboard_entry(analysis, fallback_name=patient.get("name"))
            for analysis, patient in zip(analyses, patients)
        ]

        return dashboard_entries
    except Exception as exc:
        logger.error(
            "Error building dashboard overview [%s]: %s", correlation_id, str(exc)
        )
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/v1/alerts")
async def get_alerts(
    request: Request,
    limit: int = Query(25, ge=1, le=200),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """Return recent high-severity alerts for mobile notifications/feed."""

    if not patient_analyzer:
        raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        alerts = _collect_recent_alerts(limit, patient_id=auth.patient)
        return {"alerts": alerts}
    except Exception as exc:
        logger.error("Error collecting alert feed [%s]: %s", correlation_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/analyze-patient")
async def analyze_patient(
    request: Request,
    fhir_patient_id: Optional[str] = None,
    include_recommendations: bool = True,
    specialty: Optional[str] = None,
    notify: Optional[bool] = False,
    analysis: Optional[AnalyzePatientRequest] = None,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """
    Analyze a patient's FHIR records and generate insights
    
    Parameters:
    - fhir_patient_id: Patient ID in FHIR system
    - include_recommendations: Include clinical decision support
    - specialty: Target medical specialty for analysis
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )
    patient_id: Optional[str] = fhir_patient_id

    try:
        if not patient_analyzer or not fhir_connector:
            raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

        payload_patient_id = None
        if analysis:
            payload_patient_id = analysis.fhir_patient_id or analysis.patient_id

        patient_id = payload_patient_id or patient_id
        if not patient_id:
            raise HTTPException(status_code=422, detail="patient_id is required")

        logger.info(f"Analyzing patient: {patient_id}")

        if auth.patient and auth.patient != patient_id:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a different patient context",
            )

        include_recs = (
            analysis.include_recommendations
            if analysis and analysis.include_recommendations is not None
            else include_recommendations
        )
        requested_specialty = analysis.specialty if analysis else specialty
        should_notify = analysis.notify if analysis and analysis.notify is not None else notify

        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            result = await patient_analyzer.analyze(
                patient_id=patient_id,
                include_recommendations=include_recs,
                specialty=requested_specialty,
                notify=bool(notifications_enabled and should_notify),
                correlation_id=correlation_id,
            )

        # Cache and broadcast the latest dashboard summary for real-time updates
        summary = _extract_summary_from_analysis(result)
        patient_summary_cache[patient_id] = {
            "analysis_timestamp": summary["last_analysis"],
            "summary": summary,
        }
        await _queue_analysis_update(summary)

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
        logger.error(
            "FHIR connector error during analysis [%s]: %s", correlation_id, exc.message
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
    except HTTPException as exc:
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(exc.detail),
                event_type="analyze",
            )
        raise
    except Exception as e:
        logger.error(f"Error analyzing patient [%s]: %s", correlation_id, str(e))
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(e),
                event_type="analyze",
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/patient-updates")
async def patient_updates(websocket: WebSocket):
    """Provide real-time dashboard updates via WebSocket."""

    token_context = await _authenticate_websocket(websocket)

    await websocket.accept()
    active_websockets[websocket] = token_context

    try:
        while True:
            # Keep the connection alive by waiting for client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        active_websockets.pop(websocket, None)


@app.get("/api/v1/dashboard-summary")
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
):
    """Return a cached dashboard summary for multiple patients."""

    if not patient_analyzer:
        raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

    # If no explicit patient list is provided, use the most recent analyses
    if not patient_ids:
        seen: set = set()
        patient_ids = []
        for analysis in reversed(patient_analyzer.analysis_history):
            pid = analysis.get("patient_id")
            if pid and pid not in seen:
                seen.add(pid)
                patient_ids.append(pid)

    if not patient_ids:
        return []

    summaries = []
    for patient_id in patient_ids:
        summary = await _get_patient_summary(patient_id, auth)
        summaries.append(summary)

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

    correlation_id = getattr(request.state, "correlation_id", "")
    logger.info(
        "Returned dashboard summary for %s patients",
        len(summaries),
        extra={"correlation_id": correlation_id},
    )

    return summaries


@app.get("/api/v1/patient/{patient_id}/fhir")
async def get_patient_fhir(
    request: Request,
    patient_id: str,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """
    Fetch patient's FHIR data from connected EHR
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not fhir_connector:
            raise HTTPException(status_code=503, detail="FHIR connector not initialized")

        if auth.patient and auth.patient != patient_id:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a different patient context",
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
        if audit_service:
            await audit_service.record_event(
                action="R",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=exc.message,
                event_type="read",
            )
        error_payload = {
            "status": "error",
            "error_type": exc.error_type,
            "message": exc.message,
            "correlation_id": exc.correlation_id or correlation_id,
        }
        return JSONResponse(status_code=502, content=error_payload)
    except HTTPException as exc:
        if audit_service:
            await audit_service.record_event(
                action="R",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(exc.detail),
                event_type="read",
            )
        raise
    except Exception as e:
        logger.error(
            "Error fetching patient FHIR data [%s]: %s", correlation_id, str(e)
        )
        if audit_service:
            await audit_service.record_event(
                action="R",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(e),
                event_type="read",
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/patient/{patient_id}/explain")
@app.get("/api/v1/explain/{patient_id}")
async def explain_patient_risk(
    request: Request,
    patient_id: str,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """
    Generate SHAP explanations for a patient's baseline risk model.

    1. Run PatientAnalyzer.analyze(patient_id)
    2. Extract features and build model inputs
    3. Compute SHAP values
    4. Return the explanations with feature names
    """

    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not patient_analyzer:
            raise HTTPException(status_code=503, detail="Patient analyzer not initialized")

        if auth.patient and auth.patient != patient_id:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a different patient context",
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
    except HTTPException as exc:
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(exc.detail),
                event_type="explain",
            )
        raise
    except Exception as e:
        logger.error(
            "Error generating SHAP explanations [%s]: %s", correlation_id, str(e)
        )
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(e),
                event_type="explain",
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query")
async def medical_query(
    request: Request,
    question: str,
    patient_id: Optional[str] = None,
    include_reasoning: bool = True
):
    """
    Query the AI for medical insights and recommendations
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not llm_engine or not rag_fusion:
            raise HTTPException(status_code=503, detail="AI engine not initialized")
        
        logger.info(f"Processing medical query: {question}")
        
        # Get patient context if provided
        patient_context = None
        if patient_id:
            patient_context = await fhir_connector.get_patient(patient_id)
        
        # Generate response with RAG and AoT
        response = await llm_engine.query_with_rag(
            question=question,
            patient_context=patient_context,
            rag_component=rag_fusion,
            aot_reasoner=aot_reasoner,
            include_reasoning=include_reasoning
        )
        
        result = {
            "status": "success",
            "question": question,
            "answer": response.get("answer"),
            "reasoning": response.get("reasoning") if include_reasoning else None,
            "sources": response.get("sources"),
            "confidence": response.get("confidence")
        }

        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Medical query processed",
                event_type="question",
            )

        return result

    except HTTPException as exc:
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(exc.detail),
                event_type="question",
            )
        raise
    except Exception as e:
        logger.error("Error processing query [%s]: %s", correlation_id, str(e))
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=patient_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(e),
                event_type="question",
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/feedback")
async def provide_feedback(
    request: Request,
    query_id: str,
    feedback_type: str,  # "positive", "negative", "correction"
    corrected_text: Optional[str] = None
):
    """
    Provide feedback for MLC (Meta-Learning for Compositionality) adaptation
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not mlc_learning:
            raise HTTPException(status_code=503, detail="MLC learning system not initialized")
        
        logger.info(f"Receiving feedback for query {query_id}: {feedback_type}")
        
        await mlc_learning.process_feedback(
            query_id=query_id,
            feedback_type=feedback_type,
            corrected_text=corrected_text
        )
        
        return {
            "status": "success",
            "message": "Feedback processed and learning model updated",
            "query_id": query_id
        }
        
    except Exception as e:
        logger.error("Error processing feedback [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/adapters")
async def get_adapters_status(request: Request):
    """
    Get S-LoRA adapter status and memory usage
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not s_lora_manager:
            raise HTTPException(status_code=503, detail="S-LoRA manager not initialized")
        
        status = await s_lora_manager.get_status()
        
        return {
            "status": "success",
            "active_adapters": status.get("active"),
            "available_adapters": status.get("available"),
            "memory_usage": status.get("memory"),
            "specialties": status.get("specialties")
        }
        
    except Exception as e:
        logger.error("Error fetching adapter status [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/adapters/activate")
async def activate_adapter(
    request: Request, adapter_name: str, specialty: Optional[str] = None
):
    """
    Activate a specific LoRA adapter for a specialty
    """
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not s_lora_manager:
            raise HTTPException(status_code=503, detail="S-LoRA manager not initialized")
        
        result = await s_lora_manager.activate_adapter(adapter_name, specialty)
        
        return {
            "status": "success",
            "adapter": adapter_name,
            "active": result
        }
        
    except Exception as e:
        logger.error("Error activating adapter [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def get_system_stats(request: Request):
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
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error("Error fetching stats [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ERROR HANDLERS ====================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler
    """
    correlation_id = getattr(request.state, "correlation_id", uuid.uuid4().hex)
    logger.error("Unhandled exception [%s]: %s", correlation_id, str(exc))
    payload = {
        "status": "error",
        "message": "An unexpected error occurred",
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return JSONResponse(status_code=500, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", uuid.uuid4().hex)
    logger.error("HTTPException [%s]: %s", correlation_id, exc.detail)

    payload = {
        "status": "error",
        "message": exc.detail if exc.detail else "Request failed",
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if exc.status_code in {401, 403}:
        payload["hint"] = "Please re-authenticate and try again."

    return JSONResponse(status_code=exc.status_code, content=payload)


# ==================== MAIN ====================

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting Healthcare AI Assistant on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )

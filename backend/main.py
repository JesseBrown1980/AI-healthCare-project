"""
Healthcare AI Assistant - Main Application Entry Point
Integrates FHIR data with advanced AI techniques (S-LoRA, MLC, RAG, AoT)
"""

# Ensure project root is in sys.path for imports to work when running directly
import sys
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Load environment variables
import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
from contextlib import asynccontextmanager

from datetime import datetime, timezone
import logging

import uuid
from typing import Any, Dict, Optional

import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from backend.middleware import (
    RateLimitMiddleware,
    TimeoutMiddleware,
    SecurityHeadersMiddleware,
)
from backend.anomaly_detector.api import router as anomaly_router
from backend.anomaly_detector.service import anomaly_service
# python-jose implementation used for JWT encoding/decoding
from jose import jwt
from backend.analysis_cache import AnalysisJobManager
from backend.audit_service import AuditService
from backend.database import init_database, close_database, DatabaseService
from backend.di import (
    ServiceContainer,
    get_container,
)
from backend.security import auth_dependency, close_shared_async_client
from backend.api.v1.api import api_router as v1_router


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
container: Optional[ServiceContainer] = None
notifications_enabled: bool = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
demo_login_enabled: bool = os.getenv("ENABLE_DEMO_LOGIN", "false").lower() == "true"
demo_login_secret: str = os.getenv("DEMO_JWT_SECRET", "dev-secret-change-me")
demo_login_expires_minutes: int = int(os.getenv("DEMO_JWT_EXPIRES", "15"))
analysis_history_limit: int = int(os.getenv("ANALYSIS_HISTORY_LIMIT", "200"))
analysis_history_ttl_seconds: int = int(
    os.getenv("ANALYSIS_HISTORY_TTL_SECONDS", str(60 * 60 * 24))
)
analysis_cache_ttl_seconds: int = int(os.getenv("ANALYSIS_CACHE_TTL_SECONDS", "300"))
analysis_job_manager: Optional[AnalysisJobManager] = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management - startup and shutdown
    """
    # Startup
    logger.info("Initializing Healthcare AI Assistant...")
    try:
        global fhir_client, fhir_connector, llm_engine, rag_fusion, s_lora_manager, mlc_learning, aot_reasoner, patient_analyzer
        global audit_service, notifier, analysis_job_manager, container

        if analysis_history_limit <= 0:
            raise ValueError("ANALYSIS_HISTORY_LIMIT must be a positive integer")

        container = ServiceContainer(
            notifications_enabled=notifications_enabled,
            analysis_history_limit=analysis_history_limit,
            analysis_history_ttl_seconds=analysis_history_ttl_seconds,
            analysis_cache_ttl_seconds=analysis_cache_ttl_seconds,
        )
        await container.startup()
        app.state.container = container

        fhir_client = container.fhir_client
        fhir_connector = container.fhir_connector
        llm_engine = container.llm_engine
        rag_fusion = container.rag_fusion
        s_lora_manager = container.s_lora_manager
        mlc_learning = container.mlc_learning
        aot_reasoner = container.aot_reasoner
        patient_analyzer = container.patient_analyzer
        notifier = container.notifier
        audit_service = container.audit_service
        analysis_job_manager = container.analysis_job_manager

        # Initialize real-time update infrastructure
        if container.analysis_update_queue is None:
            container.analysis_update_queue = asyncio.Queue()
        if container.active_websockets is None:
            container.active_websockets = {}
        container.broadcast_task = asyncio.create_task(
            _broadcast_analysis_updates(container)
        )

        # Initialize Database
        logger.info("Initializing Database...")
        await init_database()
        db_service = DatabaseService()
        app.state.db_service = db_service
        logger.info("✓ Database initialized successfully")
        
        # Initialize Anomaly Detector
        logger.info("Initializing Anomaly Detector...")
        anomaly_service.initialize()
        app.state.model = anomaly_service.get_model()
        logger.info(f"✓ Anomaly Detector initialized with {anomaly_service.get_model_info()['model_type'].upper()} model")
        
        # Update PatientAnalyzer and AuditService to use database service (if available)
        if container.patient_analyzer and db_service:
            container.patient_analyzer.database_service = db_service
            logger.info("✓ PatientAnalyzer updated to use database service")
        
        if container.audit_service and db_service:
            container.audit_service.database_service = db_service
            logger.info("✓ AuditService updated to use database service")
        
        # Update PatientAnalyzer to use anomaly service (if available)
        if container.patient_analyzer and anomaly_service:
            container.patient_analyzer.anomaly_service = anomaly_service
            logger.info("✓ PatientAnalyzer updated to use GNN anomaly detection")

        logger.info("✓ Healthcare AI Assistant initialized successfully")

    except Exception as e:
        logger.error(f"Initialization error: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Healthcare AI Assistant...")
    # Add cleanup code here if needed
    if container and container.broadcast_task:
        container.broadcast_task.cancel()
        try:
            await container.broadcast_task
        except asyncio.CancelledError:
            pass

    if container and container.active_websockets is not None:
        for websocket in list(container.active_websockets.keys()):
            try:
                await websocket.close(code=1001)
            except Exception:
                pass
        container.active_websockets.clear()

    if container:
        await container.shutdown()
    else:
        await close_shared_async_client()
    
    # Close database connections
    await close_database()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Healthcare AI Assistant",
    description="AI-powered healthcare application with FHIR integration",
    version="1.0.0",
    lifespan=lifespan,
    # Request size limits (10MB default, 50MB for file uploads)
    max_request_size=int(os.getenv("MAX_REQUEST_SIZE", 10 * 1024 * 1024)),  # 10MB
)

# Register Modular V1 Router (includes Patients, Clinical, Auth, System)
app.include_router(v1_router, prefix="/api/v1")

# Register Anomaly Detector Router (keep as separate or could be included in v1)
app.include_router(anomaly_router, prefix="/api/v1/anomaly", tags=["Anomaly Detection"])

# Add security headers middleware (first, so it applies to all responses)
app.add_middleware(
    SecurityHeadersMiddleware,
    enabled=os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true",
    strict_transport_security=os.getenv("HSTS_ENABLED", "true").lower() == "true",
)

# Add timeout middleware
app.add_middleware(
    TimeoutMiddleware,
    timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30.0")),
    enabled=os.getenv("TIMEOUT_MIDDLEWARE_ENABLED", "true").lower() == "true",
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
    burst_size=int(os.getenv("RATE_LIMIT_BURST", "10")),
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
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
    container = getattr(getattr(request.app, "state", None), "container", None)
    audit_service = getattr(container, "audit_service", None) if container else None

    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = (
            audit_service.new_correlation_id() if audit_service else uuid.uuid4().hex
        )
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Endpoints migrated to api/v1/endpoints/



# ==================== API ENDPOINTS ====================

# ==================== HELPERS ====================

def get_vendor_override(request: Request, default: str = "generic") -> str:
    """Resolve vendor preference from query parameters or a default value."""

    vendor_param = request.query_params.get("vendor")
    if vendor_param:
        return vendor_param.lower()
    return default


async def _broadcast_analysis_updates(app_container: ServiceContainer) -> None:
    """Broadcast queued analysis updates to all connected WebSocket clients."""

    if not app_container.analysis_update_queue or app_container.active_websockets is None:
        return

    try:
        while True:
            update = await app_container.analysis_update_queue.get()
            stale_connections = []

            update_patient_id = None
            if isinstance(update, dict):
                data = update.get("data") or {}
                update_patient_id = data.get("patient_id") or update.get("patient_id")

            for websocket, token_context in list(app_container.active_websockets.items()):
                if (
                    update_patient_id
                    and token_context.patient
                    and token_context.patient != update_patient_id
                ):
                    continue
                try:
                    await websocket.send_json(update)
                except Exception:
                    stale_connections.append(websocket)

            for websocket in stale_connections:
                try:
                    app_container.active_websockets.pop(websocket, None)
                except KeyError:
                    pass
    except asyncio.CancelledError:
        pass


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


async def _authenticate_websocket(websocket: WebSocket) -> Any:
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


@app.get("/health", include_in_schema=False)
async def root_health():
    """
    Lightweight health check for container orchestration.
    """
    return {
        "status": "healthy",
        "service": "Healthcare AI Assistant",
        "version": "1.0.0",
        "vendor": "generic",
    }


@app.websocket("/ws/patient-updates")
async def patient_updates(websocket: WebSocket):
    """Provide real-time dashboard updates via WebSocket."""

    app_container = getattr(getattr(websocket.app, "state", None), "container", None)
    if not app_container or app_container.active_websockets is None:
        await websocket.close(code=1011, reason="Service unavailable")
        return

    token_context = await _authenticate_websocket(websocket)

    await websocket.accept()
    app_container.active_websockets[websocket] = token_context

    try:
        while True:
            # Keep the connection alive by waiting for client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if app_container.active_websockets is not None:
            app_container.active_websockets.pop(websocket, None)


# ==================== ERROR HANDLERS ====================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    Provides consistent error response format and logging.
    """
    correlation_id = getattr(request.state, "correlation_id", uuid.uuid4().hex)
    
    # Log with full traceback for debugging
    logger.error(
        "Unhandled exception [%s] at %s %s: %s",
        correlation_id,
        request.method,
        request.url.path,
        str(exc),
        exc_info=True
    )
    
    # Determine error message based on environment
    is_debug = os.getenv("DEBUG", "False").lower() == "true"
    error_message = "An unexpected error occurred"
    error_detail = None
    
    if is_debug:
        error_message = f"Internal server error: {type(exc).__name__}"
        error_detail = str(exc)
    
    payload = {
        "status": "error",
        "message": error_message,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": str(request.url.path),
    }
    
    if error_detail:
        payload["detail"] = error_detail
    
    return JSONResponse(status_code=500, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP exception handler for FastAPI HTTPException.
    Provides consistent error response format with helpful hints.
    """
    correlation_id = getattr(request.state, "correlation_id", uuid.uuid4().hex)
    
    # Log based on status code severity
    if exc.status_code >= 500:
        logger.error("HTTPException [%s] %s: %s", correlation_id, exc.status_code, exc.detail)
    elif exc.status_code >= 400:
        logger.warning("HTTPException [%s] %s: %s", correlation_id, exc.status_code, exc.detail)
    else:
        logger.info("HTTPException [%s] %s: %s", correlation_id, exc.status_code, exc.detail)

    payload = {
        "status": "error",
        "message": exc.detail if exc.detail else "Request failed",
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": exc.status_code,
    }

    # Add helpful hints based on error type
    if exc.status_code == 401:
        payload["hint"] = "Please authenticate and try again. Check your access token."
    elif exc.status_code == 403:
        payload["hint"] = "You don't have permission to access this resource. Check your roles and scopes."
    elif exc.status_code == 404:
        payload["hint"] = "The requested resource was not found. Check the URL and resource ID."
    elif exc.status_code == 422:
        payload["hint"] = "Request validation failed. Check your input parameters."
    elif exc.status_code == 429:
        payload["hint"] = "Rate limit exceeded. Please try again later."
    elif exc.status_code == 503:
        payload["hint"] = "Service temporarily unavailable. Please try again in a moment."

    return JSONResponse(status_code=exc.status_code, content=payload)


# ==================== MAIN ====================

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting Healthcare AI Assistant on {host}:{port}")
    
    # Check if running as Windows executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - disable reload
        reload_mode = False
    else:
        reload_mode = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload_mode
    )

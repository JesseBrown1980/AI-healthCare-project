from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from .config import settings
from .api import router as api_router
from .exceptions import AnomalyDetectionError

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    try:
        from .service import anomaly_service
        anomaly_service.initialize()
        app.state.model = anomaly_service.get_model()
        app.state.is_loaded = True
        settings.logger.info("Model lifecycle initialized and bound to app state.")
    except Exception as e:
        settings.logger.critical(f"Critical failure during service startup: {e}")
        app.state.is_loaded = False
        
    yield
    settings.logger.info(f"Shutting down {settings.PROJECT_NAME}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    """
    Health check endpoint.
    Returns 503 if the model is not fully initialized.
    """
    if not getattr(app.state, "is_loaded", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is initializing. Model not loaded yet."
        )
    return {"status": "ready", "version": settings.VERSION}

@app.get("/")
async def root():
    return {"message": "Anomaly Detection Service is running"}

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR, tags=["anomaly-detection"])

@app.exception_handler(AnomalyDetectionError)
async def anomaly_detection_exception_handler(request: Request, exc: AnomalyDetectionError):
    settings.logger.error(f"Domain Error: {exc.message} | Detail: {exc.detail}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "AnomalyDetectionError",
            "message": exc.message,
            "detail": exc.detail
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    settings.logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred in the security processing pipeline."
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from .config import settings
from .models.gnn_baseline import EdgeLevelGNN
from .api import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Model using Singleton Service
    print("Initializing Anomaly Detection Model...")
    try:
        from .service import anomaly_service
        anomaly_service.initialize()
        # Bind the model from service to app state for easy access in API
        app.state.model = anomaly_service.get_model()
        app.state.is_loaded = True
        print("Model initialized and bound to app state.")
    except Exception as e:
        print(f"Failed to initialize model: {e}")
        app.state.is_loaded = False
        
    yield
    print("Shutting down Anomaly Detection Service...")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


# Integration Instructions: backend/main.py

Since the `backend/main.py` file contains complex existing logic, please manually add the following lines to integrate the Anomaly Detector.

### 1. Add Import
Add this line near the top of the file with other imports:
```python
from backend.anomaly_detector.api import router as anomaly_router
```

### 2. Include Router
Add this line where the FastAPI app is initialized (usually near the bottom, after `app = FastAPI(...)`):

```python
# ... existing code ...
app = FastAPI(title="AI Healthcare Assistant", ...)

# [NEW] Register Anomaly Detector Router
app.include_router(anomaly_router, prefix="/api/v1/anomaly", tags=["Anomaly Detection"])

# ... existing code ...
```

This will expose the endpoint at `http://localhost:8000/api/v1/anomaly/score` (proxied if using the main backend as a gateway) or you can access it directly via the microservice port 8001.

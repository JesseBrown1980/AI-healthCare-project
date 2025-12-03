
from fastapi.testclient import TestClient
from backend.anomaly_detector.main import app
from datetime import datetime, timezone

client = TestClient(app)

# Mock model and loaded state to bypass lifespan/dependency issues
from unittest.mock import MagicMock
app.state.model = MagicMock()
app.state.model.eval = MagicMock()
app.state.model.__call__ = MagicMock(return_value=MagicMock(tolist=lambda: [0.5, 0.5], ndim=1))
# Mock get_edge_importance if needed by API for GSL
app.state.model.get_edge_importance = MagicMock(return_value=MagicMock(tolist=lambda: [0.1, 0.1])) 
app.state.is_loaded = True


def test_health_check():
    response = client.get("/security/anomaly/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

from unittest.mock import patch

@patch("backend.anomaly_detector.api.anomaly_service")
def test_score_events_flow(mock_algo_service):
    mock_algo_service.get_model_info.return_value = {"model_type": "baseline"}

    # 1. Define mock batch
    payload = {
        "events": [
            {
                "event_id": "event_01",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_entity": "user_1",
                "destination_entity": "resource_A",
                "action": "READ"
            },
            {
                "event_id": "event_02",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_entity": "user_2",
                "destination_entity": "resource_A",
                "action": "WRITE"
            }
        ]
    }
    
    # 2. Call API
    response = client.post("/security/anomaly/score", json=payload)
    
    # 3. Validation
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert "anomaly_score" in data["results"][0]
    assert isinstance(data["results"][0]["anomaly_score"], float)
    # print("Integration test passed: API returned scores for batch.")

if __name__ == "__main__":
    # If run directly, simple manual check
    try:
        test_health_check()
        test_score_events_flow()
        # print("All tests passed.")
    except ImportError:
        # print("Skipping tests: Dependencies missing in this environment.")
        pass

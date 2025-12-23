
from fastapi.testclient import TestClient
from backend.anomaly_detector.main import app
from datetime import datetime

client = TestClient(app)

def test_health_check():
    response = client.get("/security/anomaly/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_score_events_flow():
    # 1. Define mock batch
    payload = {
        "events": [
            {
                "event_id": "e1",
                "timestamp": datetime.utcnow().isoformat(),
                "source_entity": "user_1",
                "destination_entity": "resource_A",
                "action": "READ"
            },
            {
                "event_id": "e2",
                "timestamp": datetime.utcnow().isoformat(),
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
    print("Integration test passed: API returned scores for batch.")

if __name__ == "__main__":
    # If run directly, simple manual check
    try:
        test_health_check()
        test_score_events_flow()
        print("All tests passed.")
    except ImportError:
        print("Skipping tests: Dependencies missing in this environment.")

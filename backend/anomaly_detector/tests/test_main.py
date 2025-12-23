import unittest
from fastapi.testclient import TestClient
from datetime import datetime
from ..main import app

class TestAnomalyService(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        # Since TestClient runs lifespan, the model should be initialized and return 200
        response = self.client.get("/security/anomaly/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_score_endpoint(self):
        # Mock payload
        payload = {
            "events": [
                {
                    "event_id": "evt_1",
                    "timestamp": datetime.now().isoformat(),
                    "source_entity": "user_123",
                    "destination_entity": "patient_555",
                    "action": "READ",
                    "metadata": {}
                },
                {
                    "event_id": "evt_2",
                    "timestamp": datetime.now().isoformat(),
                    "source_entity": "ip_10.0.0.1",
                    "destination_entity": "endpoint_login",
                    "action": "POST",
                    "metadata": {}
                }
            ]
        }
        
        response = self.client.post("/security/anomaly/score", json=payload)
        
        # We expect a success
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        
        # Check structure of first result
        res1 = data["results"][0]
        self.assertEqual(res1["event_id"], "evt_1")
        self.assertIsInstance(res1["anomaly_score"], float)
        self.assertIn("is_anomaly", res1)

if __name__ == "__main__":
    unittest.main()

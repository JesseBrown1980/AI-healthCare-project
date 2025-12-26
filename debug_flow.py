import requests
import os

BASE_URL = "http://localhost:8000"

def test_flow():
    # 1. Login to get token
    print("1. Logging in...")
    login_url = f"{BASE_URL}/api/v1/auth/login"
    # Using generic demo credentials if available or relying on the demo login endpoint 
    # Check if we need to use the specific demo credentials from main.py or if there's a demo mode
    # Assuming standard /auth/login with form data or json
    
    # Based on main.py, there is a DemoLoginRequest model
    login_payload = {
        "email": "demo@example.com",
        "password": "demo", 
        "patient": "patient-12345"
    }
    
    try:
        resp = requests.post(login_url, json=login_payload)
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} - {resp.text}")
            # Try form data if JSON fails (OAuth2PasswordRequestForm often used)
            # But api/v1/endpoints/auth.py likely uses JSON based on DemoLoginRequest
            return
            
        data = resp.json()
        token = data.get("access_token")
        print(f"   Success! Token: {token[:10]}...")
    except Exception as e:
        print(f"Login error: {e}")
        return

    # 2. Call Analyze Patient
    print("\n2. Calling /analyze-patient...")
    analyze_url = f"{BASE_URL}/api/v1/analyze-patient"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    analyze_payload = {
        "fhir_patient_id": "patient-12345",
        "include_recommendations": True,
        "specialty": "cardiology"
    }
    
    try:
        resp = requests.post(analyze_url, headers=headers, json=analyze_payload)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            res = resp.json()
            print(f"   Analysis Status: {res.get('status')}")
            print(f"   Patient: {res.get('patient_id')}")
        else:
            print(f"   Failed: {resp.text}")
            
    except Exception as e:
        print(f"Analyze error: {e}")

    # 3. Call Anomaly Score
    print("\n3. Calling /anomaly/score...")
    anomaly_url = f"{BASE_URL}/api/v1/anomaly/score"
    anomaly_payload = {
        "events": [
            {"id": "evt1", "source": "api", "target": "db", "timestamp": "2023-01-01T12:00:00Z", "action": "read"}
        ]
    }
    
    try:
        resp = requests.post(anomaly_url, headers=headers, json=anomaly_payload)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"   Score: {resp.json().get('results')[0].get('anomaly_score')}")
        else:
            print(f"   Failed: {resp.text}")

    except Exception as e:
        print(f"Anomaly error: {e}")

if __name__ == "__main__":
    test_flow()

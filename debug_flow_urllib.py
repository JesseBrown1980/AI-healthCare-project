import urllib.request
import urllib.error
import json
import os

BASE_URL = "http://localhost:8000"

def run_test():
    print("Running diagnostics...")
    
    # 1. Login
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_payload = {
        "email": "demo@example.com",
        "password": "demo", 
        "patient": "patient-12345"
    }
    
    try:
        req = urllib.request.Request(
            login_url, 
            data=json.dumps(login_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        print(f"1. POST {login_url}")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            token = data.get("access_token")
            print("   Login SUCCESS. Token received.")
    except urllib.error.HTTPError as e:
        print(f"   Login FAILED: {e.code} {e.read().decode()}")
        return
    except Exception as e:
        print(f"   Login ERROR: {e}")
        return

    # 2. Analyze Patient
    analyze_url = f"{BASE_URL}/api/v1/analyze-patient"
    analyze_payload = {
        "fhir_patient_id": "patient-12345",
        "include_recommendations": True,
        "specialty": "cardiology"
    }
    
    try:
        req = urllib.request.Request(
            analyze_url,
            data=json.dumps(analyze_payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        print(f"\n2. POST {analyze_url}")
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            print(f"   Analysis SUCCESS. Status: {res.get('status')}")
    except urllib.error.HTTPError as e:
        print(f"   Analysis FAILED: {e.code} {e.read().decode()}")
    except Exception as e:
        print(f"   Analysis ERROR: {e}")

if __name__ == "__main__":
    run_test()

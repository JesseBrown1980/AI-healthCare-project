
import requests
import json

API_URL = "http://localhost:8000/api/v1/analyze-patient"

# Case 1: Minimal valid request
payload_1 = {
    "fhir_patient_id": "demo-patient-1",
    "notify": True
}

try:
    print(f"Testing {API_URL} with payload: {payload_1}")
    response = requests.post(API_URL, json=payload_1)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")

# Case 2: Request with patient_id (alias) which might trigger attr error
payload_2 = {
    "patient_id": "demo-patient-1",
    "notify": True
}

try:
    print(f"\nTesting {API_URL} with payload: {payload_2}")
    response = requests.post(API_URL, json=payload_2)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")

import pytest
import os
import json
from fastapi.testclient import TestClient

# Set environment variables BEFORE importing app to influence middleware init if possible
os.environ["INPUT_VALIDATION_STRICT"] = "true"
os.environ["SECURITY_HEADERS_ENABLED"] = "true"
os.environ["ENABLE_CSP"] = "true"

from backend.main import app
from backend.di import ServiceContainer

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Ensure environment is set for all tests."""
    monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("INPUT_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("INPUT_VALIDATION_STRICT", "true")
    
    # Manually ensure container exists in app state to avoid 503s
    if not hasattr(app.state, "container") or app.state.container is None:
        app.state.container = ServiceContainer(
            notifications_enabled=False,
            analysis_history_limit=10,
            analysis_history_ttl_seconds=3600,
            analysis_cache_ttl_seconds=3600
        )

@pytest.fixture
def client():
    """Fixture for TestClient with lifespan."""
    with TestClient(app) as c:
        yield c

def test_security_headers_present(client):
    """Verify security headers are present in responses."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers

def test_csp_restricts_unsafe_inline_in_prod(monkeypatch):
    """Verify CSP removes unsafe-inline when ENVIRONMENT=production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENABLE_CSP", "true")
    
    # We must recreate the client to pick up the new environment state in middleare dispatch if cached
    with TestClient(app) as prod_client:
        response = prod_client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")
        # Production CSP should not have unsafe-inline
        assert "'unsafe-inline'" not in csp
        assert "script-src 'self'" in csp

def test_xss_detection_in_query_strict(client):
    """Verify XSS patterns in query parameters are detected."""
    response = client.get("/api/v1/patients?name=<script>alert('xss')</script>")
    # If strict mode is working, this should be 400
    assert response.status_code == 400
    assert "Malicious patterns" in response.json()["message"] or "Invalid characters" in response.json()["message"]

def test_sql_injection_detection_in_body_strict(client):
    """Verify SQL injection patterns in request body are detected."""
    payload = {
        "fhir_patient_id": "123' OR '1'='1",
        "specialty": "cardiology"
    }
    response = client.post("/api/v1/analyze-patient", json=payload)
    assert response.status_code == 400
    assert "Malicious patterns" in response.json()["message"]

def test_request_body_buffering(client):
    """Verify that despite middleware reading the body, the app can still read it."""
    payload = {
        "fhir_patient_id": "test-patient-id",
        "specialty": "cardiology"
    }
    # This matches a clean request. Middleware will buffer and re-wrap.
    response = client.post("/api/v1/analyze-patient", json=payload)
    
    # If it reached the app (even if it returns 401 or something else), it's NOT a 400 or 500
    # A 503 is technically fine too as it means it hit the (unstarted) container in deps
    assert response.status_code not in (400, 500)
    # The presence of a JSON response usually means it got through the middleware
    assert response.headers["content-type"] == "application/json"

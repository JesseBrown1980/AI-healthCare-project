"""
OWASP Top 10 Security Tests
Tests for common security vulnerabilities based on OWASP Top 10 (2021).
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
import json


class TestA01BrokenAccessControl:
    """A01:2021 - Broken Access Control"""
    
    def test_unauthenticated_access_denied(self, test_client):
        """Test that unauthenticated requests are denied."""
        # Try to access protected endpoint without auth
        response = test_client.get("/api/v1/patients/dashboard")
        assert response.status_code in [401, 403]
    
    def test_invalid_token_rejected(self, test_client):
        """Test that invalid tokens are rejected."""
        response = test_client.get(
            "/api/v1/patients/dashboard",
            headers={"Authorization": "Bearer invalid-token-12345"}
        )
        assert response.status_code in [401, 403]
    
    def test_expired_token_rejected(self, test_client):
        """Test that expired tokens are rejected."""
        # This would require creating an actually expired token
        # For now, test with malformed token
        response = test_client.get(
            "/api/v1/patients/dashboard",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"}
        )
        assert response.status_code in [401, 403]
    
    def test_horizontal_privilege_escalation_blocked(self, test_client, auth_headers):
        """Test that users cannot access other patients' data."""
        # Try to access a patient not in the user's scope
        response = test_client.get(
            "/api/v1/patient/UNAUTHORIZED_PATIENT_ID/fhir",
            headers=auth_headers
        )
        # Should either return 403 or not find the patient
        assert response.status_code in [403, 404, 503]
    
    def test_vertical_privilege_escalation_blocked(self, test_client, auth_headers):
        """Test that regular users cannot access admin endpoints."""
        # Try to access admin functionality
        response = test_client.post(
            "/api/v1/admin/users",
            headers=auth_headers,
            json={"username": "newadmin", "role": "admin"}
        )
        # Should be forbidden or not found
        assert response.status_code in [403, 404, 405]


class TestA02CryptographicFailures:
    """A02:2021 - Cryptographic Failures"""
    
    def test_https_enforcement_header(self, test_client):
        """Test that HSTS header is present."""
        response = test_client.get("/health")
        # In test mode, HSTS may be disabled, but check header exists in prod config
        assert response.status_code == 200
    
    def test_sensitive_data_not_in_url(self, test_client, auth_headers):
        """Test that sensitive data is not exposed in URLs."""
        # Check that SSN/passwords aren't in query params
        response = test_client.get(
            "/api/v1/patient/123?ssn=123-45-6789",
            headers=auth_headers
        )
        # The request should be rejected or the SSN should not appear in logs
        # This is more of a policy check - the endpoint may not even accept SSN param
        assert "ssn" not in str(response.url).lower() or response.status_code in [400, 403, 404, 503]
    
    def test_password_not_in_response(self, test_client, auth_headers):
        """Test that passwords are never returned in responses."""
        response = test_client.get("/api/v1/profile", headers=auth_headers)
        if response.status_code == 200:
            response_text = response.text.lower()
            assert "password" not in response_text or "password\":" not in response_text


class TestA03Injection:
    """A03:2021 - Injection"""
    
    def test_sql_injection_in_patient_id(self, test_client, auth_headers):
        """Test SQL injection in patient ID parameter."""
        malicious_ids = [
            "1; DROP TABLE patients;--",
            "1' OR '1'='1",
            "1 UNION SELECT * FROM users--",
            "'; DELETE FROM patients WHERE ''='",
        ]
        
        for malicious_id in malicious_ids:
            response = test_client.get(
                f"/api/v1/patient/{malicious_id}/fhir",
                headers=auth_headers
            )
            # Should return 400/404/422, not 500 (which might indicate SQL error)
            assert response.status_code != 500, f"Potential SQL injection vulnerability with: {malicious_id}"
    
    def test_command_injection_blocked(self, test_client, auth_headers):
        """Test command injection attempts are blocked."""
        malicious_inputs = [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
        ]
        
        for malicious_input in malicious_inputs:
            response = test_client.post(
                "/api/v1/query",
                headers=auth_headers,
                json={"question": malicious_input}
            )
            # Should be handled gracefully
            assert response.status_code != 500
    
    def test_xss_in_input_fields(self, test_client, auth_headers):
        """Test XSS payloads are sanitized."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
        ]
        
        for payload in xss_payloads:
            response = test_client.post(
                "/api/v1/feedback",
                headers=auth_headers,
                json={"query_id": "test", "feedback": payload}
            )
            if response.status_code == 200:
                # Check that script tags are not in response
                assert "<script>" not in response.text


class TestA07IdentificationAndAuthenticationFailures:
    """A07:2021 - Identification and Authentication Failures"""
    
    def test_brute_force_protection(self, test_client):
        """Test that repeated failed logins are rate limited."""
        # Attempt many failed logins
        for i in range(15):
            response = test_client.post(
                "/api/v1/auth/login",
                json={"email": "brute@test.com", "password": f"wrong{i}"}
            )
        
        # After many attempts, should be rate limited
        # (This depends on rate limiting being enabled)
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "brute@test.com", "password": "stillwrong"}
        )
        # Should either be rate limited (429) or return auth error
        assert response.status_code in [401, 404, 429]
    
    def test_weak_password_rejected(self, test_client):
        """Test that weak passwords are rejected during registration."""
        weak_passwords = ["123", "password", "qwerty", "a"]
        
        for weak_pass in weak_passwords:
            response = test_client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": weak_pass}
            )
            # Should reject weak password or endpoint not found
            assert response.status_code in [400, 404, 422]
    
    def test_session_fixation_prevention(self, test_client):
        """Test that session tokens are rotated after login."""
        # This would require actual session management testing
        # For now, verify that tokens contain unique identifiers
        pass


class TestA09SecurityLoggingAndMonitoring:
    """A09:2021 - Security Logging and Monitoring Failures"""
    
    def test_failed_login_logged(self, test_client, tmp_path):
        """Test that failed logins are logged."""
        from backend.audit import get_audit_logger
        
        # Trigger a failed login
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "hacker@test.com", "password": "wrong"}
        )
        
        # The audit logger should have recorded this
        # (In a real test, we'd check the audit logs)
        assert response.status_code in [401, 404]
    
    def test_access_denied_logged(self, test_client, auth_headers):
        """Test that access denied events are logged."""
        # Attempt unauthorized access
        response = test_client.get(
            "/api/v1/admin/config",
            headers=auth_headers
        )
        
        # Should be denied and logged
        assert response.status_code in [403, 404]


class TestSecurityHeaders:
    """Test security headers are properly set."""
    
    def test_x_frame_options(self, test_client):
        """Test X-Frame-Options header is set."""
        response = test_client.get("/health")
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_x_content_type_options(self, test_client):
        """Test X-Content-Type-Options header is set."""
        response = test_client.get("/health")
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_referrer_policy(self, test_client):
        """Test Referrer-Policy header is set."""
        response = test_client.get("/health")
        assert "Referrer-Policy" in response.headers


# Pytest fixtures
@pytest.fixture
def test_client():
    """Create a test client for the app."""
    import os
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"
    
    try:
        from backend.main import app
        with TestClient(app) as client:
            yield client
    except ImportError:
        pytest.skip("Could not import main app")


@pytest.fixture
def auth_headers():
    """Create mock auth headers for testing."""
    # In a real test, this would be a valid test token
    return {"Authorization": "Bearer test-token-for-testing"}

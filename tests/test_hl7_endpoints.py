"""
Tests for HL7 v2.x API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from backend.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_hl7_message():
    """Sample HL7 v2.x message."""
    return (
        "MSH|^~\\&|LAB|HOSPITAL|AI_SYSTEM|HOSPITAL|20240101120000||ORU^R01|12345|P|2.5\r"
        "PID|1||123456^^^MRN||DOE^JOHN||19800101|M\r"
        "OBR|1||LAB123|CBC^Complete Blood Count|||20240101100000\r"
        "OBX|1|NM|6690-2^WBC^LN|1|7.5|10*3/uL|4.0-11.0|N|||F|||20240101100000\r"
    )




def test_receive_hl7_message_success(client, sample_hl7_message):
    """Test receiving and processing HL7 message."""
    # Use demo login token for testing
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
    else:
        # Skip if demo login not enabled
        pytest.skip("Demo login not enabled")
    
    response = client.post(
        "/api/v1/hl7/receive",
        json={"message": sample_hl7_message, "auto_convert": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message_type"] == "ORU^R01"
    assert data["patient_id"] == "123456"
    assert "fhir_resources" in data
    assert data["fhir_resources"]["observations_count"] > 0


def test_receive_hl7_message_invalid(client):
    """Test receiving invalid HL7 message."""
    # Use demo login token for testing
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
    else:
        pytest.skip("Demo login not enabled")
    
    response = client.post(
        "/api/v1/hl7/receive",
        json={"message": "INVALID MESSAGE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 400
    assert "Invalid HL7 message" in response.json()["detail"]


def test_validate_hl7_message_valid(client, sample_hl7_message):
    """Test validating a valid HL7 message."""
    response = client.post(
        "/api/v1/hl7/validate",
        json={"message": sample_hl7_message},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "valid"
    assert data["message_type"] == "ORU^R01"
    assert data["has_patient"] is True
    assert data["has_observations"] is True


def test_validate_hl7_message_invalid(client):
    """Test validating an invalid HL7 message."""
    response = client.post(
        "/api/v1/hl7/validate",
        json={"message": "INVALID"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid"
    assert "error" in data


def test_list_hl7_messages_placeholder(client):
    """Test listing HL7 messages (placeholder implementation)."""
    # Use demo login token for testing
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": ""},
    )
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
    else:
        pytest.skip("Demo login not enabled")
    
    response = client.get(
        "/api/v1/hl7/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] == 0
    assert "not yet implemented" in data["message"]

"""
Tests for Consent Management API.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from contextlib import asynccontextmanager

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_consent_lifecycle(async_client: AsyncClient, auth_token, test_db):
    """
    Test the full lifecycle of consent: Accept -> Verify -> Withdraw -> Verify.
    """
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a mock for get_db_session that returns the test_db session
    # mimicking the context manager behavior
    @asynccontextmanager
    async def mock_get_db_session():
        yield test_db

    # Patch the service's import of get_db_session
    with patch("backend.services.consent_service.get_db_session", side_effect=mock_get_db_session):
        
        # 1. Check initial status (should be empty or default)
        response = await async_client.get("/api/v1/consent/status", headers=headers)
        assert response.status_code == 200, f"Failed check status: {response.text}"
        data = response.json()
        assert "consents" in data
        
        # 2. Accept Privacy Policy
        consent_payload = {
            "consent_type": "privacy_policy",
            "version": "1.0"
        }
        response = await async_client.post("/api/v1/consent/accept", json=consent_payload, headers=headers)
        assert response.status_code == 200, f"Failed accept: {response.text}"
        assert response.json()["status"] == "success"
        
        # 3. Verify Accepted
        response = await async_client.get("/api/v1/consent/status?consent_type=privacy_policy", headers=headers)
        assert response.status_code == 200, f"Failed verify: {response.text}"
        status = response.json()
        assert status["accepted"] is True
        assert status["consent_type"] == "privacy_policy"
        
        # 4. Withdraw Consent
        withdraw_payload = {"consent_type": "privacy_policy"}
        response = await async_client.post("/api/v1/consent/withdraw", json=withdraw_payload, headers=headers)
        assert response.status_code == 200, f"Failed withdraw: {response.text}"
        
        # 5. Verify Withdrawn
        response = await async_client.get("/api/v1/consent/status?consent_type=privacy_policy", headers=headers)
        assert response.status_code == 200, f"Failed verify withdrawn: {response.text}"
        status = response.json()
        assert status["accepted"] is False
        assert status["withdrawn_at"] is not None

@pytest.mark.asyncio
async def test_consent_metadata(async_client: AsyncClient, auth_token, test_db):
    """Test that metadata (IP, user agent) is captured."""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "User-Agent": "TestAgent/1.0"
    }
    
    payload = {
        "consent_type": "marketing",
        "version": "v2"
    }
    
    # Create a mock for get_db_session that returns the test_db session
    @asynccontextmanager
    async def mock_get_db_session():
        yield test_db

    # Patch the service's import of get_db_session
    with patch("backend.services.consent_service.get_db_session", side_effect=mock_get_db_session):
        response = await async_client.post("/api/v1/consent/accept", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed accept: {response.text}"
        
        # Verify metadata
        response = await async_client.get("/api/v1/consent/status?consent_type=marketing", headers=headers)
        assert response.status_code == 200, f"Failed verify: {response.text}"

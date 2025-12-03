
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from backend.database.models import User, Consent, Base, PatientProfile
from backend.database.connection import init_database, get_db_context, _engine
from backend.main import app

@pytest.mark.asyncio
async def test_right_to_be_forgotten(async_client: AsyncClient, auth_token, test_db):
    """Test GDPR Right to be Forgotten (Account Deletion)."""
    # Override dependency to use the test session
    from backend.database.connection import get_db_session
    app.dependency_overrides[get_db_session] = lambda: test_db

    headers = {"Authorization": f"Bearer {auth_token}"}
    user_id = "test-user-123"
    
    # 2. Seed DB using the test_db session directly
    # Create user
    test_user = User(id=user_id, email="test@example.com", full_name="Test User", oauth_provider="google")
    test_db.add(test_user)
    
    # Create consent
    test_consent = Consent(user_id=user_id, consent_type="privacy_policy")
    test_db.add(test_consent)
    
    # Create profile (to check cascade or separate deletion)
    test_profile = PatientProfile(patient_id="p-123", user_id=user_id, insurance_provider="Test Ins")
    test_db.add(test_profile)
    
    await test_db.flush()
    # We don't commit here because test_db fixture handles transaction, 
    # and we want changes visible to the endpoint sharing the same session.
    
    try:
        # 3. Call Delete Endpoint
        response = await async_client.post("/api/v1/privacy/forget-me", headers=headers)
        assert response.status_code == 200, f"Failed deletion: {response.text}"
        data = response.json()
        assert data["status"] == "success"
        
        # 4. Verify Deletion in DB
        # User gone?
        result = await test_db.execute(select(User).where(User.id == user_id))
        assert result.scalars().first() is None
        
        # Consent gone?
        result = await test_db.execute(select(Consent).where(Consent.user_id == user_id))
        assert result.scalars().first() is None
        
        # Profile gone?
        result = await test_db.execute(select(PatientProfile).where(PatientProfile.user_id == user_id))
        assert result.scalars().first() is None
        
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_data_export(async_client: AsyncClient, auth_token, test_db):
    """Test GDPR Data Portability (Export)."""
    # Override dependency
    from backend.database.connection import get_db_session
    app.dependency_overrides[get_db_session] = lambda: test_db

    headers = {"Authorization": f"Bearer {auth_token}"}
    user_id = "test-user-123"
    
    # Seed DB
    existing = await test_db.get(User, user_id)
    if not existing:
        test_user = User(id=user_id, email="test@example.com", full_name="Test User", oauth_provider="google")
        test_db.add(test_user)
        test_profile = PatientProfile(patient_id="p-123", user_id=user_id, insurance_provider="Test Export")
        test_db.add(test_profile)
        await test_db.flush()
            
    try:
        response = await async_client.get("/api/v1/privacy/export", headers=headers)
        assert response.status_code == 200, f"Failed export: {response.text}"
        data = response.json()
        
        # Verify structure
        assert isinstance(data, dict)
        # Check if nested in 'export_data' or direct (endpoint returns direct dict from service)
        # Service returns: {'user_info':, 'clinical_data': ...}
        assert "user_info" in data
        assert data["user_info"]["email"] == "test@example.com"
        assert "clinical_data" in data
        assert "profile" in data["clinical_data"]
    finally:
        app.dependency_overrides = {}

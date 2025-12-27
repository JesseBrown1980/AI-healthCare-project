from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from jose import jwt
import os
import logging
from backend.models import (
    DemoLoginRequest,
    DemoLoginResponse,
    RegisterRequest,
    RegisterResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
)
from backend.auth import hash_password, verify_password, is_password_strong
from backend.di import get_database_service
from backend.database.service import DatabaseService
from backend.database.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


demo_login_enabled: bool = os.getenv("ENABLE_DEMO_LOGIN", "false").lower() == "true"

demo_login_secret = os.getenv("DEMO_LOGIN_SECRET", "demo-secret-key-123")
demo_login_expires_minutes = int(os.getenv("DEMO_LOGIN_EXPIRES_MINS", "60"))

def _issue_demo_token(email: str, patient: Optional[str]) -> DemoLoginResponse:
    """Create a short-lived JWT for demo use when SMART tokens are unavailable."""
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=demo_login_expires_minutes)
    scopes = "patient/*.read user/*.read system/*.read"

    payload = {
        "sub": email,
        "scope": scopes,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "demo-login",
    }

    if patient:
        payload["patient"] = patient

    token = jwt.encode(payload, demo_login_secret, algorithm="HS256")

    return DemoLoginResponse(
        access_token=token,
        expires_in=int((expires_at - issued_at).total_seconds()),
    )

@router.post("/login", response_model=DemoLoginResponse)
async def login(
    payload: DemoLoginRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Authenticate user and issue JWT token.
    
    Supports both database-backed authentication and demo login mode.
    """
    # Try database authentication first if available
    if db_service:
        try:
            user_service = UserService()
            user = await user_service.get_user_by_email(payload.email)
            if user:
                # Verify password
                if not verify_password(payload.password, user['password_hash']):
                    raise HTTPException(status_code=403, detail="Invalid credentials")
                
                # Check if user is active
                if not user.get('is_active', True):
                    raise HTTPException(status_code=403, detail="User account is inactive")
                
                # Update last login
                await user_service.update_user_last_login(user['id'])
                
                # Issue token with user roles
                roles = user.get('roles', ['viewer'])
                scopes = "patient/*.read user/*.read system/*.read"
                if 'admin' in roles:
                    scopes += " patient/*.write user/*.write system/*.write"
                elif 'clinician' in roles:
                    scopes += " patient/*.write"
                
                return _issue_demo_token(payload.email, payload.patient, scopes=scopes)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Database authentication failed: {e}")
            # Fall through to demo login
    
    # Fallback to demo login if database auth fails or is disabled
    if not demo_login_enabled:
        raise HTTPException(status_code=404, detail="Login is disabled")

    allowed_email = os.getenv("DEMO_LOGIN_EMAIL")
    allowed_password = os.getenv("DEMO_LOGIN_PASSWORD")

    if allowed_email and payload.email.lower() != allowed_email.lower():
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if allowed_password and payload.password != allowed_password:
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if not allowed_email and not allowed_password and not payload.password:
        raise HTTPException(status_code=400, detail="Password is required for demo login")

    return _issue_demo_token(payload.email, payload.patient)


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Register a new user account.
    
    Requires database service to be available.
    """
    if not db_service:
        raise HTTPException(
            status_code=503,
            detail="User registration requires database service"
        )
    
    # Validate password strength
    is_strong, error_msg = is_password_strong(payload.password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Hash password
        password_hash = hash_password(payload.password)
        
        # Create user
        user_service = UserService()
        user = await user_service.create_user(
            email=payload.email,
            password_hash=password_hash,
            full_name=payload.full_name,
            roles=payload.roles,
        )
        
        return RegisterResponse(
            id=user['id'],
            email=user['email'],
            full_name=user.get('full_name'),
            roles=user.get('roles', ['viewer']),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")


def _issue_demo_token(email: str, patient: Optional[str], scopes: Optional[str] = None) -> DemoLoginResponse:
    """Create a short-lived JWT for demo use when SMART tokens are unavailable."""
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=demo_login_expires_minutes)
    if scopes is None:
        scopes = "patient/*.read user/*.read system/*.read"

    payload = {
        "sub": email,
        "scope": scopes,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "demo-login",
    }

    if patient:
        payload["patient"] = patient

    token = jwt.encode(payload, demo_login_secret, algorithm="HS256")

    return DemoLoginResponse(
        access_token=token,
        expires_in=int((expires_at - issued_at).total_seconds()),
    )

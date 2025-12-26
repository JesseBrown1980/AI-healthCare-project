from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from jose import jwt
import os
from backend.models import (
    DemoLoginRequest,
    DemoLoginResponse,
)

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
async def demo_login(payload: DemoLoginRequest):
    """
    Issue a short-lived JWT for local development and demos.
    """
    if not demo_login_enabled:
        raise HTTPException(status_code=404, detail="Demo login is disabled")

    allowed_email = os.getenv("DEMO_LOGIN_EMAIL")
    allowed_password = os.getenv("DEMO_LOGIN_PASSWORD")

    if allowed_email and payload.email.lower() != allowed_email.lower():
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if allowed_password and payload.password != allowed_password:
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if not allowed_email and not allowed_password and not payload.password:
        raise HTTPException(status_code=400, detail="Password is required for demo login")

    return _issue_demo_token(payload.email, payload.patient)

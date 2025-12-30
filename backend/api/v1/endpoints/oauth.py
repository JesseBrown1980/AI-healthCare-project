"""
OAuth authentication endpoints (Google, Apple Sign-In)
"""

import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from jose import jwt
import os

from backend.auth.oauth import GoogleOAuthProvider, AppleOAuthProvider, get_oauth_provider
from backend.database.user_service import UserService
from backend.database.service import DatabaseService
from backend.di import get_database_service
from backend.api.v1.endpoints.auth import _issue_demo_token, demo_login_secret, demo_login_expires_minutes

logger = logging.getLogger(__name__)

router = APIRouter()

# Store OAuth states temporarily (in production, use Redis)
_oauth_states: Dict[str, Dict[str, Any]] = {}


def _generate_state() -> str:
    """Generate a random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def _store_state(state: str, provider: str, redirect_after: Optional[str] = None):
    """Store OAuth state temporarily."""
    _oauth_states[state] = {
        "provider": provider,
        "redirect_after": redirect_after,
        "created_at": datetime.now(timezone.utc),
    }


def _verify_state(state: str) -> Optional[Dict[str, Any]]:
    """Verify and retrieve OAuth state."""
    if state not in _oauth_states:
        return None
    
    state_data = _oauth_states[state]
    
    # Clean up old states (older than 10 minutes)
    if (datetime.now(timezone.utc) - state_data["created_at"]).total_seconds() > 600:
        del _oauth_states[state]
        return None
    
    return state_data


def _clear_state(state: str):
    """Clear OAuth state after use."""
    if state in _oauth_states:
        del _oauth_states[state]


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    redirect_after: Optional[str] = Query(None, description="URL to redirect to after login"),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Initiate OAuth flow - redirects user to provider's authorization page.
    
    Supported providers: 'google', 'apple'
    """
    if not db_service:
        raise HTTPException(
            status_code=503,
            detail="OAuth authentication requires database service"
        )
    
    oauth_provider = get_oauth_provider(provider)
    if not oauth_provider:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider: {provider}. Supported: google, apple"
        )
    
    # Generate state for CSRF protection
    state = _generate_state()
    _store_state(state, provider, redirect_after)
    
    # Get authorization URL
    if isinstance(oauth_provider, GoogleOAuthProvider):
        auth_url = oauth_provider.get_authorization_url(state)
    elif isinstance(oauth_provider, AppleOAuthProvider):
        auth_url = oauth_provider.get_authorization_url(state)
    else:
        raise HTTPException(status_code=500, detail="Invalid OAuth provider")
    
    # Redirect to provider
    return RedirectResponse(url=auth_url)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State token for CSRF protection"),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    OAuth callback endpoint - handles provider redirect after authorization.
    
    Exchanges authorization code for tokens and creates/logs in user.
    """
    if not db_service:
        raise HTTPException(
            status_code=503,
            detail="OAuth authentication requires database service"
        )
    
    # Verify state
    state_data = _verify_state(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state token")
    
    if state_data["provider"] != provider:
        raise HTTPException(status_code=400, detail="State provider mismatch")
    
    _clear_state(state)
    
    # Get OAuth provider
    oauth_provider = get_oauth_provider(provider)
    if not oauth_provider:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    try:
        # Exchange code for tokens
        if isinstance(oauth_provider, GoogleOAuthProvider):
            tokens = await oauth_provider.exchange_code_for_tokens(code)
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            
            # Get user info
            user_info = await oauth_provider.get_user_info(access_token)
            provider_user_id = user_info.get("sub")
            email = user_info.get("email")
            full_name = user_info.get("name") or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
            email_verified = user_info.get("verified_email", True)
            
        elif isinstance(oauth_provider, AppleOAuthProvider):
            tokens = await oauth_provider.exchange_code_for_tokens(code)
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            id_token = tokens.get("id_token")
            
            # Get user info from ID token
            user_info = await oauth_provider.get_user_info_from_id_token(id_token)
            provider_user_id = user_info.get("sub")
            email = user_info.get("email")
            full_name = user_info.get("name", "")
            email_verified = user_info.get("email_verified", True)
        else:
            raise HTTPException(status_code=500, detail="Invalid OAuth provider")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by OAuth provider")
        
        # Find or create user
        user_service = UserService()
        user = await user_service.get_user_by_email(email)
        
        if user:
            # Existing user - check if OAuth account is linked
            if user.get("oauth_provider") == provider and user.get("oauth_provider_id") == provider_user_id:
                # Update tokens
                await user_service.update_oauth_tokens(
                    user["id"],
                    provider,
                    provider_user_id,
                    access_token,
                    refresh_token,
                    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                )
            elif user.get("oauth_provider") is None:
                # Link OAuth account to existing password-based account
                await user_service.link_oauth_account(
                    user["id"],
                    provider,
                    provider_user_id,
                    access_token,
                    refresh_token,
                    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                )
            else:
                # OAuth account linked to different provider
                raise HTTPException(
                    status_code=400,
                    detail=f"Email already linked to {user.get('oauth_provider')} account"
                )
        else:
            # New user - create account
            user = await user_service.create_oauth_user(
                email=email,
                full_name=full_name,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                email_verified=email_verified,
            )
        
        # Update last login
        await user_service.update_user_last_login(user["id"])
        
        # Issue JWT token
        roles = user.get("roles", ["viewer"])
        scopes = "patient/*.read user/*.read system/*.read"
        if "admin" in roles:
            scopes += " patient/*.write user/*.write system/*.write"
        elif "clinician" in roles:
            scopes += " patient/*.write"
        
        token_response = _issue_demo_token(email, None, scopes)
        
        # Redirect to frontend with token
        redirect_after = state_data.get("redirect_after", "/")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501")
        
        # In production, use secure cookie or token in URL fragment
        redirect_url = f"{frontend_url}{redirect_after}?token={token_response.access_token}"
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth authentication failed: {str(e)}")


@router.post("/oauth/{provider}/link")
async def link_oauth_account(
    provider: str,
    code: str,
    state: Optional[str] = None,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Link an OAuth account to an existing user account.
    
    Requires the user to be already authenticated.
    """
    # This would require current user context from JWT
    # Implementation depends on your auth middleware
    raise HTTPException(status_code=501, detail="Account linking not yet implemented")


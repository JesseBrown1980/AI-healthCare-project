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
from backend.utils.validation import validate_oauth_provider, validate_email, validate_url
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.security import TokenContext, auth_dependency

logger = logging.getLogger(__name__)

router = APIRouter()

# Store OAuth states temporarily (in production, use Redis)
_oauth_states: Dict[str, Dict[str, Any]] = {}


def _generate_state() -> str:
    """Generate a random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def _store_state(state: str, provider: str, redirect_after: Optional[str] = None) -> None:
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


def _clear_state(state: str) -> None:
    """Clear OAuth state after use."""
    if state in _oauth_states:
        del _oauth_states[state]


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    request: Request,
    provider: str,
    redirect_after: Optional[str] = Query(None, description="URL to redirect to after login"),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Initiate OAuth flow - redirects user to provider's authorization page.
    
    Supported providers: 'google', 'apple'
    """
    correlation_id = get_correlation_id(request)
    
    # Validate provider name
    try:
        provider = validate_oauth_provider(provider)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    if not db_service:
        raise create_http_exception(
            message="OAuth authentication requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate redirect_after URL if provided
    if redirect_after:
        redirect_after = redirect_after.strip()
        try:
            # Use validate_url utility
            redirect_after = validate_url(redirect_after, allowed_schemes=["http", "https"])
            # Additional security: ensure it's same origin
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501")
            if redirect_after.startswith("http://") or redirect_after.startswith("https://"):
                if not redirect_after.startswith(frontend_url):
                    log_structured(
                        level="warning",
                        message="Invalid redirect URL detected",
                        correlation_id=correlation_id,
                        request=request,
                        redirect_url=redirect_after,
                        frontend_url=frontend_url
                    )
                    redirect_after = None
        except ValueError:
            log_structured(
                level="warning",
                message="Invalid redirect URL format",
                correlation_id=correlation_id,
                request=request,
                redirect_url=redirect_after
            )
            redirect_after = None
    
    try:
        log_structured(
            level="info",
            message="Initiating OAuth authorization",
            correlation_id=correlation_id,
            request=request,
            provider=provider
        )
    
        oauth_provider = get_oauth_provider(provider)
        if not oauth_provider:
            raise create_http_exception(
                message=f"OAuth provider '{provider}' is not configured. Please check server configuration.",
                status_code=503,
                error_type="ServiceUnavailable"
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
            raise create_http_exception(
                message="Invalid OAuth provider",
                status_code=500,
                error_type="InternalServerError"
            )
        
        log_structured(
            level="info",
            message="OAuth authorization URL generated",
            correlation_id=correlation_id,
            request=request,
            provider=provider
        )
        
        # Redirect to provider
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "oauth_authorize", "provider": provider},
            correlation_id,
            request
        )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    request: Request,
    provider: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State token for CSRF protection"),
    error: Optional[str] = Query(None, description="OAuth error from provider"),
    error_description: Optional[str] = Query(None, description="OAuth error description"),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    OAuth callback endpoint - handles provider redirect after authorization.
    
    Exchanges authorization code for tokens and creates/logs in user.
    """
    correlation_id = get_correlation_id(request)
    
    # Validate provider name
    try:
        provider = validate_oauth_provider(provider)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    # Check for OAuth provider errors
    if error:
        error_msg = error_description or error
        log_structured(
            level="warning",
            message="OAuth provider returned error",
            correlation_id=correlation_id,
            request=request,
            provider=provider,
            error=error,
            error_description=error_msg
        )
        raise create_http_exception(
            message=f"OAuth authorization failed: {error_msg}",
            status_code=400,
            error_type="OAuthError"
        )
    
    # Validate inputs
    if not code or not code.strip():
        raise create_http_exception(
            message="Authorization code is required",
            status_code=400,
            error_type="ValidationError"
        )
    
    if not state or not state.strip():
        raise create_http_exception(
            message="State token is required",
            status_code=400,
            error_type="ValidationError"
        )
    
    code = code.strip()
    state = state.strip()
    
    if not db_service:
        raise create_http_exception(
            message="OAuth authentication requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    try:
        log_structured(
            level="info",
            message="Processing OAuth callback",
            correlation_id=correlation_id,
            request=request,
            provider=provider
        )
        
        # Verify state
        state_data = _verify_state(state)
        if not state_data:
            log_structured(
                level="warning",
                message="Invalid or expired OAuth state token",
                correlation_id=correlation_id,
                request=request,
                provider=provider,
                state_prefix=state[:10] if state else "None"
            )
            raise create_http_exception(
                message="Invalid or expired state token. Please try logging in again.",
                status_code=400,
                error_type="ValidationError"
            )
        
        if state_data["provider"] != provider:
            log_structured(
                level="warning",
                message="State provider mismatch",
                correlation_id=correlation_id,
                request=request,
                expected_provider=state_data["provider"],
                received_provider=provider
            )
            raise create_http_exception(
                message="State provider mismatch. Please try logging in again.",
                status_code=400,
                error_type="ValidationError"
            )
        
        _clear_state(state)
        
        # Get OAuth provider
        oauth_provider = get_oauth_provider(provider)
        if not oauth_provider:
            raise create_http_exception(
                message=f"Unsupported provider: {provider}",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Exchange code for tokens
        if isinstance(oauth_provider, GoogleOAuthProvider):
            try:
                tokens = await oauth_provider.exchange_code_for_tokens(code)
            except Exception as e:
                log_service_error(
                    e,
                    {"operation": "oauth_callback", "provider": provider, "step": "exchange_code"},
                    correlation_id,
                    request
                )
                raise create_http_exception(
                    message="Failed to exchange authorization code. The code may be invalid or expired.",
                    status_code=400,
                    error_type="OAuthError"
                )
            
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            
            if not access_token:
                raise create_http_exception(
                    message="OAuth provider did not return an access token",
                    status_code=400,
                    error_type="OAuthError"
                )
            
            # Get user info
            try:
                user_info = await oauth_provider.get_user_info(access_token)
            except Exception as e:
                log_service_error(
                    e,
                    {"operation": "oauth_callback", "provider": provider, "step": "get_user_info"},
                    correlation_id,
                    request
                )
                raise create_http_exception(
                    message="Failed to retrieve user information from OAuth provider",
                    status_code=400,
                    error_type="OAuthError"
                )
            
            provider_user_id = user_info.get("sub")
            email = user_info.get("email")
            full_name = user_info.get("name") or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
            email_verified = user_info.get("verified_email", True)
            
        elif isinstance(oauth_provider, AppleOAuthProvider):
            try:
                tokens = await oauth_provider.exchange_code_for_tokens(code)
            except Exception as e:
                logger.error(f"Failed to exchange Apple OAuth code: {e}", exc_info=True)
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange authorization code. The code may be invalid or expired."
                )
            
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            id_token = tokens.get("id_token")
            
            if not id_token:
                raise HTTPException(
                    status_code=400,
                    detail="OAuth provider did not return an ID token"
                )
            
            # Get user info from ID token
            try:
                user_info = await oauth_provider.get_user_info_from_id_token(id_token)
            except Exception as e:
                logger.error(f"Failed to get Apple user info: {e}", exc_info=True)
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve user information from OAuth provider"
                )
            
            provider_user_id = user_info.get("sub")
            email = user_info.get("email")
            full_name = user_info.get("name", "")
            email_verified = user_info.get("email_verified", True)
        else:
            logger.error(f"Invalid OAuth provider type: {type(oauth_provider)}")
            raise HTTPException(status_code=500, detail="Invalid OAuth provider configuration")
        
        if not email:
            raise create_http_exception(
                message="Email not provided by OAuth provider. Please ensure your account has a verified email address.",
                status_code=400,
                error_type="OAuthError"
            )
        
        if not provider_user_id:
            raise create_http_exception(
                message="User ID not provided by OAuth provider",
                status_code=400,
                error_type="OAuthError"
            )
        
        # Find or create user
        user_service = UserService()
        try:
            user = await user_service.get_user_by_email(email)
        except Exception as e:
            log_service_error(
                e,
                {"operation": "oauth_callback", "provider": provider, "step": "get_user"},
                correlation_id,
                request
            )
            raise create_http_exception(
                message="Database service temporarily unavailable. Please try again later.",
                status_code=503,
                error_type="ServiceUnavailable"
            )
        
        if user:
            # Existing user - check if OAuth account is linked
            if user.get("oauth_provider") == provider and user.get("oauth_provider_id") == provider_user_id:
                # Update tokens
                try:
                    await user_service.update_oauth_tokens(
                        user["id"],
                        provider,
                        provider_user_id,
                        access_token,
                        refresh_token,
                        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    )
                except Exception as e:
                    logger.error(f"Failed to update OAuth tokens: {e}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update authentication tokens"
                    )
            elif user.get("oauth_provider") is None:
                # Link OAuth account to existing password-based account
                try:
                    await user_service.link_oauth_account(
                        user["id"],
                        provider,
                        provider_user_id,
                        access_token,
                        refresh_token,
                        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    )
                except Exception as e:
                    logger.error(f"Failed to link OAuth account: {e}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to link OAuth account to existing user"
                    )
            else:
                # OAuth account linked to different provider
                existing_provider = user.get('oauth_provider', 'unknown')
                logger.warning(
                    f"Attempt to link {provider} account to email already linked to {existing_provider}"
                )
                raise HTTPException(
                    status_code=409,
                    detail=f"Email already linked to {existing_provider} account. Please use {existing_provider} to sign in."
                )
        else:
            # New user - create account
            try:
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
            except ValueError as e:
                # User already exists (race condition)
                log_structured(
                    level="warning",
                    message="User creation failed (may already exist)",
                    correlation_id=correlation_id,
                    request=request,
                    provider=provider,
                    error=str(e)
                )
                user = await user_service.get_user_by_email(email)
                if not user:
                    raise create_http_exception(
                        message="Failed to create user account",
                        status_code=500,
                        error_type="InternalServerError"
                    )
            except Exception as e:
                log_service_error(
                    e,
                    {"operation": "oauth_callback", "provider": provider, "step": "create_user"},
                    correlation_id,
                    request
                )
                raise create_http_exception(
                    message="Failed to create user account. Please try again later.",
                    status_code=500,
                    error_type="InternalServerError"
                )
        
        # Update last login
        try:
            await user_service.update_user_last_login(user["id"])
        except Exception as e:
            log_structured(
                level="warning",
                message="Failed to update last login (non-critical)",
                correlation_id=correlation_id,
                request=request,
                error=str(e)
            )
            # Non-critical error, continue
        
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
        
        log_structured(
            level="info",
            message="OAuth callback completed successfully",
            correlation_id=correlation_id,
            request=request,
            provider=provider,
            user_email=email
        )
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except ValueError as e:
        # Validation errors
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "oauth_callback", "provider": provider},
            correlation_id,
            request
        )


@router.post("/oauth/{provider}/refresh")
async def refresh_oauth_token(
    request: Request,
    provider: str,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
    auth: TokenContext = Depends(
        auth_dependency({"user/*.read"})
    ),
):
    """
    Refresh OAuth access token using stored refresh token.
    
    Requires the user to be authenticated and have an OAuth account linked.
    """
    correlation_id = get_correlation_id(request)
    
    try:
        provider = validate_oauth_provider(provider)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    if not db_service:
        raise create_http_exception(
            message="OAuth token refresh requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    try:
        log_structured(
            level="info",
            message="Refreshing OAuth token",
            correlation_id=correlation_id,
            request=request,
            provider=provider
        )
        
        user_service = UserService()
        
        # Get current user from auth context
        user_email = auth.user_id if hasattr(auth, 'user_id') else None
        if not user_email:
            # Try to extract from token if available
            raise create_http_exception(
                message="User authentication required for token refresh",
                status_code=401,
                error_type="Unauthorized"
            )
        
        # Get user from database
        user = await user_service.get_user_by_email(user_email)
        if not user:
            raise create_http_exception(
                message="User not found",
                status_code=404,
                error_type="NotFound"
            )
        
        # Check if user has OAuth account linked
        if user.get("oauth_provider") != provider:
            raise create_http_exception(
                message=f"User account is not linked to {provider} OAuth provider",
                status_code=400,
                error_type="ValidationError"
            )
        
        refresh_token = user.get("oauth_refresh_token")
        if not refresh_token:
            raise create_http_exception(
                message="No refresh token available. Please re-authenticate with OAuth.",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Get OAuth provider and refresh token
        oauth_provider = get_oauth_provider(provider)
        if not oauth_provider:
            raise create_http_exception(
                message=f"Unsupported provider: {provider}",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Refresh access token
        if isinstance(oauth_provider, GoogleOAuthProvider):
            try:
                new_tokens = await oauth_provider.refresh_access_token(refresh_token)
            except Exception as e:
                log_service_error(
                    e,
                    {"operation": "refresh_oauth_token", "provider": provider},
                    correlation_id,
                    request
                )
                raise create_http_exception(
                    message="Failed to refresh access token. Please re-authenticate.",
                    status_code=400,
                    error_type="OAuthError"
                )
        elif isinstance(oauth_provider, AppleOAuthProvider):
            # Apple doesn't have a separate refresh endpoint in the same way
            # The refresh token is used during token exchange
            raise create_http_exception(
                message="Apple OAuth token refresh requires re-authentication",
                status_code=501,
                error_type="NotImplemented"
            )
        else:
            raise create_http_exception(
                message="Invalid OAuth provider configuration",
                status_code=500,
                error_type="InternalServerError"
            )
        
        new_access_token = new_tokens.get("access_token")
        new_refresh_token = new_tokens.get("refresh_token", refresh_token)  # Keep old if not provided
        expires_in = new_tokens.get("expires_in", 3600)
        
        if not new_access_token:
            raise create_http_exception(
                message="OAuth provider did not return a new access token",
                status_code=400,
                error_type="OAuthError"
            )
        
        # Update tokens in database
        try:
            await user_service.update_oauth_tokens(
                user["id"],
                provider,
                user.get("oauth_provider_id"),
                new_access_token,
                new_refresh_token,
                datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            )
        except Exception as e:
            log_service_error(
                e,
                {"operation": "refresh_oauth_token", "provider": provider, "step": "update_tokens"},
                correlation_id,
                request
            )
            raise create_http_exception(
                message="Failed to update authentication tokens",
                status_code=500,
                error_type="InternalServerError"
            )
        
        log_structured(
            level="info",
            message="OAuth token refreshed successfully",
            correlation_id=correlation_id,
            request=request,
            provider=provider,
            user_email=user_email
        )
        
        return {
            "status": "success",
            "message": "Access token refreshed successfully",
            "expires_in": expires_in
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "refresh_oauth_token", "provider": provider},
            correlation_id,
            request
        )


@router.post("/oauth/{provider}/link")
async def link_oauth_account(
    request: Request,
    provider: str,
    code: str,
    state: Optional[str] = None,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
    auth: TokenContext = Depends(auth_dependency({"user/*.write"})),
):
    """
    Link an OAuth account to an existing user account.
    
    Requires the user to be already authenticated.
    """
    correlation_id = get_correlation_id(request)
    
    try:
        provider = validate_oauth_provider(provider)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    if not db_service:
        raise create_http_exception(
            message="OAuth account linking requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate code
    if not code or not code.strip():
        raise create_http_exception(
            message="Authorization code is required",
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Linking OAuth account",
            correlation_id=correlation_id,
            request=request,
            provider=provider
        )
        
        # This would require current user context from JWT
        # Implementation depends on your auth middleware
        raise create_http_exception(
            message="Account linking not yet implemented",
            status_code=501,
            error_type="NotImplemented"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "link_oauth_account", "provider": provider},
            correlation_id,
            request
        )


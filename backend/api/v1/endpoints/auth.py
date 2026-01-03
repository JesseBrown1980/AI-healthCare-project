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
    EmailVerificationRequest,
    EmailVerificationResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
)
from backend.auth import hash_password, verify_password, is_password_strong
from backend.di import get_database_service
from backend.database.service import DatabaseService
from backend.database.user_service import UserService
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.utils.validation import validate_email, validate_password_strength

logger = logging.getLogger(__name__)

router = APIRouter()


demo_login_enabled: bool = os.getenv("ENABLE_DEMO_LOGIN", "false").lower() == "true"

demo_login_secret = os.getenv("DEMO_LOGIN_SECRET", "demo-secret-key-123")
demo_login_expires_minutes = int(os.getenv("DEMO_LOGIN_EXPIRES_MINS", "60"))

def _issue_demo_token(email: str, patient: Optional[str] = None, scopes: Optional[str] = None) -> DemoLoginResponse:
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

@router.post("/login", response_model=DemoLoginResponse)
async def login(
    request: Request,
    payload: DemoLoginRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Authenticate user and issue JWT token.
    
    Supports both database-backed authentication and demo login mode.
    """
    correlation_id = get_correlation_id(request)
    
    # Validate email
    try:
        validated_email = validate_email(payload.email)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    # Try database authentication first if available
    if db_service:
        try:
            log_structured(
                level="info",
                message="Attempting database authentication",
                correlation_id=correlation_id,
                request=request,
                email=validated_email
            )
            
            user_service = UserService()
            user = await user_service.get_user_by_email(validated_email)
            if user:
                # Check if user is OAuth-only (no password)
                if user.get('oauth_provider') and not user.get('password_hash'):
                    raise create_http_exception(
                        message=f"Please sign in with {user.get('oauth_provider', 'OAuth')}",
                        status_code=403,
                        error_type="Forbidden"
                    )
                
                # Verify password (skip if OAuth user with dummy password)
                password_hash = user.get('password_hash')
                if not password_hash:
                    raise create_http_exception(
                        message="Invalid credentials",
                        status_code=403,
                        error_type="Forbidden"
                    )
                
                if not verify_password(payload.password, password_hash):
                    raise create_http_exception(
                        message="Invalid credentials",
                        status_code=403,
                        error_type="Forbidden"
                    )
                
                # Check if user is active
                if not user.get('is_active', True):
                    raise create_http_exception(
                        message="User account is inactive",
                        status_code=403,
                        error_type="Forbidden"
                    )
                
                # Update last login
                await user_service.update_user_last_login(user['id'])
                
                # Issue token with user roles
                roles = user.get('roles', ['viewer'])
                scopes = "patient/*.read user/*.read system/*.read"
                if 'admin' in roles:
                    scopes += " patient/*.write user/*.write system/*.write"
                elif 'clinician' in roles:
                    scopes += " patient/*.write"
                
                log_structured(
                    level="info",
                    message="User authenticated successfully",
                    correlation_id=correlation_id,
                    request=request,
                    email=validated_email,
                    roles=roles
                )
                
                return _issue_demo_token(validated_email, payload.patient, scopes=scopes)
        except HTTPException:
            raise
        except Exception as e:
            log_structured(
                level="warning",
                message="Database authentication failed, falling back to demo login",
                correlation_id=correlation_id,
                request=request,
                email=validated_email,
                error=str(e)
            )
            # Fall through to demo login
    
    # Fallback to demo login if database auth fails or is disabled
    if not demo_login_enabled:
        raise create_http_exception(
            message="Login is disabled",
            status_code=404,
            error_type="NotFound"
        )

    allowed_email = os.getenv("DEMO_LOGIN_EMAIL")
    allowed_password = os.getenv("DEMO_LOGIN_PASSWORD")

    if allowed_email and validated_email.lower() != allowed_email.lower():
        raise create_http_exception(
            message="Invalid credentials",
            status_code=403,
            error_type="Forbidden"
        )

    if allowed_password and payload.password != allowed_password:
        raise create_http_exception(
            message="Invalid credentials",
            status_code=403,
            error_type="Forbidden"
        )

    if not allowed_email and not allowed_password and not payload.password:
        raise create_http_exception(
            message="Password is required for demo login",
            status_code=400,
            error_type="ValidationError"
        )

    log_structured(
        level="info",
        message="Demo login successful",
        correlation_id=correlation_id,
        request=request,
        email=validated_email
    )

    return _issue_demo_token(validated_email, payload.patient)


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: Request,
    payload: RegisterRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Register a new user account.
    
    Requires database service to be available.
    """
    correlation_id = get_correlation_id(request)
    
    if not db_service:
        raise create_http_exception(
            message="User registration requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate email
    try:
        validated_email = validate_email(payload.email)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    # Validate password strength
    try:
        validated_password = validate_password_strength(payload.password, min_length=8)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Registering new user",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        # Hash password
        password_hash = hash_password(validated_password)
        
        # Create user
        user_service = UserService()
        user = await user_service.create_user(
            email=validated_email,
            password_hash=password_hash,
            full_name=payload.full_name,
            roles=payload.roles,
        )
        
        log_structured(
            level="info",
            message="User registered successfully",
            correlation_id=correlation_id,
            request=request,
            user_id=user['id'],
            email=validated_email
        )
        
        return RegisterResponse(
            id=user['id'],
            email=user['email'],
            full_name=user.get('full_name'),
            roles=user.get('roles', ['viewer']),
        )
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "register", "email": validated_email},
            correlation_id,
            request
        )


@router.post("/password-reset", response_model=PasswordResetResponse)
async def password_reset(
    request: Request,
    payload: PasswordResetRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Request a password reset token.
    
    Generates a secure token and stores it with the user account.
    In production, this token would be sent via email.
    """
    correlation_id = get_correlation_id(request)
    
    if not db_service:
        raise create_http_exception(
            message="Password reset requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate email
    try:
        validated_email = validate_email(payload.email)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Requesting password reset token",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        user_service = UserService()
        token = await user_service.generate_password_reset_token(validated_email)
        
        log_structured(
            level="info",
            message="Password reset token generated",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        # Always return success message (don't reveal if user exists)
        # In production, only send email if user exists
        return PasswordResetResponse(
            message="If an account with that email exists, a password reset token has been generated."
        )
    except Exception as e:
        log_structured(
            level="error",
            message="Password reset request failed",
            correlation_id=correlation_id,
            request=request,
            email=validated_email,
            error=str(e)
        )
        # Still return success to prevent email enumeration
        return PasswordResetResponse(
            message="If an account with that email exists, a password reset token has been generated."
        )


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def password_reset_confirm(
    request: Request,
    payload: PasswordResetConfirmRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Confirm password reset with token and set new password.
    
    Validates the token and updates the user's password.
    """
    correlation_id = get_correlation_id(request)
    
    if not db_service:
        raise create_http_exception(
            message="Password reset requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate email
    try:
        validated_email = validate_email(payload.email)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    # Validate password strength
    try:
        validated_password = validate_password_strength(payload.new_password, min_length=8)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Confirming password reset",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        user_service = UserService()
        
        # Verify token
        is_valid = await user_service.verify_password_reset_token(validated_email, payload.token)
        if not is_valid:
            raise create_http_exception(
                message="Invalid or expired password reset token",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Hash new password
        new_password_hash = hash_password(validated_password)
        
        # Reset password
        success = await user_service.reset_password_with_token(
            validated_email,
            payload.token,
            new_password_hash
        )
        
        if not success:
            raise create_http_exception(
                message="Failed to reset password. Token may be invalid or expired.",
                status_code=400,
                error_type="ValidationError"
            )
        
        log_structured(
            level="info",
            message="Password reset confirmed successfully",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        return PasswordResetConfirmResponse(
            message="Password reset successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "password_reset_confirm", "email": validated_email},
            correlation_id,
            request
        )


@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email_request(
    request: Request,
    payload: EmailVerificationRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Request an email verification token.
    
    Generates a secure token and stores it with the user account.
    In production, this token would be sent via email.
    """
    correlation_id = get_correlation_id(request)
    
    if not db_service:
        raise create_http_exception(
            message="Email verification requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate email
    try:
        validated_email = validate_email(payload.email)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Requesting email verification token",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        user_service = UserService()
        token = await user_service.generate_verification_token(validated_email)
        
        log_structured(
            level="info",
            message="Email verification token generated",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        # Always return success message (don't reveal if user exists)
        # In production, only send email if user exists
        return EmailVerificationResponse(
            message="If an account with that email exists, a verification token has been generated."
        )
    except Exception as e:
        log_structured(
            level="error",
            message="Email verification request failed",
            correlation_id=correlation_id,
            request=request,
            email=validated_email,
            error=str(e)
        )
        # Still return success to prevent email enumeration
        return EmailVerificationResponse(
            message="If an account with that email exists, a verification token has been generated."
        )


@router.post("/verify-email/confirm", response_model=EmailVerificationConfirmResponse)
async def verify_email_confirm(
    request: Request,
    payload: EmailVerificationConfirmRequest,
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    Confirm email verification with token.
    
    Validates the token and marks the user's email as verified.
    """
    correlation_id = get_correlation_id(request)
    
    if not db_service:
        raise create_http_exception(
            message="Email verification requires database service",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    # Validate email
    try:
        validated_email = validate_email(payload.email)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Confirming email verification",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        user_service = UserService()
        
        # Verify token
        is_valid = await user_service.verify_email_with_token(validated_email, payload.token)
        if not is_valid:
            raise create_http_exception(
                message="Invalid or expired verification token",
                status_code=400,
                error_type="ValidationError"
            )
        
        log_structured(
            level="info",
            message="Email verified successfully",
            correlation_id=correlation_id,
            request=request,
            email=validated_email
        )
        
        return EmailVerificationConfirmResponse(
            message="Email verified successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "verify_email_confirm", "email": validated_email},
            correlation_id,
            request
        )


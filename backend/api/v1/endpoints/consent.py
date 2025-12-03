"""
Consent management API endpoints.

Handles user consent for privacy policies, terms of service, and data processing.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.security import TokenContext, auth_dependency
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.services.consent_service import ConsentService
from backend.database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class ConsentAcceptRequest(BaseModel):
    """Request model for accepting consent."""
    consent_type: str = Field(..., description="Type of consent (privacy_policy, terms_of_service, etc.)")
    version: Optional[str] = Field(None, description="Version of the policy/terms")


class ConsentWithdrawRequest(BaseModel):
    """Request model for withdrawing consent."""
    consent_type: str = Field(..., description="Type of consent to withdraw")


class ConsentStatusResponse(BaseModel):
    """Response model for consent status."""
    user_id: str
    consent_type: Optional[str] = None
    accepted: bool
    accepted_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    version: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConsentListResponse(BaseModel):
    """Response model for listing all consents."""
    user_id: str
    consents: Dict[str, Any]
    has_required_consent: bool


@router.post("/accept", response_model=Dict[str, str])
async def accept_consent(
    request: Request,
    consent_data: ConsentAcceptRequest,
    auth: TokenContext = Depends(auth_dependency({"user/*.write"})),
    consent_service: ConsentService = Depends(lambda: ConsentService()),
):
    """
    Accept a consent (privacy policy, terms of service, etc.).
    """
    correlation_id = get_correlation_id(request)
    
    try:
        # Extract IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        log_structured(
            level="info",
            message="User accepting consent",
            correlation_id=correlation_id,
            request=request,
            user_id=auth.user_id,
            consent_type=consent_data.consent_type,
        )
        
        consent_id = await consent_service.record_consent(
            user_id=auth.user_id,
            consent_type=consent_data.consent_type,
            version=consent_data.version,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"region": consent_service.region},
        )
        
        log_structured(
            level="info",
            message="Consent accepted successfully",
            correlation_id=correlation_id,
            request=request,
            user_id=auth.user_id,
            consent_id=consent_id,
            consent_type=consent_data.consent_type,
        )
        
        return {
            "status": "success",
            "message": "Consent accepted",
            "consent_id": consent_id,
        }
    
    except Exception as e:
        log_service_error(e, {"user_id": auth.user_id, "consent_type": consent_data.consent_type}, correlation_id, request)
        raise create_http_exception(
            message="Failed to record consent",
            status_code=500,
            error_type="InternalServerError"
        )


@router.post("/withdraw", response_model=Dict[str, str])
async def withdraw_consent(
    request: Request,
    consent_data: ConsentWithdrawRequest,
    auth: TokenContext = Depends(auth_dependency({"user/*.write"})),
    consent_service: ConsentService = Depends(lambda: ConsentService()),
):
    """
    Withdraw a consent.
    """
    correlation_id = get_correlation_id(request)
    
    try:
        # Extract IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        log_structured(
            level="info",
            message="User withdrawing consent",
            correlation_id=correlation_id,
            request=request,
            user_id=auth.user_id,
            consent_type=consent_data.consent_type,
        )
        
        withdrawn = await consent_service.withdraw_consent(
            user_id=auth.user_id,
            consent_type=consent_data.consent_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if not withdrawn:
            raise create_http_exception(
                message="No active consent found to withdraw",
                status_code=404,
                error_type="NotFound"
            )
        
        log_structured(
            level="info",
            message="Consent withdrawn successfully",
            correlation_id=correlation_id,
            request=request,
            user_id=auth.user_id,
            consent_type=consent_data.consent_type,
        )
        
        return {
            "status": "success",
            "message": "Consent withdrawn",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log_service_error(e, {"user_id": auth.user_id, "consent_type": consent_data.consent_type}, correlation_id, request)
        raise create_http_exception(
            message="Failed to withdraw consent",
            status_code=500,
            error_type="InternalServerError"
        )


@router.get("/status", response_model=ConsentListResponse)
async def get_consent_status(
    request: Request,
    consent_type: Optional[str] = None,
    auth: TokenContext = Depends(auth_dependency({"user/*.read"})),
    consent_service: ConsentService = Depends(lambda: ConsentService()),
):
    """
    Get consent status for the current user.
    """
    correlation_id = get_correlation_id(request)
    
    try:
        if consent_type:
            status = await consent_service.get_consent_status(auth.user_id, consent_type)
            if not status:
                raise create_http_exception(
                    message="Consent not found",
                    status_code=404,
                    error_type="NotFound"
                )
            
            return ConsentStatusResponse(
                user_id=auth.user_id,
                consent_type=status["consent_type"],
                accepted=status["accepted"],
                accepted_at=status["accepted_at"],
                withdrawn_at=status["withdrawn_at"],
                version=status.get("version"),
                metadata=status.get("metadata", {}),
            )
        else:
            # Get all consents
            all_consents = await consent_service.get_all_user_consents(auth.user_id)
            has_required = await consent_service.has_required_consent(auth.user_id)
            
            return ConsentListResponse(
                user_id=auth.user_id,
                consents=all_consents,
                has_required_consent=has_required,
            )
    
    except HTTPException:
        raise
    except Exception as e:
        log_service_error(e, {"user_id": auth.user_id}, correlation_id, request)
        raise create_http_exception(
            message="Failed to get consent status",
            status_code=500,
            error_type="InternalServerError"
        )

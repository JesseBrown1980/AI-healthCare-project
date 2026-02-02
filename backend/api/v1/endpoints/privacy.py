
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from backend.database.connection import get_db_session
from backend.services.privacy_service import PrivacyService
from backend.security import auth_dependency, TokenContext
from backend.audit_service import AuditService
from backend.di.container import ServiceContainer
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.utils.error_responses import get_correlation_id, create_http_exception
from backend.utils.logging_utils import log_structured

router = APIRouter()
privacy_service = PrivacyService()

@router.post("/forget-me", status_code=status.HTTP_200_OK)
async def request_account_deletion(
    request: Request,
    background_tasks: BackgroundTasks,
    token: TokenContext = Depends(auth_dependency(required_scopes=["user/*.write"])),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Request permanent deletion of the user request's account and data (Right to be Forgotten).
    This action is irreversible.
    """
    user_id = token.subject
    if not user_id:
        raise create_http_exception(
            message="Invalid user context",
            status_code=400,
            error_type="ValidationError"
        )

    correlation_id = get_correlation_id(request)
    
    with ServiceErrorHandler.safe_execution(
        {"operation": "request_account_deletion", "user_id": user_id},
        correlation_id,
        request
    ):
        log_structured(
            level="info",
            message="Processing account deletion request",
            correlation_id=correlation_id,
            request=request,
            user_id=user_id
        )
        
        deleted_stats = await privacy_service.delete_user_data(session, user_id)
        
        log_structured(
            level="info",
            message="Account deletion processed successfully",
            correlation_id=correlation_id,
            request=request,
            user_id=user_id,
            deleted_records=deleted_stats
        )
        
        return {
            "status": "success", 
            "message": "Account and associated data have been permanently deleted.",
            "deleted_records": deleted_stats
        }

@router.get("/export", status_code=status.HTTP_200_OK)
async def export_data(
    request: Request,
    token: TokenContext = Depends(auth_dependency(required_scopes=["user/*.read"])),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Export all personal data in a portable JSON format (GDPR Data Portability).
    """
    user_id = token.subject
    if not user_id:
        raise create_http_exception(
            message="Invalid user context",
            status_code=400,
            error_type="ValidationError"
        )

    correlation_id = get_correlation_id(request)
    
    with ServiceErrorHandler.safe_execution(
        {"operation": "export_data", "user_id": user_id},
        correlation_id,
        request
    ):
        log_structured(
            level="info",
            message="Processing data export request",
            correlation_id=correlation_id,
            request=request,
            user_id=user_id
        )
        
        data = await privacy_service.export_user_data(session, user_id)
        
        log_structured(
            level="info",
            message="Data export processed successfully",
            correlation_id=correlation_id,
            request=request,
            user_id=user_id
        )
        
        return data

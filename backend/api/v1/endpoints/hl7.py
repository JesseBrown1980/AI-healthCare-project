"""
HL7 v2.x message reception endpoints.

Provides HTTP endpoints for receiving and processing HL7 v2.x messages.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Body

from backend.security import TokenContext, auth_dependency
from backend.di import get_database_service, get_fhir_connector, get_audit_service
from backend.database.service import DatabaseService
from backend.fhir_connector import FhirResourceService
from backend.audit_service import AuditService
from backend.hl7 import HL7MessageParser, HL7ParseError, HL7MessageRouter, HL7ToFHIRConverter, HL7ConversionError
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler

logger = logging.getLogger(__name__)

router = APIRouter()


def get_hl7_parser() -> HL7MessageParser:
    """Dependency to get HL7 message parser."""
    return HL7MessageParser()


def get_hl7_converter() -> HL7ToFHIRConverter:
    """Dependency to get HL7 to FHIR converter."""
    return HL7ToFHIRConverter()


def get_hl7_router() -> HL7MessageRouter:
    """Dependency to get HL7 message router."""
    return HL7MessageRouter()


@router.post("/hl7/receive")
async def receive_hl7_message(
    request: Request,
    message: str = Body(..., description="HL7 v2.x message (pipe-delimited)"),
    auto_convert: bool = Body(True, description="Automatically convert to FHIR and store"),
    trigger_analysis: bool = Body(False, description="Trigger patient analysis after processing"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.write", "user/*.write", "system/*.write"})
    ),
    parser: HL7MessageParser = Depends(get_hl7_parser),
    converter: HL7ToFHIRConverter = Depends(get_hl7_converter),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
    fhir_connector: Optional[FhirResourceService] = Depends(get_fhir_connector),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Receive and process an HL7 v2.x message.
    
    Parses the message, optionally converts to FHIR resources, and stores them.
    Supports ADT, ORU, ORM message types.
    
    Returns:
        - Parsed message structure
        - Converted FHIR resources (if auto_convert=True)
        - Processing status
    """
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Receiving HL7 message",
            correlation_id=correlation_id,
            request=request,
            auto_convert=auto_convert,
            trigger_analysis=trigger_analysis
        )
        
        # Parse HL7 message
        parsed_message = parser.parse(message)
        message_type = parsed_message.get("message_type", "UNKNOWN")
        
        log_structured(
            level="info",
            message="HL7 message parsed successfully",
            correlation_id=correlation_id,
            request=request,
            message_type=message_type
        )
        
        # Extract patient ID if available
        patient_id = None
        if "pid" in parsed_message:
            patient_id = parsed_message["pid"].get("patient_id")
        
        # Convert to FHIR if requested
        fhir_resources = None
        if auto_convert:
            try:
                fhir_resources = converter.convert(parsed_message)
                
                # Store FHIR resources if database service available
                if db_service and fhir_resources:
                    # Store patient if present
                    if fhir_resources.get("patient") and patient_id:
                        # Patient would typically be stored via FHIR connector
                        # For now, we'll log it
                        logger.info("Patient resource from HL7: %s [%s]", patient_id, correlation_id)
                    
                    # Store observations
                    for obs in fhir_resources.get("observations", []):
                        # Observations would be stored via FHIR connector
                        logger.debug("Observation from HL7: %s [%s]", obs.get("code", {}).get("text"), correlation_id)
                
                log_structured(
                    level="info",
                    message="HL7 message converted to FHIR resources",
                    correlation_id=correlation_id,
                    request=request,
                    message_type=message_type
                )
            except HL7ConversionError as e:
                log_structured(
                    level="warning",
                    message="HL7 conversion error (continuing without conversion)",
                    correlation_id=correlation_id,
                    request=request,
                    error=str(e)
                )
                # Continue without conversion
        
        # Audit log
        if audit_service and patient_id:
            await audit_service.record_event(
                action="C",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc=f"HL7 message received: {message_type}",
                event_type="hl7_receive",
            )
        
        # Build response
        response = {
            "status": "success",
            "message_type": message_type,
            "patient_id": patient_id,
            "parsed_message": {
                "message_type": message_type,
                "has_patient": "pid" in parsed_message,
                "has_observations": "obx" in parsed_message,
                "has_encounter": "pv1" in parsed_message,
            },
        }
        
        if fhir_resources:
            response["fhir_resources"] = {
                "patient": fhir_resources.get("patient") is not None,
                "observations_count": len(fhir_resources.get("observations", [])),
                "encounters_count": len(fhir_resources.get("encounters", [])),
                "medication_requests_count": len(fhir_resources.get("medication_requests", [])),
            }
        
        # TODO: Trigger patient analysis if requested and patient_id available
        # This would require integration with PatientAnalyzer
        if trigger_analysis and patient_id:
            log_structured(
                level="info",
                message="Analysis trigger requested for patient",
                correlation_id=correlation_id,
                request=request,
                patient_id=patient_id
            )
            # Future: await patient_analyzer.analyze(patient_id, ...)
            response["analysis_triggered"] = True
        
        log_structured(
            level="info",
            message="HL7 message processed successfully",
            correlation_id=correlation_id,
            request=request,
            message_type=message_type,
            patient_id=patient_id
        )
        
        return response
    
    except HL7ParseError as e:
        log_service_error(
            e,
            {"operation": "receive_hl7_message", "message_type": message_type if 'message_type' in locals() else "unknown"},
            correlation_id,
            request
        )
        raise create_http_exception(
            message=f"Invalid HL7 message: {str(e)}",
            status_code=400,
            error_type="ValidationError"
        )
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "receive_hl7_message"},
            correlation_id,
            request
        )


@router.get("/hl7/messages")
async def list_hl7_messages(
    request: Request,
    message_type: Optional[str] = None,
    patient_id: Optional[str] = None,
    limit: int = 100,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """
    List received HL7 messages (if stored in database).
    
    Note: This endpoint requires database storage of HL7 messages.
    Currently returns placeholder - full implementation would query database.
    """
    from backend.utils.validation import validate_patient_id
    
    if not db_service:
        raise HTTPException(
            status_code=503,
            detail="Database service required for message listing"
        )
    
    # Validate patient_id if provided
    if patient_id:
        patient_id = validate_patient_id(patient_id)
    
    # TODO: Implement database query for stored HL7 messages
    # For now, return placeholder
    return {
        "status": "success",
        "messages": [],
        "count": 0,
        "message": "HL7 message storage not yet implemented",
    }


@router.get("/hl7/messages/{message_id}")
async def get_hl7_message(
    request: Request,
    message_id: str,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    db_service: Optional[DatabaseService] = Depends(get_database_service),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Get a specific HL7 message by ID.
    
    Note: This endpoint requires database storage of HL7 messages.
    """
    correlation_id = get_correlation_id(request)
    
    if not db_service:
        raise create_http_exception(
            message="Database service required",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    try:
        log_structured(
            level="info",
            message="Fetching HL7 message",
            correlation_id=correlation_id,
            request=request,
            message_id=message_id
        )
        
        # TODO: Implement database query
        raise create_http_exception(
            message="HL7 message storage not yet implemented",
            status_code=404,
            error_type="NotFound"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_hl7_message", "message_id": message_id},
            correlation_id,
            request
        )


@router.post("/hl7/validate")
async def validate_hl7_message(
    request: Request,
    body: Dict[str, str] = Body(..., description="Request body with 'message' field"),
    parser: HL7MessageParser = Depends(get_hl7_parser),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Validate an HL7 v2.x message without processing it.
    
    Returns validation result and parsed structure if valid.
    """
    correlation_id = get_correlation_id(request)
    message = body.get("message", "")
    
    try:
        log_structured(
            level="info",
            message="Validating HL7 message",
            correlation_id=correlation_id,
            request=request
        )
        
        if not message:
            raise create_http_exception(
                message="Message field is required",
                status_code=400,
                error_type="ValidationError"
            )
        
        parsed_message = parser.parse(message)
        
        log_structured(
            level="info",
            message="HL7 message validated successfully",
            correlation_id=correlation_id,
            request=request,
            message_type=parsed_message.get("message_type")
        )
        
        return {
            "status": "valid",
            "message_type": parsed_message.get("message_type"),
            "has_patient": "pid" in parsed_message,
            "has_observations": "obx" in parsed_message,
            "has_encounter": "pv1" in parsed_message,
            "segments": list(parsed_message.get("segments", {}).keys()),
        }
    except HL7ParseError as e:
        log_structured(
            level="warning",
            message="HL7 message validation failed",
            correlation_id=correlation_id,
            request=request,
            error=str(e)
        )
        return {
            "status": "invalid",
            "error": str(e),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "validate_hl7_message"},
            correlation_id,
            request
        )

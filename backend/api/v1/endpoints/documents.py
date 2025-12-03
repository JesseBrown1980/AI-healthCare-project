"""
Document upload and management endpoints.

Handles file uploads, OCR processing, and document linking to patients.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, Request
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import os

from backend.security import TokenContext, auth_dependency
from backend.di import get_database_service, get_audit_service
from backend.database import DatabaseService
from backend.document_service import DocumentService
from backend.audit_service import AuditService
from backend.utils.validation import validate_patient_id, validate_document_id, validate_filename, validate_file_size, MAX_FILE_SIZE
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured
from backend.utils.service_error_handler import ServiceErrorHandler

router = APIRouter()


def get_document_service(
    database_service: Optional[DatabaseService] = Depends(get_database_service),
) -> Optional[DocumentService]:
    """Get document service instance."""
    if not database_service:
        return None
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    return DocumentService(database_service=database_service, upload_dir=upload_dir)


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    patient_id: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.write", "user/*.write", "system/*.write"})
    ),
    document_service: Optional[DocumentService] = Depends(get_document_service),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Upload a document (PDF, image) for OCR processing.
    
    Returns document ID and metadata.
    """
    if not document_service:
        raise create_http_exception(
            message="Document service not available (database required)",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Uploading document",
            correlation_id=correlation_id,
            request=request,
            filename=file.filename[:50] if file.filename else None,
            document_type=document_type
        )
        # Validate filename
        if file.filename:
            validate_filename(file.filename)
        
        # Validate file size (check content-length header if available)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                file_size = int(content_length)
                validate_file_size(file_size, max_size=MAX_FILE_SIZE)
            except ValueError:
                # Invalid content-length, will check during read
                pass
        
        # Validate file type
        allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}
        file_ext = os.path.splitext(file.filename or "")[1].lower()
        if file_ext not in allowed_extensions:
            raise create_http_exception(
                message=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Validate patient_id if provided
        validated_patient_id = None
        if patient_id:
            validated_patient_id = validate_patient_id(patient_id)
        elif auth.patient:
            validated_patient_id = validate_patient_id(auth.patient)
        
        # Save file
        result = await document_service.save_uploaded_file(
            file=file,
            patient_id=validated_patient_id,
            document_type=document_type,
            created_by=auth.user_id,
        )
        
        # Audit log
        if audit_service:
            await audit_service.record_event(
                action="C",
                patient_id=patient_id or auth.patient,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Document uploaded",
                event_type="document_upload",
            )
        
        log_structured(
            level="info",
            message="Document uploaded successfully",
            correlation_id=correlation_id,
            request=request,
            document_id=result["id"],
            duplicate=result.get("duplicate", False)
        )
        
        return {
            "status": "success",
            "document_id": result["id"],
            "file_hash": result["file_hash"],
            "document_type": result["document_type"],
            "duplicate": result.get("duplicate", False),
            "message": "Document uploaded successfully. Use /documents/{id}/process to run OCR.",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "upload_document", "filename": file.filename},
            correlation_id,
            request
        )


@router.post("/documents/{document_id}/process")
async def process_document(
    request: Request,
    document_id: str = Path(..., description="Document ID to process"),
    engine: Optional[str] = Query(None, description="OCR engine: 'tesseract' or 'easyocr'"),
    language: Optional[str] = Query(None, description="Language code (e.g., 'en', 'es')"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    document_service: Optional[DocumentService] = Depends(get_document_service),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Process document with OCR to extract text.
    
    Returns extracted text and confidence score.
    """
    # Validate document_id
    document_id = validate_document_id(document_id)
    
    if not document_service:
        raise create_http_exception(
            message="Document service not available",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Processing document with OCR",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id,
            engine=engine,
            language=language
        )
        
        result = await document_service.process_document_with_ocr(
            document_id=document_id,
            engine=engine,
            language=language,
        )
        
        log_structured(
            level="info",
            message="Document processed successfully",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id,
            word_count=result.get("word_count", 0),
            confidence=result.get("confidence", 0)
        )
        
        # Audit log
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=None,  # Will be linked to document's patient_id
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Document processed with OCR",
                event_type="document_ocr",
            )
        
        return {
            "status": "success",
            "document_id": result["document_id"],
            "extracted_text": result["extracted_text"],
            "confidence": result["confidence"],
            "engine": result["engine"],
            "word_count": result["word_count"],
        }
    
    except (ValueError, FileNotFoundError) as e:
        raise create_http_exception(
            message=str(e),
            status_code=404,
            error_type="NotFound"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "process_document", "document_id": document_id},
            correlation_id,
            request
        )


@router.post("/documents/{document_id}/link-patient")
async def link_document_to_patient(
    request: Request,
    document_id: str = Path(..., description="Document ID to link"),
    patient_id: str = Form(..., description="Patient ID to link document to"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.write", "user/*.write", "system/*.write"})
    ),
    document_service: Optional[DocumentService] = Depends(get_document_service),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Link a document to a patient record.
    
    This allows the document to be associated with a patient's medical record.
    Validates both document_id and patient_id before linking.
    """
    # Validate IDs
    document_id = validate_document_id(document_id)
    patient_id = validate_patient_id(patient_id)
    
    if not document_service:
        raise create_http_exception(
            message="Document service not available",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Linking document to patient",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id,
            patient_id=patient_id
        )
        
        result = await document_service.link_document_to_patient(
            document_id=document_id,
            patient_id=patient_id,
        )
        
        log_structured(
            level="info",
            message="Document linked to patient successfully",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id,
            patient_id=patient_id
        )
        
        # Audit log
        if audit_service:
            await audit_service.record_event(
                action="U",
                patient_id=patient_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Document linked to patient",
                event_type="document_link",
            )
        
        return result
    
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=404,
            error_type="NotFound"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "link_document_to_patient", "document_id": document_id, "patient_id": patient_id},
            correlation_id,
            request
        )


@router.get("/patients/{patient_id}/documents")
async def get_patient_documents(
    request: Request,
    patient_id: str = Path(..., description="Patient ID"),
    limit: int = Query(100, ge=1, le=500),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    database_service: Optional[DatabaseService] = Depends(get_database_service),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Get all documents for a patient.
    
    Returns list of documents with metadata.
    """
    # Validate patient_id
    patient_id = validate_patient_id(patient_id)
    
    if not database_service:
        raise create_http_exception(
            message="Database service not available",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    correlation_id = get_correlation_id(request)
    
    try:
        # Check patient access
        if auth.patient and auth.patient != patient_id:
            raise create_http_exception(
                message="Access denied to this patient's documents",
                status_code=403,
                error_type="PermissionDenied"
            )
        
        log_structured(
            level="info",
            message="Fetching patient documents",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id,
            limit=limit
        )
        
        documents = await database_service.get_patient_documents(
            patient_id=patient_id,
            limit=limit,
        )
        
        log_structured(
            level="info",
            message="Patient documents fetched successfully",
            correlation_id=correlation_id,
            request=request,
            patient_id=patient_id,
            document_count=len(documents)
        )
        
        return {
            "status": "success",
            "patient_id": patient_id,
            "documents": documents,
            "count": len(documents),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_patient_documents", "patient_id": patient_id},
            correlation_id,
            request
        )


@router.get("/documents/{document_id}")
async def get_document(
    request: Request,
    document_id: str = Path(..., description="Document ID"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
    database_service: Optional[DatabaseService] = Depends(get_database_service),
):
    """Get document details by ID."""
    # Validate document_id
    document_id = validate_document_id(document_id)
    
    if not database_service:
        raise create_http_exception(
            message="Database service not available",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Fetching document",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id
        )
        
        document = await database_service.get_document(document_id)
        if not document:
            raise create_http_exception(
                message="Document not found",
                status_code=404,
                error_type="NotFound"
            )
        
        # Check patient access
        if auth.patient and document.get("patient_id") != auth.patient:
            raise create_http_exception(
                message="Access denied to this document",
                status_code=403,
                error_type="PermissionDenied"
            )
        
        log_structured(
            level="info",
            message="Document fetched successfully",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id
        )
        
        return {
            "status": "success",
            "document": document,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "get_document", "document_id": document_id},
            correlation_id,
            request
        )


@router.post("/documents/{document_id}/convert-fhir")
async def convert_document_to_fhir(
    request: Request,
    document_id: str,
    patient_id: Optional[str] = Form(None),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.write", "user/*.write", "system/*.write"})
    ),
    document_service: Optional[DocumentService] = Depends(get_document_service),
    audit_service: Optional[AuditService] = Depends(get_audit_service),
):
    """
    Convert parsed document data to FHIR resources.
    
    Creates Observation, MedicationStatement, and Condition resources
    from the extracted medical data.
    """
    if not document_service:
        raise create_http_exception(
            message="Document service not available",
            status_code=503,
            error_type="ServiceUnavailable"
        )
    
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Converting document to FHIR resources",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id,
            patient_id=patient_id or auth.patient
        )
        
        result = await document_service.convert_to_fhir_resources(
            document_id=document_id,
            patient_id=patient_id or auth.patient,
        )
        
        log_structured(
            level="info",
            message="Document converted to FHIR successfully",
            correlation_id=correlation_id,
            request=request,
            document_id=document_id,
            patient_id=result.get("patient_id"),
            resource_counts=result.get("fhir_resources", {}).keys()
        )
        
        # Audit log
        if audit_service:
            await audit_service.record_event(
                action="C",
                patient_id=result["patient_id"],
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Document converted to FHIR resources",
                event_type="document_fhir_conversion",
            )
        
        return {
            "status": "success",
            "document_id": result["document_id"],
            "patient_id": result["patient_id"],
            "fhir_resources": result["fhir_resources"],
            "resource_counts": {
                "observations": len(result["fhir_resources"].get("observations", [])),
                "medications": len(result["fhir_resources"].get("medication_statements", [])),
                "conditions": len(result["fhir_resources"].get("conditions", [])),
            },
            "message": "FHIR resources created. Use FHIR connector to submit to FHIR server.",
        }
    
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "convert_document_to_fhir", "document_id": document_id},
            correlation_id,
            request
        )


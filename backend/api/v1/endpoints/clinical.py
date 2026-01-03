from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
import uuid

from backend.models import (
    QueryResponse,
    FeedbackResponse,
    AdapterStatusResponse,
    ActivateAdapterResponse,
)
from backend.security import TokenContext, auth_dependency
from backend.di import (
    get_llm_engine,
    get_rag_fusion,
    get_optional_rag_fusion,
    get_aot_reasoner,
    get_fhir_connector,
    get_audit_service,
    get_optional_audit_service,
    get_optional_mlc_learning,
    get_s_lora_manager,
    get_optional_s_lora_manager,
)
from backend.llm_engine import LLMEngine
from backend.rag_fusion import RAGFusion
from backend.aot_reasoner import AoTReasoner
from backend.mlc_learning import MLCLearning
from backend.audit_service import AuditService
from backend.fhir_connector import FhirResourceService
from backend.s_lora_manager import SLoRAManager
from backend.utils.validation import validate_patient_id, validate_query_string
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.utils.i18n import get_language_from_request, translate, DEFAULT_LANGUAGE

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def medical_query(
    request: Request,
    question: str,
    patient_id: Optional[str] = None,
    include_reasoning: bool = True,
    llm_engine: LLMEngine = Depends(get_llm_engine),
    rag_fusion: RAGFusion = Depends(get_rag_fusion),
    aot_reasoner: AoTReasoner = Depends(get_aot_reasoner),
    fhir_connector: FhirResourceService = Depends(get_fhir_connector),
    audit_service: Optional[AuditService] = Depends(get_optional_audit_service),
):
    """
    Query the AI for medical insights and recommendations
    """
    correlation_id = get_correlation_id(request)

    # Validate patient_id early if provided
    validated_patient_id = None
    if patient_id:
        try:
            validated_patient_id = validate_patient_id(patient_id)
        except HTTPException:
            # Re-raise validation errors immediately
            raise

    # Validate question input
    try:
        question = validate_query_string(question, max_length=2000)
    except HTTPException:
        raise

    try:
        log_structured(
            level="info",
            message="Processing medical query",
            correlation_id=correlation_id,
            request=request,
            patient_id=validated_patient_id,
            include_reasoning=include_reasoning,
            question_length=len(question)
        )

        # Get patient context if provided
        patient_context = None
        if validated_patient_id:
            (
                access_token,
                scopes,
                _existing_patient,
                user_context,
            ) = fhir_connector.client.get_effective_context()

            async with fhir_connector.request_context(
                access_token, scopes, validated_patient_id, user_context
            ):
                patient_context = await fhir_connector.get_patient(validated_patient_id)
        
        # Get language preference from request
        language = get_language_from_request(request)
        
        # Generate response with RAG and AoT
        response = await llm_engine.query_with_rag(
            question=question,
            patient_context=patient_context,
            rag_component=rag_fusion,
            aot_reasoner=aot_reasoner,
            include_reasoning=include_reasoning,
            language=language
        )
        
        result = {
            "status": "success",
            "question": question,
            "answer": response.get("answer"),
            "reasoning": response.get("reasoning") if include_reasoning else None,
            "sources": response.get("sources"),
            "confidence": response.get("confidence")
        }

        log_structured(
            level="info",
            message="Medical query processed successfully",
            correlation_id=correlation_id,
            request=request,
            patient_id=validated_patient_id,
            confidence=response.get("confidence"),
            has_sources=bool(response.get("sources"))
        )

        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=validated_patient_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Medical query processed",
                event_type="question",
            )

        return result

    except HTTPException as exc:
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=validated_patient_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(exc.detail),
                event_type="question",
            )
        raise
    except Exception as e:
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=validated_patient_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(e),
                event_type="question",
            )
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "medical_query", "patient_id": validated_patient_id},
            correlation_id,
            request
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def provide_feedback(
    request: Request,
    query_id: str,
    feedback_type: str,  # "positive", "negative", "correction"
    corrected_text: Optional[str] = None,
    mlc_learning: Optional[MLCLearning] = Depends(get_optional_mlc_learning),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Provide feedback for MLC (Meta-Learning for Compositionality) adaptation
    """
    correlation_id = get_correlation_id(request)

    try:
        if not mlc_learning:
            raise create_http_exception(
                message="MLC learning system not initialized",
                status_code=503,
                error_type="ServiceUnavailable"
            )
        
        # Validate feedback_type
        valid_feedback_types = ["positive", "negative", "correction"]
        if feedback_type not in valid_feedback_types:
            raise create_http_exception(
                message=f"Invalid feedback type. Must be one of: {', '.join(valid_feedback_types)}",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Validate corrected_text if provided
        if corrected_text:
            corrected_text = validate_query_string(corrected_text, max_length=5000)
        
        log_structured(
            level="info",
            message="Processing feedback",
            correlation_id=correlation_id,
            request=request,
            query_id=query_id,
            feedback_type=feedback_type
        )
        
        await mlc_learning.process_feedback(
            query_id=query_id,
            feedback_type=feedback_type,
            corrected_text=corrected_text
        )
        
        log_structured(
            level="info",
            message="Feedback processed successfully",
            correlation_id=correlation_id,
            request=request,
            query_id=query_id,
            feedback_type=feedback_type
        )
        
        return {
            "status": "success",
            "message": "Feedback processed and learning model updated",
            "query_id": query_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "provide_feedback", "query_id": query_id, "feedback_type": feedback_type},
            correlation_id,
            request
        )



@router.post("/adapters/activate", response_model=ActivateAdapterResponse)
async def activate_adapter(
    request: Request,
    adapter_name: str,
    specialty: Optional[str] = None,
    s_lora_manager: SLoRAManager = Depends(get_s_lora_manager),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Activate a specific LoRA adapter for a specialty
    """
    correlation_id = get_correlation_id(request)

    try:
        # Validate adapter_name (basic validation)
        if not adapter_name or len(adapter_name) > 255:
            raise create_http_exception(
                message="Invalid adapter name",
                status_code=400,
                error_type="ValidationError"
            )
        
        log_structured(
            level="info",
            message="Activating adapter",
            correlation_id=correlation_id,
            request=request,
            adapter_name=adapter_name,
            specialty=specialty
        )
        
        result = await s_lora_manager.activate_adapter(adapter_name, specialty)
        
        log_structured(
            level="info",
            message="Adapter activated successfully",
            correlation_id=correlation_id,
            request=request,
            adapter_name=adapter_name,
            active=result
        )
        
        return {
            "status": "success",
            "adapter": adapter_name,
            "active": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "activate_adapter", "adapter_name": adapter_name, "specialty": specialty},
            correlation_id,
            request
        )

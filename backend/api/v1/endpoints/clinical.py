from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
import uuid
import logging

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
from backend.utils.validation import validate_patient_id

logger = logging.getLogger(__name__)

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
    correlation_id = getattr(request.state, "correlation_id", None)
    if not correlation_id:
        correlation_id = (
            audit_service.new_correlation_id() if audit_service else uuid.uuid4().hex
        )

    try:
        logger.info(f"Processing medical query: {question}")

        # Get patient context if provided
        patient_context = None
        if patient_id:
            # Validate patient_id format
            validated_patient_id = validate_patient_id(patient_id)
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
        
        # Generate response with RAG and AoT
        response = await llm_engine.query_with_rag(
            question=question,
            patient_context=patient_context,
            rag_component=rag_fusion,
            aot_reasoner=aot_reasoner,
            include_reasoning=include_reasoning
        )
        
        result = {
            "status": "success",
            "question": question,
            "answer": response.get("answer"),
            "reasoning": response.get("reasoning") if include_reasoning else None,
            "sources": response.get("sources"),
            "confidence": response.get("confidence")
        }

        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=validated_patient_id if patient_id else None,
                user_context=None,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Medical query processed",
                event_type="question",
            )

        return result

    except HTTPException as exc:
        if audit_service:
            validated_id = validate_patient_id(patient_id) if patient_id else None
            await audit_service.record_event(
                action="E",
                patient_id=validated_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(exc.detail),
                event_type="question",
            )
        raise
    except Exception as e:
        logger.error("Error processing query [%s]: %s", correlation_id, str(e))
        if audit_service:
            try:
                validated_id = validate_patient_id(patient_id) if patient_id else None
            except:
                validated_id = None
            await audit_service.record_event(
                action="E",
                patient_id=validated_id,
                user_context=None,
                correlation_id=correlation_id,
                outcome="8",
                outcome_desc=str(e),
                event_type="question",
            )
        raise HTTPException(status_code=500, detail=str(e))


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
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        if not mlc_learning:
            raise HTTPException(status_code=503, detail="MLC learning system not initialized")
        
        logger.info(f"Receiving feedback for query {query_id}: {feedback_type}")
        
        await mlc_learning.process_feedback(
            query_id=query_id,
            feedback_type=feedback_type,
            corrected_text=corrected_text
        )
        
        return {
            "status": "success",
            "message": "Feedback processed and learning model updated",
            "query_id": query_id
        }
    except HTTPException as exc:
        logger.error("Error processing feedback [%s]: %s", correlation_id, str(exc))
        raise exc
    except Exception as e:
        logger.error("Error processing feedback [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))



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
    correlation_id = getattr(
        request.state, "correlation_id", audit_service.new_correlation_id() if audit_service else ""
    )

    try:
        result = await s_lora_manager.activate_adapter(adapter_name, specialty)
        
        return {
            "status": "success",
            "adapter": adapter_name,
            "active": result
        }
        
    except Exception as e:
        logger.error("Error activating adapter [%s]: %s", correlation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))

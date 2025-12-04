"""
Healthcare AI Assistant - Main Application Entry Point
Integrates FHIR data with advanced AI techniques (S-LoRA, MLC, RAG, AoT)
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional
import uvicorn
import os
from dotenv import load_dotenv
from security import TokenContext, auth_dependency

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core modules (to be implemented)
from fhir_connector import FHIRConnector
from llm_engine import LLMEngine
from rag_fusion import RAGFusion
from s_lora_manager import SLoRAManager
from mlc_learning import MLCLearning
from aot_reasoner import AoTReasoner
from patient_analyzer import PatientAnalyzer

# Global instances
fhir_connector = None
llm_engine = None
rag_fusion = None
s_lora_manager = None
mlc_learning = None
aot_reasoner = None
patient_analyzer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management - startup and shutdown
    """
    # Startup
    logger.info("Initializing Healthcare AI Assistant...")
    try:
        global fhir_connector, llm_engine, rag_fusion, s_lora_manager, mlc_learning, aot_reasoner, patient_analyzer
        
        # Initialize core components
        logger.info("Loading FHIR Connector...")
        fhir_connector = FHIRConnector(
            server_url=os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir"),
            client_id=os.getenv("SMART_CLIENT_ID", ""),
            client_secret=os.getenv("SMART_CLIENT_SECRET", ""),
            scope=os.getenv(
                "SMART_SCOPE", "system/*.read patient/*.read user/*.read"
            ),
            auth_url=os.getenv("SMART_AUTH_URL") or None,
            token_url=os.getenv("SMART_TOKEN_URL") or None,
            well_known_url=os.getenv("SMART_WELL_KNOWN") or None,
            audience=os.getenv("SMART_AUDIENCE") or None,
            refresh_token=os.getenv("SMART_REFRESH_TOKEN") or None,
        )
        
        logger.info("Loading LLM Engine...")
        llm_engine = LLMEngine(
            model_name=os.getenv("LLM_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        
        logger.info("Loading RAG-Fusion Component...")
        rag_fusion = RAGFusion(
            knowledge_base_path=os.getenv("KB_PATH", "./data/medical_kb"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
        
        logger.info("Loading S-LoRA Manager...")
        s_lora_manager = SLoRAManager(
            adapter_path=os.getenv("ADAPTER_PATH", "./models/adapters"),
            base_model=os.getenv("BASE_MODEL", "meta-llama/Llama-2-7b-hf")
        )
        
        logger.info("Loading MLC Learning System...")
        mlc_learning = MLCLearning(
            learning_rate=float(os.getenv("MLC_LEARNING_RATE", "0.001")),
            feedback_history_path=os.getenv("FEEDBACK_PATH", "./data/feedback")
        )
        
        logger.info("Loading Algorithm of Thought Reasoner...")
        aot_reasoner = AoTReasoner(
            reasoning_depth=int(os.getenv("REASONING_DEPTH", "3"))
        )
        
        logger.info("Initializing Patient Analyzer...")
        patient_analyzer = PatientAnalyzer(
            fhir_connector=fhir_connector,
            llm_engine=llm_engine,
            rag_fusion=rag_fusion,
            s_lora_manager=s_lora_manager,
            aot_reasoner=aot_reasoner,
            mlc_learning=mlc_learning
        )
        
        logger.info("✓ Healthcare AI Assistant initialized successfully")
        
    except Exception as e:
        logger.error(f"Initialization error: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Healthcare AI Assistant...")
    # Add cleanup code here if needed
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Healthcare AI Assistant",
    description="AI-powered healthcare application with FHIR integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API ENDPOINTS ====================

@app.get("/api/v1/health")
async def health_check(
    auth: TokenContext = Depends(auth_dependency())
):
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "Healthcare AI Assistant",
        "version": "1.0.0"
    }


@app.post("/api/v1/analyze-patient")
async def analyze_patient(
    fhir_patient_id: str,
    include_recommendations: bool = True,
    specialty: Optional[str] = None,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """
    Analyze a patient's FHIR records and generate insights
    
    Parameters:
    - fhir_patient_id: Patient ID in FHIR system
    - include_recommendations: Include clinical decision support
    - specialty: Target medical specialty for analysis
    """
    try:
        if not patient_analyzer:
            raise HTTPException(status_code=503, detail="Patient analyzer not initialized")
        
        logger.info(f"Analyzing patient: {fhir_patient_id}")
        
        if auth.patient and auth.patient != fhir_patient_id:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a different patient context",
            )

        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            result = await patient_analyzer.analyze(
                patient_id=fhir_patient_id,
                include_recommendations=include_recommendations,
                specialty=specialty
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing patient: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/patient/{patient_id}/fhir")
async def get_patient_fhir(
    patient_id: str,
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read", "system/*.read"})
    ),
):
    """
    Fetch patient's FHIR data from connected EHR
    """
    try:
        if not fhir_connector:
            raise HTTPException(status_code=503, detail="FHIR connector not initialized")
        
        if auth.patient and auth.patient != patient_id:
            raise HTTPException(
                status_code=403,
                detail="Token is scoped to a different patient context",
            )

        async with fhir_connector.request_context(
            auth.access_token, auth.scopes, auth.patient
        ):
            patient_data = await fhir_connector.get_patient(patient_id)
        
        return {
            "status": "success",
            "patient_id": patient_id,
            "data": patient_data
        }
        
    except Exception as e:
        logger.error(f"Error fetching patient FHIR data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query")
async def medical_query(
    question: str,
    patient_id: Optional[str] = None,
    include_reasoning: bool = True
):
    """
    Query the AI for medical insights and recommendations
    """
    try:
        if not llm_engine or not rag_fusion:
            raise HTTPException(status_code=503, detail="AI engine not initialized")
        
        logger.info(f"Processing medical query: {question}")
        
        # Get patient context if provided
        patient_context = None
        if patient_id:
            patient_context = await fhir_connector.get_patient(patient_id)
        
        # Generate response with RAG and AoT
        response = await llm_engine.query_with_rag(
            question=question,
            patient_context=patient_context,
            rag_component=rag_fusion,
            aot_reasoner=aot_reasoner,
            include_reasoning=include_reasoning
        )
        
        return {
            "status": "success",
            "question": question,
            "answer": response.get("answer"),
            "reasoning": response.get("reasoning") if include_reasoning else None,
            "sources": response.get("sources"),
            "confidence": response.get("confidence")
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/feedback")
async def provide_feedback(
    query_id: str,
    feedback_type: str,  # "positive", "negative", "correction"
    corrected_text: Optional[str] = None
):
    """
    Provide feedback for MLC (Meta-Learning for Compositionality) adaptation
    """
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
        
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/adapters")
async def get_adapters_status():
    """
    Get S-LoRA adapter status and memory usage
    """
    try:
        if not s_lora_manager:
            raise HTTPException(status_code=503, detail="S-LoRA manager not initialized")
        
        status = await s_lora_manager.get_status()
        
        return {
            "status": "success",
            "active_adapters": status.get("active"),
            "available_adapters": status.get("available"),
            "memory_usage": status.get("memory"),
            "specialties": status.get("specialties")
        }
        
    except Exception as e:
        logger.error(f"Error fetching adapter status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/adapters/activate")
async def activate_adapter(adapter_name: str, specialty: Optional[str] = None):
    """
    Activate a specific LoRA adapter for a specialty
    """
    try:
        if not s_lora_manager:
            raise HTTPException(status_code=503, detail="S-LoRA manager not initialized")
        
        result = await s_lora_manager.activate_adapter(adapter_name, specialty)
        
        return {
            "status": "success",
            "adapter": adapter_name,
            "active": result
        }
        
    except Exception as e:
        logger.error(f"Error activating adapter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats")
async def get_system_stats():
    """
    Get system statistics and performance metrics
    """
    try:
        stats = {
            "llm": llm_engine.get_stats() if llm_engine else None,
            "rag": rag_fusion.get_stats() if rag_fusion else None,
            "s_lora": s_lora_manager.get_stats() if s_lora_manager else None,
            "mlc": mlc_learning.get_stats() if mlc_learning else None,
        }
        
        return {
            "status": "success",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ERROR HANDLERS ====================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    Global exception handler
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "status": "error",
        "detail": "An unexpected error occurred",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


# ==================== MAIN ====================

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting Healthcare AI Assistant on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )

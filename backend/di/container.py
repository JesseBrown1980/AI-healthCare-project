import logging
import os
from typing import Optional

from backend.audit_service import AuditService
from backend.fhir_http_client import FhirHttpClient
from backend.fhir_resource_service import FhirResourceService
from backend.llm_engine import LLMEngine
from backend.rag_fusion import RAGFusion
from backend.s_lora_manager import SLoRAManager
from backend.mlc_learning import MLCLearning
from backend.aot_reasoner import AoTReasoner
from backend.notifier import Notifier
from backend.patient_analyzer import PatientAnalyzer
from backend.analysis_cache import AnalysisJobManager
from backend.security import close_shared_async_client

logger = logging.getLogger(__name__)


class ServiceContainer:
    def __init__(
        self,
        *,
        notifications_enabled: bool,
        analysis_history_limit: int,
        analysis_history_ttl_seconds: int,
        analysis_cache_ttl_seconds: int,
    ) -> None:
        self.notifications_enabled = notifications_enabled
        self.analysis_history_limit = analysis_history_limit
        self.analysis_history_ttl_seconds = analysis_history_ttl_seconds
        self.analysis_cache_ttl_seconds = analysis_cache_ttl_seconds

        self.fhir_client: Optional[FhirHttpClient] = None
        self.fhir_connector: Optional[FhirResourceService] = None
        self.llm_engine: Optional[LLMEngine] = None
        self.rag_fusion: Optional[RAGFusion] = None
        self.s_lora_manager: Optional[SLoRAManager] = None
        self.mlc_learning: Optional[MLCLearning] = None
        self.aot_reasoner: Optional[AoTReasoner] = None
        self.notifier: Optional[Notifier] = None
        self.patient_analyzer: Optional[PatientAnalyzer] = None
        self.analysis_job_manager: Optional[AnalysisJobManager] = None
        self.audit_service: Optional[AuditService] = None

    async def startup(self) -> None:
        logger.info("Loading FHIR HTTP client and resource service...")
        self.fhir_client = FhirHttpClient(
            server_url=os.getenv("FHIR_SERVER_URL", "http://localhost:8080/fhir"),
            vendor=os.getenv("EHR_VENDOR", "generic"),
            client_id=os.getenv("SMART_CLIENT_ID", ""),
            client_secret=os.getenv("SMART_CLIENT_SECRET", ""),
            scope=os.getenv("SMART_SCOPE", "system/*.read patient/*.read user/*.read"),
            auth_url=os.getenv("SMART_AUTH_URL") or None,
            token_url=os.getenv("SMART_TOKEN_URL") or None,
            well_known_url=os.getenv("SMART_WELL_KNOWN") or None,
            audience=os.getenv("SMART_AUDIENCE") or None,
            refresh_token=os.getenv("SMART_REFRESH_TOKEN") or None,
        )
        self.fhir_connector = FhirResourceService(self.fhir_client)

        logger.info("Loading LLM Engine...")
        self.llm_engine = LLMEngine(
            model_name=os.getenv("LLM_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
        )

        logger.info("Loading RAG-Fusion Component...")
        self.rag_fusion = RAGFusion(
            knowledge_base_path=os.getenv("KB_PATH", "./data/medical_kb"),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
        )

        logger.info("Loading S-LoRA Manager...")
        self.s_lora_manager = SLoRAManager(
            adapter_path=os.getenv("ADAPTER_PATH", "./models/adapters"),
            base_model=os.getenv("BASE_MODEL", "meta-llama/Llama-2-7b-hf"),
        )

        logger.info("Loading MLC Learning System...")
        self.mlc_learning = MLCLearning(
            learning_rate=float(os.getenv("MLC_LEARNING_RATE", "0.001")),
            feedback_history_path=os.getenv("FEEDBACK_PATH", "./data/feedback"),
        )

        logger.info("Loading Algorithm of Thought Reasoner...")
        self.aot_reasoner = AoTReasoner(
            reasoning_depth=int(os.getenv("REASONING_DEPTH", "3"))
        )

        logger.info("Loading Notifier...")
        self.notifier = Notifier()

        logger.info("Initializing Patient Analyzer...")
        self.patient_analyzer = PatientAnalyzer(
            fhir_connector=self.fhir_connector,
            llm_engine=self.llm_engine,
            rag_fusion=self.rag_fusion,
            s_lora_manager=self.s_lora_manager,
            aot_reasoner=self.aot_reasoner,
            mlc_learning=self.mlc_learning,
            notifier=self.notifier,
            notifications_enabled=self.notifications_enabled,
            history_limit=self.analysis_history_limit,
            history_ttl_seconds=self.analysis_history_ttl_seconds,
        )

        self.analysis_job_manager = AnalysisJobManager(
            ttl_seconds=self.analysis_cache_ttl_seconds
        )

        logger.info("Initializing Audit Service...")
        self.audit_service = AuditService(fhir_connector=self.fhir_connector)

    async def shutdown(self) -> None:
        if self.fhir_client and self.fhir_client.session:
            if not self.fhir_client.session.is_closed:
                await self.fhir_client.session.aclose()
            self.fhir_client.session = None

        await close_shared_async_client()

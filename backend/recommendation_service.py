import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.llm_engine import LLMEngine
    from backend.rag_fusion import RAGFusion
    from backend.aot_reasoner import AoTReasoner
    from backend.mlc_learning import MLCLearning

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating clinical recommendations."""

    def __init__(
        self,
        llm_engine: "LLMEngine",
        rag_fusion: "RAGFusion",
        aot_reasoner: "AoTReasoner",
        mlc_learning: "MLCLearning",
    ) -> None:
        """
        Initialize RecommendationService.
        
        Args:
            llm_engine: LLM engine for generating recommendations
            rag_fusion: RAG fusion component for knowledge retrieval
            aot_reasoner: Algorithm of Thought reasoner
            mlc_learning: Meta-Learning for Compositionality learning component
        """
        self.llm_engine = llm_engine
        self.rag_fusion = rag_fusion
        self.aot_reasoner = aot_reasoner
        self.mlc_learning = mlc_learning

    async def generate_recommendations(
        self,
        patient_data: Dict[str, Any],
        summary: Dict[str, Any],
        alerts: List[Dict[str, Any]],
        risk_scores: Dict[str, Any],
        adapters: List[str],
        focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate clinical recommendations using LLM with RAG and AoT."""

        del summary, risk_scores, adapters  # currently unused but retained for interface completeness

        recommendations = {
            "clinical_recommendations": [],
            "reasoning_chains": [],
            "evidence_citations": [],
            "priority_actions": [],
        }

        try:
            task_type = focus or "patient_analysis"
            await self.mlc_learning.compose_for_task(task_type)

            queries = [
                f"What are the main clinical priorities for this patient with {len(patient_data.get('conditions', []))} conditions?",
                "Given the alerts identified, what immediate actions should be taken?",
                "What preventive measures would be most impactful for this patient?",
            ]

            for query in queries:
                reasoning_chain = await self.aot_reasoner.generate_reasoning_chain(
                    question=query, context=patient_data
                )
                recommendations["reasoning_chains"].append(reasoning_chain)

                await self.rag_fusion.retrieve_relevant_knowledge(query)

                llm_response = await self.llm_engine.query_with_rag(
                    question=query,
                    patient_context=patient_data,
                    rag_component=self.rag_fusion,
                    aot_reasoner=self.aot_reasoner,
                    include_reasoning=True,
                    language=language,
                )

                recommendations["clinical_recommendations"].append(
                    {
                        "query": query,
                        "recommendation": llm_response.get("answer"),
                        "confidence": llm_response.get("confidence"),
                        "sources": llm_response.get("sources"),
                    }
                )

                recommendations["evidence_citations"].extend(llm_response.get("sources", []))

            recommendations["priority_actions"] = [
                {"priority": 1, "action": alert["message"], "severity": alert["severity"]}
                for alert in alerts[:3]
            ]

            return recommendations
        except Exception as exc:
            logger.error("Error generating recommendations: %s", exc)
            return {
                "clinical_recommendations": [],
                "reasoning_chains": [],
                "evidence_citations": [],
                "error": str(exc),
            }

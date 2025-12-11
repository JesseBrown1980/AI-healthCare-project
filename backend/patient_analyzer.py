"""
Patient Analyzer Module
Central orchestration of all AI components for comprehensive patient analysis
Combines FHIR data, LLM intelligence, RAG knowledge, S-LoRA adaptation, MLC learning, and AoT reasoning
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .alert_service import AlertService
from .fhir_connector import FHIRConnectorError
from .notification_service import NotificationService
from .patient_data_service import PatientDataService
from .recommendation_service import RecommendationService
from .risk_scoring_service import RiskScoringService

logger = logging.getLogger(__name__)


class PatientAnalyzer:
    """
    Central analysis engine that orchestrates all healthcare AI components
    Provides comprehensive patient analysis and clinical decision support
    """

    def __init__(
        self,
        fhir_connector,
        llm_engine,
        rag_fusion,
        s_lora_manager,
        aot_reasoner,
        mlc_learning,
        notifier=None,
        notifications_enabled: bool = False,
        patient_data_service: Optional[PatientDataService] = None,
        risk_scoring_service: Optional[RiskScoringService] = None,
        recommendation_service: Optional[RecommendationService] = None,
        alert_service: Optional[AlertService] = None,
        notification_service: Optional[NotificationService] = None,
        history_limit: Optional[int] = None,
    ):
        """
        Initialize PatientAnalyzer with all components

        Args:
            fhir_connector: FHIR data integration module
            llm_engine: Language model interface
            rag_fusion: Retrieval-augmented generation
            s_lora_manager: Sparse LoRA adapter management
            aot_reasoner: Algorithm of Thought reasoning engine
            mlc_learning: Meta-learning for compositionality
        """
        self.fhir_connector = fhir_connector
        self.llm_engine = llm_engine
        self.rag_fusion = rag_fusion
        self.s_lora_manager = s_lora_manager
        self.aot_reasoner = aot_reasoner
        self.mlc_learning = mlc_learning

        self.patient_data_service = patient_data_service or PatientDataService(
            fhir_connector
        )
        self.risk_scoring_service = risk_scoring_service or RiskScoringService()
        self.recommendation_service = recommendation_service or RecommendationService(
            llm_engine, rag_fusion, aot_reasoner, mlc_learning
        )
        self.alert_service = alert_service or AlertService()
        self.notification_service = notification_service or NotificationService(
            notifier, notifications_enabled
        )

        self.analysis_history: List[Dict] = []
        self.history_limit = history_limit

        logger.info("PatientAnalyzer initialized with all components")

    async def _generate_summary(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.patient_data_service:
            return {}
        return await self.patient_data_service.generate_summary(patient_data)

    async def _identify_alerts(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.alert_service:
            return []
        return await self.alert_service.identify_alerts(patient_data)

    def _highest_alert_severity(self, alerts: List[Dict[str, Any]]) -> Optional[str]:
        if not self.alert_service:
            return None
        return self.alert_service.highest_alert_severity(alerts)

    async def _calculate_risk_scores(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.risk_scoring_service:
            return {}
        return await self.risk_scoring_service.calculate_risk_scores(patient_data)

    async def _medication_review(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.risk_scoring_service:
            return {}
        return await self.risk_scoring_service.review_medications(patient_data)

    async def _generate_recommendations(self, *, patient_data, summary, alerts, risk_scores, adapters, focus):
        if not self.recommendation_service:
            return []
        return await self.recommendation_service.generate_recommendations(
            patient_data=patient_data,
            summary=summary,
            alerts=alerts,
            risk_scores=risk_scores,
            adapters=adapters,
            focus=focus,
        )

    async def _record_for_learning(self, patient_id: str, result: Dict[str, Any]) -> None:
        if not self.mlc_learning:
            return
        await self.mlc_learning.record_feedback(patient_id, result)

    async def analyze(
        self,
        patient_id: str,
        include_recommendations: bool = True,
        specialty: Optional[str] = None,
        analysis_focus: Optional[str] = None,
        notify: bool = False,
        correlation_id: str = "",
    ) -> Dict[str, Any]:
        """
        Comprehensive patient analysis using all AI components

        Args:
            patient_id: FHIR patient ID
            include_recommendations: Include clinical decision support
            specialty: Target medical specialty
            analysis_focus: Specific focus area (e.g., "medication_review", "risk_assessment")

        Returns:
            Comprehensive analysis including summary, alerts, recommendations
        """
        logger.info("Starting analysis for patient %s", patient_id)
        analysis_start = datetime.now(timezone.utc)

        try:
            result = {
                "patient_id": patient_id,
                "analysis_timestamp": analysis_start.isoformat(),
                "status": "in_progress",
            }

            # 1. FETCH PATIENT DATA (FHIR)
            logger.info("Step 1: Fetching FHIR data...")
            patient_data = await self.patient_data_service.fetch_patient_data(
                patient_id
            )
            result["patient_data"] = patient_data

            # 2. DETERMINE SPECIALTIES (S-LoRA)
            logger.info("Step 2: Determining relevant specialties...")
            specialties = [specialty] if specialty else []
            selected_adapters = await self.s_lora_manager.select_adapters(
                specialties=specialties, patient_data=patient_data
            )

            for adapter in selected_adapters[:3]:  # Limit to top 3 for efficiency
                await self.s_lora_manager.activate_adapter(adapter)

            result["active_specialties"] = [
                self.s_lora_manager.adapters[a].get("specialty")
                for a in selected_adapters[:3]
            ]

            # 3. GENERATE PATIENT SUMMARY
            logger.info("Step 3: Generating patient summary...")
            summary = await self._generate_summary(patient_data)
            result["summary"] = summary

            # 4. IDENTIFY ALERTS
            logger.info("Step 4: Identifying clinical alerts...")
            alerts = await self._identify_alerts(patient_data)
            result["alerts"] = alerts
            result["alert_count"] = len(alerts)
            result["highest_alert_severity"] = self._highest_alert_severity(alerts)

            # 5. CALCULATE RISK SCORES
            logger.info("Step 5: Calculating risk scores...")
            risk_scores = await self._calculate_risk_scores(patient_data)
            result["risk_scores"] = risk_scores
            result["overall_risk_score"] = self.risk_scoring_service.derive_overall_risk_score(
                risk_scores
            )
            result["polypharmacy_risk"] = risk_scores.get("polypharmacy_risk", False)

            # 6. MEDICATION REVIEW
            logger.info("Step 6: Reviewing medications...")
            medication_review = await self._medication_review(patient_data)
            result["medication_review"] = medication_review

            # 7. GENERATE RECOMMENDATIONS (if requested)
            if include_recommendations:
                logger.info("Step 7: Generating clinical recommendations...")
                recommendations = await self._generate_recommendations(
                    patient_data=patient_data,
                    summary=summary,
                    alerts=alerts,
                    risk_scores=risk_scores,
                    adapters=selected_adapters,
                    focus=analysis_focus,
                )
                result["recommendations"] = recommendations

            # 8. APPLY MLC LEARNING
            logger.info("Step 8: Recording for meta-learning...")
            await self._record_for_learning(patient_id, result)

            # 9. COMPILE FINAL ANALYSIS
            analysis_end = datetime.now(timezone.utc)
            result["analysis_duration_seconds"] = (
                analysis_end - analysis_start
            ).total_seconds()
            result["last_analyzed_at"] = analysis_end.isoformat()
            result["status"] = "completed"

            self._add_to_history(result)

            logger.info(
                "Analysis completed for patient %s in %.2fs",
                patient_id,
                result["analysis_duration_seconds"],
            )

            await self.notification_service.notify_if_needed(
                result, correlation_id, notify
            )

            return result

        except FHIRConnectorError as e:
            logger.error(
                "FHIR connector error analyzing patient %s: %s", patient_id, str(e)
            )
            return {
                "patient_id": patient_id,
                "status": "error",
                "error_type": e.error_type,
                "message": e.message,
                "correlation_id": e.correlation_id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:  # pragma: no cover - defensive logging
            logger.error("Error analyzing patient %s: %s", patient_id, str(e))
            return {
                "patient_id": patient_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _record_for_learning(self, patient_id: str, analysis: Dict):
        """Record analysis for MLC learning and feedback"""
        logger.info("Recording analysis for MLC learning: %s", patient_id)

    def _add_to_history(self, analysis: Dict[str, Any]) -> None:
        """Add an analysis result to history while enforcing limits."""

        self.analysis_history.append(analysis)

        if self.history_limit is not None and self.history_limit > 0:
            excess = len(self.analysis_history) - self.history_limit
            if excess > 0:
                del self.analysis_history[:excess]

    def clear_history(self) -> None:
        """Remove all cached analyses to reclaim memory."""

        self.analysis_history.clear()

    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "total_analyses": len(self.analysis_history),
            "successful_analyses": sum(
                1 for a in self.analysis_history if a.get("status") == "completed"
            ),
            "average_analysis_time": sum(
                a.get("analysis_duration_seconds", 0) for a in self.analysis_history
            )
            / max(len(self.analysis_history), 1),
        }

    @staticmethod
    def _calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
        """Deprecated wrapper retained for backward compatibility."""

        return PatientDataService._calculate_age(birth_date_str)

"""
Patient Analyzer Module
Central orchestration of all AI components for comprehensive patient analysis
Combines FHIR data, LLM intelligence, RAG knowledge, S-LoRA adaptation, MLC learning, and AoT reasoning
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# New Service Imports
from .analysis.alert_service import AlertService
from .analysis.history_service import HistoryService

from .fhir_connector import FHIRConnectorError
from .notification_service import NotificationService
from .patient_data_service import PatientDataService
from .recommendation_service import RecommendationService
from .risk_scoring_service import RiskScoringService

if TYPE_CHECKING:
    from .database.service import DatabaseService

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
        history_service: Optional[HistoryService] = None,
        database_service: Optional["DatabaseService"] = None,
        anomaly_service: Optional[Any] = None,
        # Legacy params kept for compatibility but preferred via HistoryService
        history_limit: Optional[int] = None,
        history_ttl_seconds: Optional[int] = None,
    ):
        """
        Initialize PatientAnalyzer with all components
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
        self.database_service = database_service
        self.anomaly_service = anomaly_service

        # Initialize History Service
        self.history_service = history_service or HistoryService(
            database_service=database_service,
            history_limit=history_limit,
            history_ttl_seconds=history_ttl_seconds
        )

        if self.anomaly_service:
            logger.info("PatientAnalyzer initialized with GNN anomaly detection")
        else:
            logger.info("PatientAnalyzer initialized without anomaly detection (optional)")

    async def _generate_summary(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.patient_data_service:
            return {}
        return await self.patient_data_service.generate_summary(patient_data)

    async def _identify_alerts(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.alert_service.identify_alerts(patient_data)

    @staticmethod
    def _highest_alert_severity(alerts: List[Dict[str, Any]]) -> Optional[str]:
        """Return the highest alert severity from a list of alerts."""
        return AlertService.highest_alert_severity(alerts)

    @staticmethod
    def _derive_overall_risk_score(risk_scores: Dict[str, Any]) -> Optional[float]:
        """Fallback helper mirroring RiskScoringService logic for convenience."""
        if not risk_scores:
            return None
        return RiskScoringService.derive_overall_risk_score(risk_scores)

    async def _calculate_risk_scores(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.risk_scoring_service:
            return {}
        return await self.risk_scoring_service.calculate_risk_scores(patient_data)

    async def _medication_review(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.risk_scoring_service:
            return {}
        return await self.risk_scoring_service.review_medications(patient_data)

    async def _generate_recommendations(self, *, patient_data, summary, alerts, risk_scores, adapters, focus, language="en"):
        if not self.recommendation_service:
            return []
        return await self.recommendation_service.generate_recommendations(
            patient_data=patient_data,
            summary=summary,
            alerts=alerts,
            risk_scores=risk_scores,
            adapters=adapters,
            focus=focus,
            language=language,
        )

    async def analyze(
        self,
        patient_id: str,
        include_recommendations: bool = True,
        specialty: Optional[str] = None,
        analysis_focus: Optional[str] = None,
        notify: bool = False,
        correlation_id: str = "",
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Comprehensive patient analysis using all AI components
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
            
            # 1a. ENRICH WITH OCR DATA (if available) - Logic retained
            if self.database_service:
                try:
                    logger.info("Step 1a: Fetching OCR-extracted data...")
                    ocr_resources = await self.database_service.get_ocr_fhir_resources_for_patient(
                        patient_id
                    )
                    
                    if ocr_resources:
                        # Existing merge logic...
                        existing_observations = patient_data.get("observations", [])
                        ocr_observations = ocr_resources.get("observations", [])
                        patient_data["observations"] = existing_observations + ocr_observations
                        
                        existing_medications = patient_data.get("medications", [])
                        ocr_medications = ocr_resources.get("medication_statements", [])
                        converted_medications = [
                            {
                                "medication": med.get("medicationCodeableConcept", {}).get("text", ""),
                                "status": med.get("status", "active"),
                                "dosage": med.get("dosage", [{}])[0].get("text", "") if med.get("dosage") else "",
                            }
                            for med in ocr_medications
                        ]
                        patient_data["medications"] = existing_medications + converted_medications
                        
                        existing_conditions = patient_data.get("conditions", [])
                        ocr_conditions = ocr_resources.get("conditions", [])
                        converted_conditions = [
                            {
                                "code": cond.get("code", {}).get("text", ""),
                                "status": cond.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
                            }
                            for cond in ocr_conditions
                        ]
                        patient_data["conditions"] = existing_conditions + converted_conditions
                        
                        logger.info(
                            "Merged OCR data: %d observations, %d medications, %d conditions",
                            len(ocr_observations),
                            len(ocr_medications),
                            len(ocr_conditions),
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch OCR data for patient %s: %s", patient_id, str(e)
                    )
            
            result["patient_data"] = patient_data

            # 2. DETERMINE SPECIALTIES (S-LoRA)
            logger.info("Step 2: Determining relevant specialties...")
            specialties = [specialty] if specialty else []
            selected_adapters = await self.s_lora_manager.select_adapters(
                specialties=specialties, patient_data=patient_data
            )

            for adapter in selected_adapters[:3]:
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

            # 6a. CLINICAL ANOMALY DETECTION (GNN-based)
            if self.anomaly_service:
                try:
                    logger.info("Step 6a: Running GNN-based clinical anomaly detection...")
                    anomaly_results = await self.anomaly_service.detect_clinical_anomalies(
                        patient_data,
                        threshold=0.5
                    )
                    result["gnn_anomaly_detection"] = anomaly_results
                    
                    high_severity_anomalies = [
                        a for a in anomaly_results.get("anomalies", [])
                        if a.get("severity") == "high"
                    ]
                    if high_severity_anomalies:
                        logger.warning(
                            "Detected %d high-severity clinical anomalies",
                            len(high_severity_anomalies)
                        )
                        for anomaly in high_severity_anomalies:
                            alerts.append({
                                "type": "gnn_anomaly",
                                "severity": "high",
                                "title": f"Clinical Anomaly: {anomaly.get('edge_type', 'unknown')}",
                                "description": (
                                    f"GNN detected unusual pattern in {anomaly.get('edge_type', 'relationship')} "
                                    f"(score: {anomaly.get('anomaly_score', 0):.2f})"
                                ),
                                "metadata": anomaly.get("metadata", {}),
                            })
                except Exception as e:
                    logger.error(f"Clinical anomaly detection failed: {e}", exc_info=True)
                    result["gnn_anomaly_detection"] = {
                        "error": str(e),
                        "message": "Anomaly detection failed"
                    }

            # 7. GENERATE RECOMMENDATIONS
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
            
            # Regulatory Disclaimer (REQ-09)
            result["regulatory_disclaimer"] = {
                "text": "This analysis is generated by an AI assistant and is NOT for primary diagnostic use. All recommendations must be verified by a qualified healthcare professional.",
                "classification": "Clinical Decision Support (CDS) Level 1",
                "references": ["FDA SaMD Guidance", "EU MDR Class IIa"],
                "version": "1.0.0"
            }

            result["status"] = "completed"

            # DELEGATED: Add to history via HistoryService
            await self.history_service.add_to_history(result)

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
                "FHIR connector error analyzing patient %s [%s]: %s",
                patient_id,
                correlation_id if correlation_id else "no-correlation-id",
                str(e),
            )
            return {
                "patient_id": patient_id,
                "status": "error",
                "error_type": e.error_type,
                "message": e.message,
                "correlation_id": e.correlation_id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(
                "Error analyzing patient %s [%s]: %s",
                patient_id,
                correlation_id if correlation_id else "no-correlation-id",
                str(e),
                exc_info=True,
            )
            return {
                "patient_id": patient_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _record_for_learning(self, patient_id: str, analysis: Dict[str, Any]):
        """Record analysis for MLC learning and feedback"""
        if not self.mlc_learning:
            logger.info("No MLC learning component configured; skipping record")
            return

        logger.info("Recording analysis for MLC learning: %s", patient_id)
        await self.mlc_learning.record_feedback(patient_id, analysis)

    # --- Delegated Methods ---

    async def _add_to_history(self, analysis: Dict[str, Any]) -> None:
        """Deprecated wrapper. Use history_service directly."""
        await self.history_service.add_to_history(analysis)

    def clear_history(self) -> None:
        """Remove all cached analyses to reclaim memory."""
        self.history_service.clear_history()

    def get_history(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return a copy of the analysis history for a patient or all patients."""
        return self.history_service.get_history(patient_id)

    async def get_latest_analysis(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest analysis for a specific patient."""
        return await self.history_service.get_latest_analysis(patient_id)

    def total_history_count(self) -> int:
        """Return the total number of cached analyses across all patients."""
        return self.history_service.total_history_count()

    def collect_recent_alerts(
        self,
        limit: int,
        patient_id: Optional[str] = None,
        roster_lookup: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate recent critical and high-severity alerts from analysis history.
        """
        history = self.history_service.get_history(patient_id)
        return self.alert_service.collect_recent_alerts(
            history, limit, patient_id, roster_lookup
        )

    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "total_analyses": self.history_service.total_history_count(),
            "successful_analyses": sum(
                1
                for a in self.history_service.get_history()
                if a.get("status") == "completed"
            ),
            "average_analysis_time": sum(
                a.get("analysis_duration_seconds", 0) for a in self.history_service.get_history()
            )
            / max(self.history_service.total_history_count(), 1),
        }

    def prune_stale_history(self) -> int:
        """Prune TTL-expired analyses across all patients."""
        return self.history_service.prune_stale_history()

    @staticmethod
    def _calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
        """Deprecated wrapper retained for backward compatibility."""
        return PatientDataService._calculate_age(birth_date_str)

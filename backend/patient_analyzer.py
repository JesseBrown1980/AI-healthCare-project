"""
Patient Analyzer Module
Central orchestration of all AI components for comprehensive patient analysis
Combines FHIR data, LLM intelligence, RAG knowledge, S-LoRA adaptation, MLC learning, and AoT reasoning
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .alert_service import AlertService
from .fhir_connector import FHIRConnectorError
from .notification_service import NotificationService
from .patient_data_service import PatientDataService
from .recommendation_service import RecommendationService
from .risk_scoring_service import RiskScoringService

if TYPE_CHECKING:
    from .database.service import DatabaseService

logger = logging.getLogger(__name__)


DEFAULT_HISTORY_LIMIT = 200
DEFAULT_HISTORY_TTL_SECONDS = 60 * 60 * 24


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
        history_ttl_seconds: Optional[int] = None,
        database_service: Optional["DatabaseService"] = None,
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

        self.history_limit = self._validated_positive_value(
            history_limit,
            DEFAULT_HISTORY_LIMIT,
            "history_limit",
        )
        self.history_ttl_seconds = self._validated_positive_value(
            history_ttl_seconds,
            DEFAULT_HISTORY_TTL_SECONDS,
            "history_ttl_seconds",
        )

        self.database_service = database_service
        self.analysis_history: Dict[str, List[Dict]] = {}

        if self.database_service:
            logger.info("PatientAnalyzer initialized with database service")
        else:
            logger.info("PatientAnalyzer initialized with in-memory history (database service not provided)")

    @staticmethod
    def _validated_positive_value(
        value: Optional[int], default_value: int, name: str
    ) -> int:
        if value is None:
            return default_value
        if value <= 0:
            logger.warning(
                "%s must be positive; falling back to default %s", name, default_value
            )
            return default_value
        return value

    async def _generate_summary(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.patient_data_service:
            return {}
        return await self.patient_data_service.generate_summary(patient_data)

    async def _identify_alerts(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.alert_service:
            return []
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
            # This hook is the only place where completed analyses flow into the
            # optional meta-learning component; removing it would make the
            # analyzer entirely observational with no feedback captured for
            # adaptive tuning.
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

    async def _record_for_learning(self, patient_id: str, analysis: Dict[str, Any]):
        """Record analysis for MLC learning and feedback"""

        if not self.mlc_learning:
            logger.info("No MLC learning component configured; skipping record")
            return

        logger.info("Recording analysis for MLC learning: %s", patient_id)
        await self.mlc_learning.record_feedback(patient_id, analysis)

    def _add_to_history(self, analysis: Dict[str, Any]) -> None:
        """Add an analysis result to history while enforcing limits and TTL."""

        patient_id = analysis.get("patient_id") or "unknown"
        
        # Try to save to database first (if available)
        if self.database_service:
            try:
                # Extract correlation_id and user_id from analysis if available
                correlation_id = analysis.get("correlation_id")
                user_id = analysis.get("user_id")
                
                # Prepare analysis data for database
                analysis_data = {
                    "analysis_data": analysis,
                    "risk_scores": analysis.get("risk_scores", {}),
                    "alerts": analysis.get("alerts", []),
                    "recommendations": analysis.get("recommendations", []),
                }
                
                # Save to database (async, but we're in sync context - will be handled by caller)
                # For now, we'll save synchronously in a fire-and-forget manner
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create a task
                        asyncio.create_task(
                            self.database_service.save_analysis(
                                patient_id=patient_id,
                                analysis_data=analysis_data,
                                user_id=user_id,
                                correlation_id=correlation_id,
                            )
                        )
                    else:
                        # If no loop running, run it
                        loop.run_until_complete(
                            self.database_service.save_analysis(
                                patient_id=patient_id,
                                analysis_data=analysis_data,
                                user_id=user_id,
                                correlation_id=correlation_id,
                            )
                        )
                except RuntimeError:
                    # No event loop, skip database save
                    pass
            except Exception as e:
                logger.warning("Failed to save analysis to database, falling back to in-memory: %s", str(e))
        
        # Also keep in-memory for backward compatibility and fast access
        bucket = self.analysis_history.setdefault(patient_id, [])
        bucket.append(analysis)

        removed = self._prune_history_for_patient(patient_id)
        if removed:
            logger.info(
                "Pruned %s expired analyses for %s after adding new result",
                removed,
                patient_id,
            )

        stale_removed = self.prune_stale_history()
        if stale_removed:
            logger.info("Pruned %s expired analyses across all patients", stale_removed)

    def clear_history(self) -> None:
        """Remove all cached analyses to reclaim memory."""

        self.analysis_history.clear()

    def get_history(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return a copy of the analysis history for a patient or all patients."""

        if patient_id is not None:
            return list(self.analysis_history.get(patient_id, []))

        all_entries: List[Dict[str, Any]] = []
        for bucket in self.analysis_history.values():
            all_entries.extend(bucket)

        return sorted(all_entries, key=self._timestamp_sort_key)

    def get_latest_analysis(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest analysis for a specific patient."""
        
        # Try database first (if available)
        if self.database_service:
            try:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, we can't use run_until_complete
                        # Fall back to in-memory for now
                        pass
                    else:
                        # Try to get from database
                        db_result = loop.run_until_complete(
                            self.database_service.get_latest_analysis(patient_id)
                        )
                        if db_result:
                            return db_result
                except RuntimeError:
                    # No event loop, fall back to in-memory
                    pass
            except Exception as e:
                logger.debug("Failed to get analysis from database, using in-memory: %s", str(e))
        
        # Fall back to in-memory
        bucket = self.analysis_history.get(patient_id) or []
        if not bucket:
            return None
        return bucket[-1]

    def total_history_count(self) -> int:
        """Return the total number of cached analyses across all patients."""

        return sum(len(bucket) for bucket in self.analysis_history.values())

    def collect_recent_alerts(
        self,
        limit: int,
        patient_id: Optional[str] = None,
        roster_lookup: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate recent critical and high-severity alerts from analysis history.
        """
        alerts: List[Dict[str, Any]] = []
        history = self.get_history(patient_id=patient_id)

        for analysis in reversed(history):
            timestamp = analysis.get("analysis_timestamp") or analysis.get("timestamp")
            analysis_patient_id = analysis.get("patient_id")

            patient_name = (
                (analysis.get("summary") or {}).get("patient_name")
                or (analysis.get("patient_data") or {})
                .get("patient", {})
                .get("name")
                or (roster_lookup.get(analysis_patient_id) if roster_lookup else None)
                or analysis_patient_id
            )

            for idx, alert in enumerate(analysis.get("alerts") or []):
                normalized = alert if isinstance(alert, dict) else {"summary": str(alert)}
                severity = (normalized.get("severity") or "").lower()

                if severity not in {"critical", "high"}:
                    continue

                alerts.append(
                    {
                        "id": normalized.get("id")
                        or f"{analysis_patient_id}-{idx}-{timestamp or len(alerts)}",
                        "patient_id": analysis_patient_id,
                        "patient_name": patient_name,
                        "title": normalized.get("title")
                        or normalized.get("type")
                        or "Clinical Alert",
                        "summary": normalized.get("summary")
                        or normalized.get("description")
                        or normalized.get("message")
                        or str(alert),
                        "severity": normalized.get("severity") or "critical",
                        "timestamp": normalized.get("timestamp")
                        or normalized.get("created_at")
                        or timestamp
                        or datetime.now(timezone.utc).isoformat(),
                    }
                )

                if len(alerts) >= limit:
                    break

            if len(alerts) >= limit:
                break

        return sorted(alerts, key=lambda a: a.get("timestamp", ""), reverse=True)[:limit]



    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "total_analyses": self.total_history_count(),
            "successful_analyses": sum(
                1
                for a in self.get_history()
                if a.get("status") == "completed"
            ),
            "average_analysis_time": sum(
                a.get("analysis_duration_seconds", 0) for a in self.get_history()
            )
            / max(self.total_history_count(), 1),
        }

    def prune_stale_history(self) -> int:
        """Prune TTL-expired analyses across all patients."""

        total_removed = 0
        for patient_id in list(self.analysis_history.keys()):
            total_removed += self._prune_history_for_patient(patient_id)
        return total_removed

    def _prune_history_for_patient(self, patient_id: str) -> int:
        bucket = self.analysis_history.get(patient_id, [])
        if not bucket:
            return 0

        removed = self._prune_by_limit(bucket)
        removed += self._prune_by_ttl(bucket)
        return removed

    def _prune_by_limit(self, bucket: List[Dict[str, Any]]) -> int:
        if self.history_limit is None or self.history_limit <= 0:
            return 0
        excess = len(bucket) - self.history_limit
        if excess > 0:
            del bucket[:excess]
        return max(excess, 0)

    def _prune_by_ttl(self, bucket: List[Dict[str, Any]]) -> int:
        if not self.history_ttl_seconds:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.history_ttl_seconds)
        retained: List[Dict[str, Any]] = []
        removed = 0
        for entry in bucket:
            timestamp = self._parse_timestamp(entry)
            if timestamp and timestamp < cutoff:
                removed += 1
                continue
            retained.append(entry)

        if removed:
            bucket[:] = retained
        return removed

    @staticmethod
    def _parse_timestamp(entry: Dict[str, Any]) -> Optional[datetime]:
        timestamp_value = entry.get("analysis_timestamp") or entry.get("timestamp")
        if not timestamp_value:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            return None

    def _timestamp_sort_key(self, entry: Dict[str, Any]) -> datetime:
        return self._parse_timestamp(entry) or datetime.min.replace(tzinfo=timezone.utc)

    @staticmethod
    def _calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
        """Deprecated wrapper retained for backward compatibility."""

        return PatientDataService._calculate_age(birth_date_str)

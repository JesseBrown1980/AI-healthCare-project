"""
Patient Analyzer Module
Central orchestration of all AI components for comprehensive patient analysis
Combines FHIR data, LLM intelligence, RAG knowledge, S-LoRA adaptation, MLC learning, and AoT reasoning
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .fhir_connector import FHIRConnectorError
from .services import (
    AlertNotificationService,
    AlertService,
    MedicationReviewService,
    PatientDataService,
    RiskScoringService,
    SummaryService,
)

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
        *,
        patient_data_service: Optional[PatientDataService] = None,
        summary_service: Optional[SummaryService] = None,
        alert_service: Optional[AlertService] = None,
        risk_scoring_service: Optional[RiskScoringService] = None,
        medication_review_service: Optional[MedicationReviewService] = None,
        notification_service: Optional[AlertNotificationService] = None,
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
        
        self.analysis_history: List[Dict] = []
        self.notifier = notifier
        self.notifications_enabled = notifications_enabled

        self.patient_data_service = patient_data_service or PatientDataService(
            fhir_connector
        )
        self.summary_service = summary_service or SummaryService()
        self.alert_service = alert_service or AlertService()
        self.risk_scoring_service = risk_scoring_service or RiskScoringService()
        self.medication_review_service = (
            medication_review_service or MedicationReviewService()
        )
        self.notification_service = notification_service or AlertNotificationService(
            notifier, notifications_enabled
        )

        logger.info("PatientAnalyzer initialized with all components")
    
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
        logger.info(f"Starting analysis for patient {patient_id}")
        analysis_start = datetime.now(timezone.utc)
        
        try:
            result = {
                "patient_id": patient_id,
                "analysis_timestamp": analysis_start.isoformat(),
                "status": "in_progress",
            }
            
            # 1. FETCH PATIENT DATA (FHIR)
            logger.info("Step 1: Fetching FHIR data...")
            patient_data = await self.patient_data_service.fetch_patient(patient_id)
            result["patient_data"] = patient_data
            
            # 2. DETERMINE SPECIALTIES (S-LoRA)
            logger.info("Step 2: Determining relevant specialties...")
            specialties = [specialty] if specialty else []
            selected_adapters = await self.s_lora_manager.select_adapters(
                specialties=specialties,
                patient_data=patient_data
            )
            
            # Activate appropriate adapters
            for adapter in selected_adapters[:3]:  # Limit to top 3 for efficiency
                await self.s_lora_manager.activate_adapter(adapter)
            
            result["active_specialties"] = [
                self.s_lora_manager.adapters[a].get("specialty") for a in selected_adapters[:3]
            ]
            
            # 3. GENERATE PATIENT SUMMARY
            logger.info("Step 3: Generating patient summary...")
            summary = await self.summary_service.generate_summary(patient_data)
            result["summary"] = summary

            # 4. IDENTIFY ALERTS
            logger.info("Step 4: Identifying clinical alerts...")
            alerts = await self.alert_service.identify_alerts(patient_data)
            result["alerts"] = alerts
            result["alert_count"] = len(alerts)
            result["highest_alert_severity"] = self.alert_service.highest_alert_severity(alerts)

            # 5. CALCULATE RISK SCORES
            logger.info("Step 5: Calculating risk scores...")
            risk_scores = await self.risk_scoring_service.calculate_risk_scores(
                patient_data
            )
            result["risk_scores"] = risk_scores
            result["overall_risk_score"] = self.risk_scoring_service.derive_overall_risk_score(
                risk_scores
            )
            result["polypharmacy_risk"] = risk_scores.get("polypharmacy_risk", False)

            # 6. MEDICATION REVIEW
            logger.info("Step 6: Reviewing medications...")
            medication_review = await self.medication_review_service.review_medications(
                patient_data
            )
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
                    focus=analysis_focus
                )
                result["recommendations"] = recommendations
            
            # 8. APPLY MLC LEARNING
            logger.info("Step 8: Recording for meta-learning...")
            await self._record_for_learning(patient_id, result)
            
            # 9. COMPILE FINAL ANALYSIS
            analysis_end = datetime.now(timezone.utc)
            result["analysis_duration_seconds"] = (analysis_end - analysis_start).total_seconds()
            result["last_analyzed_at"] = analysis_end.isoformat()
            result["status"] = "completed"
            
            # Store in history
            self.analysis_history.append(result)

            logger.info(f"Analysis completed for patient {patient_id} in {result['analysis_duration_seconds']:.2f}s")

            await self.notification_service.notify_if_needed(
                result, notify, correlation_id
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
        except Exception as e:
            logger.error(f"Error analyzing patient {patient_id}: {str(e)}")
            return {
                "patient_id": patient_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _generate_recommendations(
        self,
        patient_data: Dict,
        summary: Dict,
        alerts: List[Dict],
        risk_scores: Dict,
        adapters: List[str],
        focus: Optional[str] = None
    ) -> Dict:
        """Generate clinical recommendations using LLM with RAG and AoT"""
        
        recommendations = {
            "clinical_recommendations": [],
            "reasoning_chains": [],
            "evidence_citations": [],
            "priority_actions": []
        }
        
        try:
            # Get MLC-suggested components for this analysis
            task_type = focus or "patient_analysis"
            components = await self.mlc_learning.compose_for_task(task_type)
            
            # Build recommendation queries
            queries = [
                f"What are the main clinical priorities for this patient with {len(patient_data.get('conditions', []))} conditions?",
                f"Given the alerts identified, what immediate actions should be taken?",
                f"What preventive measures would be most impactful for this patient?"
            ]
            
            for query in queries:
                # Generate reasoning chain (AoT)
                reasoning_chain = await self.aot_reasoner.generate_reasoning_chain(
                    question=query,
                    context=patient_data
                )
                recommendations["reasoning_chains"].append(reasoning_chain)
                
                # Query LLM with RAG
                rag_results = await self.rag_fusion.retrieve_relevant_knowledge(query)
                
                llm_response = await self.llm_engine.query_with_rag(
                    question=query,
                    patient_context=patient_data,
                    rag_component=self.rag_fusion,
                    aot_reasoner=self.aot_reasoner,
                    include_reasoning=True
                )
                
                recommendations["clinical_recommendations"].append({
                    "query": query,
                    "recommendation": llm_response.get("answer"),
                    "confidence": llm_response.get("confidence"),
                    "sources": llm_response.get("sources")
                })
                
                recommendations["evidence_citations"].extend(llm_response.get("sources", []))
            
            # Identify priority actions from alerts and risk scores
            recommendations["priority_actions"] = [
                {"priority": 1, "action": alert["message"], "severity": alert["severity"]}
                for alert in alerts[:3]
            ]
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return {
                "clinical_recommendations": [],
                "reasoning_chains": [],
                "evidence_citations": [],
                "error": str(e)
            }
    
    async def _record_for_learning(self, patient_id: str, analysis: Dict):
        """Record analysis for MLC learning and feedback"""
        # This would normally track components used, performance, etc.
        logger.info(f"Recording analysis for MLC learning: {patient_id}")
    
    def get_stats(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "total_analyses": len(self.analysis_history),
            "successful_analyses": sum(
                1 for a in self.analysis_history if a.get("status") == "completed"
            ),
            "average_analysis_time": sum(
                a.get("analysis_duration_seconds", 0) for a in self.analysis_history
            ) / max(len(self.analysis_history), 1)
        }


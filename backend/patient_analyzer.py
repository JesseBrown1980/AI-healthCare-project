"""
Patient Analyzer Module
Central orchestration of all AI components for comprehensive patient analysis
Combines FHIR data, LLM intelligence, RAG knowledge, S-LoRA adaptation, MLC learning, and AoT reasoning
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, date

from .fhir_connector import FHIRConnectorError

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
        mlc_learning
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
        
        logger.info("PatientAnalyzer initialized with all components")
    
    async def analyze(
        self,
        patient_id: str,
        include_recommendations: bool = True,
        specialty: Optional[str] = None,
        analysis_focus: Optional[str] = None
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
        analysis_start = datetime.now()
        
        try:
            result = {
                "patient_id": patient_id,
                "analysis_timestamp": analysis_start.isoformat(),
                "status": "in_progress"
            }
            
            # 1. FETCH PATIENT DATA (FHIR)
            logger.info("Step 1: Fetching FHIR data...")
            patient_data = await self.fhir_connector.get_patient(patient_id)
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
            summary = await self._generate_summary(patient_data)
            result["summary"] = summary
            
            # 4. IDENTIFY ALERTS
            logger.info("Step 4: Identifying clinical alerts...")
            alerts = await self._identify_alerts(patient_data)
            result["alerts"] = alerts
            result["alert_count"] = len(alerts)
            
            # 5. CALCULATE RISK SCORES
            logger.info("Step 5: Calculating risk scores...")
            risk_scores = await self._calculate_risk_scores(patient_data)
            result["risk_scores"] = risk_scores
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
                    focus=analysis_focus
                )
                result["recommendations"] = recommendations
            
            # 8. APPLY MLC LEARNING
            logger.info("Step 8: Recording for meta-learning...")
            await self._record_for_learning(patient_id, result)
            
            # 9. COMPILE FINAL ANALYSIS
            analysis_end = datetime.now()
            result["analysis_duration_seconds"] = (analysis_end - analysis_start).total_seconds()
            result["status"] = "completed"
            
            # Store in history
            self.analysis_history.append(result)
            
            logger.info(f"Analysis completed for patient {patient_id} in {result['analysis_duration_seconds']:.2f}s")
            
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
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_summary(self, patient_data: Dict) -> Dict:
        """Generate concise patient summary"""
        patient_info = patient_data.get("patient", {})
        age = self._calculate_age(patient_info.get("birthDate"))

        summary = {
            "patient_name": patient_info.get("name"),
            "age_gender": f"{age if age is not None else 'Unknown'} / {patient_info.get('gender', 'Unknown')}",
            "age": age,
            "active_conditions_count": len(patient_data.get("conditions", [])),
            "current_medications_count": len(patient_data.get("medications", [])),
            "recent_visits": len(patient_data.get("encounters", [])),
            "key_conditions": [c.get("code") for c in patient_data.get("conditions", [])[:3]],
            "key_medications": [m.get("medication") for m in patient_data.get("medications", [])[:3]],
            "narrative_summary": f"Patient {patient_info.get('name')} (age {age if age is not None else 'Unknown'}) has {len(patient_data.get('conditions', []))} active conditions and is on {len(patient_data.get('medications', []))} medications."
        }

        return summary
    
    async def _identify_alerts(self, patient_data: Dict) -> List[Dict]:
        """Identify clinical alerts and red flags"""
        alerts = []
        
        # Check for high-risk conditions
        critical_conditions = ["MI", "stroke", "sepsis", "acute_MI", "pulmonary_embolism"]
        for condition in patient_data.get("conditions", []):
            code = condition.get("code", "").lower()
            if any(risk in code for risk in critical_conditions):
                alerts.append({
                    "severity": "critical",
                    "type": "condition",
                    "message": f"Critical condition identified: {condition.get('code')}",
                    "recommendation": "Immediate clinical review required"
                })
        
        # Check lab values
        for obs in patient_data.get("observations", []):
            value = obs.get("value")
            interp = obs.get("interpretation", "").lower()
            
            if "high" in interp or "critical" in interp:
                alerts.append({
                    "severity": "high",
                    "type": "lab",
                    "message": f"Abnormal lab value: {obs.get('code')} = {value} {obs.get('unit')}",
                    "recommendation": f"Review {obs.get('code')} and consider intervention"
                })
        
        # Check for drug interactions
        meds = [m.get("medication", "").lower() for m in patient_data.get("medications", [])]
        known_interactions = [
            ("warfarin", "nsaid"),
            ("lisinopril", "potassium"),
            ("metformin", "dye")
        ]
        
        for drug1, drug2 in known_interactions:
            if any(drug1 in m for m in meds) and any(drug2 in m for m in meds):
                alerts.append({
                    "severity": "medium",
                    "type": "drug_interaction",
                    "message": f"Potential interaction: {drug1} + {drug2}",
                    "recommendation": "Consider alternative or adjust dosing"
                })
        
        return alerts
    
    async def _calculate_risk_scores(self, patient_data: Dict) -> Dict:
        """Calculate various clinical risk scores"""
        risk_scores = {}

        def _normalize(score: float) -> float:
            return max(0.0, min(1.0, score))

        patient_info = patient_data.get("patient", {})
        age = self._calculate_age(patient_info.get("birthDate"))
        age_factor = _normalize((age or 0) / 100)

        conditions = [c.get("code", "").lower() for c in patient_data.get("conditions", [])]
        medication_count = len(patient_data.get("medications", []))
        polypharmacy = medication_count > 10
        med_burden_factor = min(0.2, medication_count * 0.02)

        # Cardiovascular risk considers age, hypertension/diabetes/smoking, and medication load
        cv_risk = 0.15 + (0.35 * age_factor)
        if any("hypertension" in c for c in conditions):
            cv_risk += 0.2
        if any("diabetes" in c for c in conditions):
            cv_risk += 0.2
        if any("smoke" in c for c in conditions):
            cv_risk += 0.2
        cv_risk += med_burden_factor
        if polypharmacy:
            cv_risk += 0.1

        risk_scores["cardiovascular_risk"] = _normalize(cv_risk)

        # Hospital readmission risk values are normalized and weight encounter history
        recent_encounters = len(
            [e for e in patient_data.get("encounters", []) if e.get("status") in ["finished", "completed"]]
        )
        readmit_risk = 0.12 + (0.25 * age_factor)
        readmit_risk += min(0.25, recent_encounters * 0.05)
        readmit_risk += min(0.25, medication_count * 0.02)
        if polypharmacy:
            readmit_risk += 0.1

        risk_scores["readmission_risk"] = _normalize(readmit_risk)

        # Medication adherence risk accounts for regimen complexity and age-related adherence challenges
        adherence_risk = 0.1 + (0.3 * age_factor) + min(0.35, medication_count * 0.03)
        if polypharmacy:
            adherence_risk += 0.15

        risk_scores["medication_non_adherence_risk"] = _normalize(adherence_risk)

        # Explicit flag for downstream consumers that expect a boolean polypharmacy field
        risk_scores["polypharmacy"] = polypharmacy
        risk_scores["polypharmacy_risk"] = polypharmacy

        return risk_scores
    
    async def _medication_review(self, patient_data: Dict) -> Dict:
        """Review medications for appropriateness and interactions"""
        review = {
            "total_medications": len(patient_data.get("medications", [])),
            "medications": [],
            "potential_issues": [],
            "deprescribing_candidates": []
        }
        
        for med in patient_data.get("medications", []):
            med_review = {
                "name": med.get("medication"),
                "status": med.get("status"),
                "indication": med.get("medication"),  # Simplified
                "appropriateness": "appropriate"
            }
            review["medications"].append(med_review)
        
        # Identify deprescribing opportunities (simplified)
        if review["total_medications"] > 10:
            review["potential_issues"].append("Polypharmacy (>10 medications) - review for duplication")
            review["deprescribing_candidates"] = [
                m.get("medication") for m in patient_data.get("medications", [])[:2]
            ]
        
        return review
    
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

    @staticmethod
    def _calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
        """Calculate age in years from a birth date string."""

        if not birth_date_str:
            return None

        try:
            birth_date = date.fromisoformat(birth_date_str[:10])
        except ValueError:
            return None

        today = date.today()
        return (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

import logging
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskScoringService:
    """Service for computing patient risk scores and medication reviews."""

    async def calculate_risk_scores(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate patient risk scores based on demographics and medications."""

        patient_info = patient_data.get("patient", {})
        age = self._calculate_age(patient_info.get("birthDate")) or 0
        conditions = patient_data.get("conditions", [])
        medications = patient_data.get("medications", [])
        encounters = patient_data.get("encounters", [])

        risk_scores: Dict[str, Any] = {}

        def _normalize(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
            return max(min_value, min(max_value, value))

        age_factor = min(1.0, age / 100)
        condition_count = len(conditions)
        medication_count = len(medications)
        encounter_count = len(encounters)
        polypharmacy = medication_count >= 10

        # Cardiovascular risk increases with age and condition burden
        cardiovascular_risk = 0.2 + (0.4 * age_factor) + (0.2 * min(1.0, condition_count / 5))
        if polypharmacy:
            cardiovascular_risk += 0.1
        risk_scores["cardiovascular_risk"] = _normalize(cardiovascular_risk)

        # Readmission risk considers encounter history and medication complexity
        readmit_risk = 0.15 + (0.25 * age_factor) + (0.2 * min(1.0, encounter_count / 5))
        if polypharmacy:
            readmit_risk += 0.1
        risk_scores["readmission_risk"] = _normalize(readmit_risk)

        # Medication adherence risk accounts for regimen complexity and age-related challenges
        adherence_risk = 0.1 + (0.3 * age_factor) + min(0.35, medication_count * 0.03)
        if polypharmacy:
            adherence_risk += 0.15
        risk_scores["medication_non_adherence_risk"] = _normalize(adherence_risk)

        # Explicit flags for downstream consumers
        risk_scores["polypharmacy"] = polypharmacy
        risk_scores["polypharmacy_risk"] = polypharmacy

        return risk_scores

    async def review_medications(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Review medications for appropriateness and interactions."""

        review = {
            "total_medications": len(patient_data.get("medications", [])),
            "medications": [],
            "potential_issues": [],
            "deprescribing_candidates": [],
        }

        for med in patient_data.get("medications", []):
            med_review = {
                "name": med.get("medication"),
                "status": med.get("status"),
                "indication": med.get("medication"),  # Simplified
                "appropriateness": "appropriate",
            }
            review["medications"].append(med_review)

        # Identify deprescribing opportunities (simplified)
        if review["total_medications"] > 10:
            review["potential_issues"].append(
                "Polypharmacy (>10 medications) - review for duplication"
            )
            review["deprescribing_candidates"] = [
                m.get("medication") for m in patient_data.get("medications", [])[:2]
            ]

        return review

    @staticmethod
    def derive_overall_risk_score(risk_scores: Dict[str, Any]) -> Optional[float]:
        """Return the highest numeric risk score for quick comparison."""

        numeric_scores = [
            value
            for value in risk_scores.values()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]

        if not numeric_scores:
            return None

        return max(numeric_scores)

    @staticmethod
    def _calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
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

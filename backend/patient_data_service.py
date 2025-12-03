import logging
from datetime import date
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PatientDataService:
    """Service responsible for retrieving and summarizing patient data."""

    def __init__(self, fhir_connector):
        self.fhir_connector = fhir_connector

    async def fetch_patient_data(self, patient_id: str) -> Dict[str, Any]:
        """Fetch patient data from the configured FHIR connector."""

        logger.info("Fetching patient data for %s", patient_id)
        return await self.fhir_connector.get_patient(patient_id)

    async def generate_summary(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a concise patient summary from raw patient data."""

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
            "narrative_summary": (
                f"Patient {patient_info.get('name')} (age {age if age is not None else 'Unknown'}) "
                f"has {len(patient_data.get('conditions', []))} active conditions and "
                f"is on {len(patient_data.get('medications', []))} medications."
            ),
        }

        return summary

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

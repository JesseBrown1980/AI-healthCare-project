"""
FHIR Connector Module
Handles integration with FHIR-compliant EHR systems
Implements OAuth2 authentication and FHIR resource parsing
"""

import asyncio
import logging
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

try:
    from fhir.resources.patient import Patient
except ImportError:  # Optional dependency for schema validation
    class Patient:
        """Fallback Patient model when fhir.resources is unavailable."""

        @staticmethod
        def model_validate(fhir_patient):
            class _Validated:
                def __init__(self, payload):
                    self.payload = payload

                def model_dump(self, mode=None):
                    return self.payload

            return _Validated(fhir_patient)

logger = logging.getLogger(__name__)


class FHIRConnector:
    """
    Connects to FHIR-compliant healthcare systems
    Handles authentication, data fetching, and resource normalization
    Allows optional use of environment-configured proxies for compatibility
    """
    
    def __init__(
        self,
        server_url: str,
        api_key: str = "",
        username: str = "",
        password: str = "",
        use_proxies: bool = True,
    ):
        """
        Initialize FHIR connector

        Args:
            server_url: FHIR server base URL
            api_key: API key for authentication
            username: Username for basic auth
            password: Password for basic auth
            use_proxies: Whether to honor proxy settings from environment variables
        """
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self.use_proxies = use_proxies
        self.session: Optional[httpx.AsyncClient] = None
        self.session = self._initialize_session()
        
    def _initialize_session(self) -> httpx.AsyncClient:
        """Initialize HTTP session with appropriate authentication"""
        headers = {"Accept": "application/fhir+json"}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        auth = None
        if self.username and self.password:
            auth = (self.username, self.password)
        
        logger.info(f"FHIR connector initialized for {self.server_url}")

        trust_env = self.use_proxies
        try:
            return httpx.AsyncClient(
                headers=headers,
                auth=auth,
                timeout=30.0,
                trust_env=trust_env,
            )
        except ImportError as exc:
            # Handles environments lacking optional proxy dependencies (e.g., socksio)
            logger.warning(
                "Proxy support unavailable (%s); creating session without proxies.",
                exc,
            )
            return httpx.AsyncClient(
                headers=headers,
                auth=auth,
                timeout=30.0,
                trust_env=False,
            )

    async def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """
        Fetch patient resource from FHIR server
        
        Args:
            patient_id: FHIR patient ID
            
        Returns:
            Parsed patient data including demographics, active conditions, medications
        """
        try:
            # Fetch Patient resource
            patient_response = await self.session.get(
                f"{self.server_url}/Patient/{patient_id}"
            )
            patient_response.raise_for_status()
            patient = self._validate_patient_resource(patient_response.json())
            
            # Fetch related resources
            conditions = await self._get_patient_conditions(patient_id)
            medications = await self._get_patient_medications(patient_id)
            observations = await self._get_patient_observations(patient_id)
            encounters = await self._get_patient_encounters(patient_id)
            
            return {
                "patient": self._normalize_patient(patient),
                "conditions": conditions,
                "medications": medications,
                "observations": observations,
                "encounters": encounters,
                "fetched_at": datetime.now().isoformat()
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Error fetching patient {patient_id}: {str(e)}")
            raise

    def _validate_patient_resource(self, fhir_patient: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming patient resource using FHIR resource models."""
        try:
            validated = Patient.model_validate(fhir_patient)
            return validated.model_dump(mode="json")
        except Exception as exc:
            logger.warning("FHIR Patient validation failed: %s", exc)
            return fhir_patient
    
    async def _get_patient_conditions(self, patient_id: str) -> List[Dict]:
        """Fetch patient's active conditions (diagnoses)"""
        try:
            response = await self.session.get(
                f"{self.server_url}/Condition",
                params={
                    "patient": patient_id,
                    "clinical-status": "active"
                }
            )
            response.raise_for_status()
            bundle = response.json()
            
            conditions = []
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                conditions.append(self._normalize_condition(resource))
            
            return conditions
        except Exception as e:
            logger.warning(f"Error fetching conditions for {patient_id}: {str(e)}")
            return []
    
    async def _get_patient_medications(self, patient_id: str) -> List[Dict]:
        """Fetch patient's active medications"""
        try:
            # First get MedicationRequest resources
            response = await self.session.get(
                f"{self.server_url}/MedicationRequest",
                params={
                    "patient": patient_id,
                    "status": "active"
                }
            )
            response.raise_for_status()
            bundle = response.json()
            
            medications = []
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                medications.append(self._normalize_medication(resource))
            
            return medications
        except Exception as e:
            logger.warning(f"Error fetching medications for {patient_id}: {str(e)}")
            return []
    
    async def _get_patient_observations(self, patient_id: str, limit: int = 50) -> List[Dict]:
        """Fetch patient's lab results and vital signs"""
        try:
            response = await self.session.get(
                f"{self.server_url}/Observation",
                params={
                    "patient": patient_id,
                    "_sort": "-date",
                    "_count": limit
                }
            )
            response.raise_for_status()
            bundle = response.json()
            
            observations = []
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                observations.append(self._normalize_observation(resource))
            
            return observations
        except Exception as e:
            logger.warning(f"Error fetching observations for {patient_id}: {str(e)}")
            return []
    
    async def _get_patient_encounters(self, patient_id: str, limit: int = 20) -> List[Dict]:
        """Fetch patient's recent encounters (visits)"""
        try:
            response = await self.session.get(
                f"{self.server_url}/Encounter",
                params={
                    "patient": patient_id,
                    "_sort": "-date",
                    "_count": limit
                }
            )
            response.raise_for_status()
            bundle = response.json()
            
            encounters = []
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                encounters.append(self._normalize_encounter(resource))
            
            return encounters
        except Exception as e:
            logger.warning(f"Error fetching encounters for {patient_id}: {str(e)}")
            return []
    
    # ==================== NORMALIZATION METHODS ====================
    
    def _normalize_patient(self, fhir_patient: Dict) -> Dict:
        """Normalize FHIR Patient resource"""
        return {
            "id": fhir_patient.get("id"),
            "name": self._get_name(fhir_patient),
            "birthDate": fhir_patient.get("birthDate"),
            "gender": fhir_patient.get("gender"),
            "telecom": fhir_patient.get("telecom", []),
            "address": fhir_patient.get("address", []),
            "maritalStatus": fhir_patient.get("maritalStatus"),
            "contact": fhir_patient.get("contact", [])
        }
    
    def _normalize_condition(self, fhir_condition: Dict) -> Dict:
        """Normalize FHIR Condition resource"""
        return {
            "id": fhir_condition.get("id"),
            "code": fhir_condition.get("code", {}).get("coding", [{}])[0].get("display"),
            "codeSystem": fhir_condition.get("code", {}).get("coding", [{}])[0].get("system"),
            "clinicalStatus": fhir_condition.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
            "onsetDate": fhir_condition.get("onsetDateTime") or fhir_condition.get("onsetDate"),
            "abatementDate": fhir_condition.get("abatementDateTime") or fhir_condition.get("abatementDate"),
            "severity": fhir_condition.get("severity", {}).get("coding", [{}])[0].get("display")
        }
    
    def _normalize_medication(self, fhir_med_request: Dict) -> Dict:
        """Normalize FHIR MedicationRequest resource"""
        return {
            "id": fhir_med_request.get("id"),
            "medication": fhir_med_request.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
            "medicationCode": fhir_med_request.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("code"),
            "status": fhir_med_request.get("status"),
            "dosageInstruction": fhir_med_request.get("dosageInstruction", []),
            "authoredOn": fhir_med_request.get("authoredOn"),
            "effectivePeriod": fhir_med_request.get("dosageInstruction", [{}])[0].get("timing", {}).get("repeat", {})
        }
    
    def _normalize_observation(self, fhir_observation: Dict) -> Dict:
        """Normalize FHIR Observation resource (labs, vitals)"""
        value = fhir_observation.get("valueQuantity", {})
        
        return {
            "id": fhir_observation.get("id"),
            "code": fhir_observation.get("code", {}).get("coding", [{}])[0].get("display"),
            "codeSystem": fhir_observation.get("code", {}).get("coding", [{}])[0].get("code"),
            "value": value.get("value"),
            "unit": value.get("unit"),
            "referenceRange": fhir_observation.get("referenceRange", []),
            "interpretation": fhir_observation.get("interpretation", [{}])[0].get("coding", [{}])[0].get("display"),
            "effectiveDateTime": fhir_observation.get("effectiveDateTime"),
            "status": fhir_observation.get("status")
        }
    
    def _normalize_encounter(self, fhir_encounter: Dict) -> Dict:
        """Normalize FHIR Encounter resource"""
        period = fhir_encounter.get("period", {})
        return {
            "id": fhir_encounter.get("id"),
            "type": fhir_encounter.get("type", [{}])[0].get("coding", [{}])[0].get("display"),
            "status": fhir_encounter.get("status"),
            "start": period.get("start"),
            "end": period.get("end"),
            "reasonCode": fhir_encounter.get("reasonCode", [{}])[0].get("coding", [{}])[0].get("display"),
            "class": fhir_encounter.get("class", {}).get("code")
        }
    
    def _get_name(self, patient: Dict) -> str:
        """Extract patient name from FHIR format"""
        names = patient.get("name", [])
        if names:
            name = names[0]
            parts = []
            if name.get("given"):
                parts.extend(name.get("given", []))
            if name.get("family"):
                parts.append(name.get("family"))
            return " ".join(parts)
        return "Unknown"
    
    def get_stats(self) -> Dict:
        """Get connector statistics"""
        return {
            "server": self.server_url,
            "authenticated": bool(self.api_key or self.username),
            "status": "connected"
        }

    async def aclose(self) -> None:
        """Cleanup session asynchronously"""
        session = getattr(self, "session", None)
        if session:
            await session.aclose()

    def __del__(self):
        """Attempt best-effort cleanup of the async session"""
        try:
            session = getattr(self, "session", None)
            if not session:
                return

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(session.aclose())
            else:
                loop = loop or asyncio.new_event_loop()
                try:
                    loop.run_until_complete(session.aclose())
                finally:
                    loop.close()
        except Exception:
            pass

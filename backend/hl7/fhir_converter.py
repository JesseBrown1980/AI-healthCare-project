"""
HL7 v2.x to FHIR resource converter.

Converts parsed HL7 v2.x messages to FHIR R4 resources.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


class HL7ConversionError(Exception):
    """Error converting HL7 v2.x to FHIR."""
    pass


class HL7ToFHIRConverter:
    """Converter from HL7 v2.x to FHIR R4 resources."""
    
    def __init__(self):
        """Initialize HL7 to FHIR converter."""
        logger.info("HL7 to FHIR converter initialized")
    
    def convert(self, parsed_message: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert parsed HL7 v2.x message to FHIR resources.
        
        Args:
            parsed_message: Parsed HL7 message from HL7MessageParser
            
        Returns:
            Dictionary containing FHIR resources:
            - patient: Patient resource (if PID present)
            - observations: List of Observation resources (if OBX present)
            - encounters: List of Encounter resources (if PV1 present)
            - medication_requests: List of MedicationRequest resources (if ORC/ORM present)
        """
        resources = {
            "patient": None,
            "observations": [],
            "encounters": [],
            "medication_requests": [],
        }
        
        message_type = parsed_message.get("message_type", "")
        
        # Convert Patient (PID segment)
        if "pid" in parsed_message:
            resources["patient"] = self._convert_patient(parsed_message["pid"])
        
        # Convert Observations (OBX segments)
        if "obx" in parsed_message:
            patient_ref = None
            if resources["patient"]:
                patient_ref = f"Patient/{resources['patient'].get('id', 'unknown')}"
            elif "pid" in parsed_message and parsed_message["pid"].get("patient_id"):
                patient_id = parsed_message["pid"]["patient_id"]
                patient_ref = f"Patient/{patient_id}"
            
            for obx in parsed_message["obx"]:
                observation = self._convert_observation(obx, patient_ref)
                if observation:
                    resources["observations"].append(observation)
        
        # Convert Encounter (PV1 segment)
        if "pv1" in parsed_message:
            patient_ref = None
            if resources["patient"]:
                patient_ref = f"Patient/{resources['patient'].get('id', 'unknown')}"
            elif "pid" in parsed_message and parsed_message["pid"].get("patient_id"):
                patient_id = parsed_message["pid"]["patient_id"]
                patient_ref = f"Patient/{patient_id}"
            
            encounter = self._convert_encounter(parsed_message["pv1"], patient_ref, message_type)
            if encounter:
                resources["encounters"].append(encounter)
        
        # Convert Medication Requests (ORC segments for orders)
        if "orc" in parsed_message:
            patient_ref = None
            if resources["patient"]:
                patient_ref = f"Patient/{resources['patient'].get('id', 'unknown')}"
            elif "pid" in parsed_message and parsed_message["pid"].get("patient_id"):
                patient_id = parsed_message["pid"]["patient_id"]
                patient_ref = f"Patient/{patient_id}"
            
            for orc in parsed_message["orc"]:
                if orc.get("order_control") in ["NW", "OK", "UA"]:  # New order, Order accepted, Unauthorized
                    med_request = self._convert_medication_request(orc, patient_ref)
                    if med_request:
                        resources["medication_requests"].append(med_request)
        
        return resources
    
    def _convert_patient(self, pid: Dict[str, Any]) -> Dict[str, Any]:
        """Convert PID segment to FHIR Patient resource."""
        patient_id = pid.get("patient_id") or str(uuid4())
        
        # Build name
        name_data = pid.get("name", {})
        name = {}
        if name_data.get("family") or name_data.get("given"):
            name = {
                "use": "official",
                "family": name_data.get("family"),
                "given": [g for g in [name_data.get("given"), name_data.get("middle")] if g],
            }
        
        # Parse date of birth
        dob = pid.get("date_of_birth")
        if dob:
            dob = self._parse_hl7_date(dob)
        
        # Map gender
        gender_map = {
            "M": "male",
            "F": "female",
            "O": "other",
            "U": "unknown",
        }
        gender_str = pid.get("gender") or ""
        gender = gender_map.get(gender_str.upper() if gender_str else "", "unknown")
        
        # Build identifiers
        identifiers = []
        for pid_entry in pid.get("patient_id_list", []):
            if pid_entry.get("id"):
                identifier = {
                    "use": "usual",
                    "value": pid_entry["id"],
                }
                if pid_entry.get("type"):
                    identifier["type"] = {
                        "coding": [{
                            "code": pid_entry["type"],
                        }]
                    }
                identifiers.append(identifier)
        
        patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": identifiers,
            "gender": gender,
        }
        
        if name:
            patient["name"] = [name]
        
        if dob:
            patient["birthDate"] = dob
        
        return patient
    
    def _convert_observation(self, obx: Dict[str, Any], patient_ref: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Convert OBX segment to FHIR Observation resource."""
        if not obx.get("observation_id"):
            logger.warning("OBX segment missing observation ID, skipping")
            return None
        
        obs_id = obx.get("observation_id", {})
        code = obs_id.get("code") or obs_id.get("text", "UNKNOWN")
        display = obs_id.get("text") or code
        
        # Build observation
        observation = {
            "resourceType": "Observation",
            "id": str(uuid4()),
            "status": self._map_observation_status(obx.get("status", "F")),
            "code": {
                "coding": [{
                    "code": code,
                    "display": display,
                }],
                "text": display,
            },
        }
        
        # Add coding system if available
        if obs_id.get("coding_system"):
            observation["code"]["coding"][0]["system"] = obs_id["coding_system"]
        else:
            # Default to LOINC if it looks like a LOINC code
            if code and code.replace("-", "").replace(".", "").isdigit():
                observation["code"]["coding"][0]["system"] = "http://loinc.org"
        
        # Add subject reference
        if patient_ref:
            observation["subject"] = {"reference": patient_ref}
        
        # Add value
        value = obx.get("observation_value")
        if value:
            value_type = obx.get("value_type", "ST")
            if value_type in ["NM", "SN"]:  # Numeric
                try:
                    numeric_value = float(value)
                    observation["valueQuantity"] = {
                        "value": numeric_value,
                    }
                    if obx.get("units"):
                        observation["valueQuantity"]["unit"] = obx["units"]
                except (ValueError, TypeError):
                    observation["valueString"] = str(value)
            else:
                observation["valueString"] = str(value)
        
        # Add reference range
        if obx.get("reference_range"):
            observation["referenceRange"] = [{
                "text": obx["reference_range"],
            }]
        
        # Add interpretation
        if obx.get("abnormal_flags"):
            interpretation = self._map_abnormal_flag(obx["abnormal_flags"])
            if interpretation:
                observation["interpretation"] = [{
                    "coding": [interpretation],
                }]
        
        # Add effective date/time
        if obx.get("observation_datetime"):
            effective_date = self._parse_hl7_datetime(obx["observation_datetime"])
            if effective_date:
                observation["effectiveDateTime"] = effective_date
        
        return observation
    
    def _convert_encounter(self, pv1: Dict[str, Any], patient_ref: Optional[str] = None, message_type: str = "") -> Optional[Dict[str, Any]]:
        """Convert PV1 segment to FHIR Encounter resource."""
        if not patient_ref:
            logger.warning("PV1 segment without patient reference, skipping")
            return None
        
        # Map patient class to encounter class
        class_map = {
            "I": "IMP",  # Inpatient
            "O": "AMB",  # Outpatient
            "E": "EMER",  # Emergency
            "P": "PRENC",  # Pre-admission
            "R": "AMB",  # Recurring patient
            "B": "IMP",  # Obstetrics
            "C": "AMB",  # Commercial Account
            "N": "NONAC",  # Not Applicable
        }
        
        patient_class = pv1.get("patient_class", "I")
        encounter_class = class_map.get(patient_class, "AMB")
        
        encounter = {
            "resourceType": "Encounter",
            "id": str(uuid4()),
            "status": self._map_encounter_status(message_type),
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": encounter_class,
                "display": self._get_class_display(encounter_class),
            },
            "subject": {"reference": patient_ref},
        }
        
        # Add location
        if pv1.get("assigned_location"):
            location_parts = pv1["assigned_location"].split("^")
            location_name = location_parts[0] if location_parts else pv1["assigned_location"]
            encounter["location"] = [{
                "location": {
                    "display": location_name,
                },
            }]
        
        # Add period
        period = {}
        if pv1.get("admit_datetime"):
            start_date = self._parse_hl7_datetime(pv1["admit_datetime"])
            if start_date:
                period["start"] = start_date
        
        if pv1.get("discharge_datetime"):
            end_date = self._parse_hl7_datetime(pv1["discharge_datetime"])
            if end_date:
                period["end"] = end_date
        
        if period:
            encounter["period"] = period
        
        return encounter
    
    def _convert_medication_request(self, orc: Dict[str, Any], patient_ref: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Convert ORC segment to FHIR MedicationRequest resource."""
        if not patient_ref:
            logger.warning("ORC segment without patient reference, skipping")
            return None
        
        med_request = {
            "resourceType": "MedicationRequest",
            "id": str(uuid4()),
            "status": "active",
            "intent": "order",
            "subject": {"reference": patient_ref},
        }
        
        # Add requester if available
        if orc.get("ordering_provider"):
            provider = orc["ordering_provider"]
            med_request["requester"] = {
                "display": f"{provider.get('given_name', '')} {provider.get('family_name', '')}".strip(),
            }
        
        return med_request
    
    def _parse_hl7_date(self, date_str: str) -> Optional[str]:
        """Parse HL7 date format (YYYYMMDD) to ISO format."""
        if not date_str or len(date_str) < 8:
            return None
        try:
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
        except Exception:
            return None
    
    def _parse_hl7_datetime(self, datetime_str: str) -> Optional[str]:
        """Parse HL7 datetime format (YYYYMMDDHHMMSS) to ISO format."""
        if not datetime_str:
            return None
        try:
            # Remove timezone if present
            dt_str = datetime_str.split("+")[0].split("-")[0]
            if len(dt_str) >= 14:
                year = dt_str[0:4]
                month = dt_str[4:6]
                day = dt_str[6:8]
                hour = dt_str[8:10]
                minute = dt_str[10:12]
                second = dt_str[12:14]
                return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"
            elif len(dt_str) >= 8:
                return self._parse_hl7_date(dt_str)
        except Exception:
            pass
        return None
    
    def _map_observation_status(self, status: str) -> str:
        """Map HL7 observation status to FHIR status."""
        status_map = {
            "F": "final",
            "P": "preliminary",
            "C": "corrected",
            "X": "cancelled",
            "D": "entered-in-error",
        }
        return status_map.get(status.upper(), "final")
    
    def _map_encounter_status(self, message_type: str) -> str:
        """Map ADT message type to encounter status."""
        if "A01" in message_type or "A04" in message_type:  # Admit, Register
            return "in-progress"
        elif "A03" in message_type or "A06" in message_type:  # Discharge, Change
            return "finished"
        elif "A02" in message_type:  # Transfer
            return "in-progress"
        return "planned"
    
    def _map_abnormal_flag(self, flag: str) -> Optional[Dict[str, str]]:
        """Map HL7 abnormal flag to FHIR interpretation."""
        flag_map = {
            "L": {"code": "L", "display": "Low", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"},
            "H": {"code": "H", "display": "High", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"},
            "LL": {"code": "LL", "display": "Critical Low", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"},
            "HH": {"code": "HH", "display": "Critical High", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"},
            "N": {"code": "N", "display": "Normal", "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"},
        }
        return flag_map.get(flag.upper())
    
    def _get_class_display(self, code: str) -> str:
        """Get display name for encounter class code."""
        display_map = {
            "IMP": "inpatient encounter",
            "AMB": "ambulatory",
            "EMER": "emergency",
            "PRENC": "pre-admission",
            "NONAC": "non-acute",
        }
        return display_map.get(code, code)

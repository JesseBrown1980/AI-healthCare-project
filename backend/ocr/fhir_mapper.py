"""
FHIR resource mapper for converting parsed medical data to FHIR resources.

Converts extracted lab values, medications, vital signs, and conditions
into FHIR Observation, MedicationStatement, and Condition resources.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


# LOINC codes for common lab tests
LOINC_CODES = {
    "glucose": {"code": "2339-0", "display": "Glucose [Mass/volume] in Blood"},
    "hba1c": {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
    "cholesterol": {"code": "2093-3", "display": "Cholesterol [Mass/volume] in Serum or Plasma"},
    "ldl": {"code": "2089-1", "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma"},
    "hdl": {"code": "2085-9", "display": "Cholesterol in HDL [Mass/volume] in Serum or Plasma"},
    "triglycerides": {"code": "2571-8", "display": "Triglyceride [Mass/volume] in Serum or Plasma"},
    "creatinine": {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"},
    "bun": {"code": "3094-0", "display": "Urea nitrogen [Mass/volume] in Serum or Plasma"},
    "sodium": {"code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma"},
    "potassium": {"code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma"},
    "hemoglobin": {"code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood"},
    "wbc": {"code": "6690-2", "display": "Leukocytes [#/volume] in Blood by Automated count"},
    "platelets": {"code": "777-3", "display": "Platelets [#/volume] in Blood by Automated count"},
}

# LOINC codes for vital signs
VITAL_LOINC = {
    "bp": {"code": "85354-9", "display": "Blood pressure panel with all children optional"},
    "hr": {"code": "8867-4", "display": "Heart rate"},
    "temp": {"code": "8310-5", "display": "Body temperature"},
    "rr": {"code": "9279-1", "display": "Respiratory rate"},
    "o2": {"code": "2708-6", "display": "Oxygen saturation in Arterial blood"},
}

# SNOMED CT codes for common conditions (simplified)
SNOMED_CONDITIONS = {
    "diabetes": {"code": "44054006", "display": "Diabetes mellitus type 2"},
    "hypertension": {"code": "38341003", "display": "Hypertensive disorder"},
    "asthma": {"code": "195967001", "display": "Asthma"},
    "copd": {"code": "13645005", "display": "Chronic obstructive pulmonary disease"},
    "chf": {"code": "42343007", "display": "Congestive heart failure"},
    "cad": {"code": "53741008", "display": "Coronary artery disease"},
    "mi": {"code": "22298006", "display": "Myocardial infarction"},
    "stroke": {"code": "230690007", "display": "Cerebrovascular accident"},
}


class FHIRMapper:
    """Mapper for converting parsed medical data to FHIR resources."""
    
    def __init__(self):
        """Initialize FHIR mapper."""
        logger.info("FHIR mapper initialized")
    
    def map_parsed_data_to_fhir(
        self,
        parsed_data: Dict[str, Any],
        patient_id: str,
        document_id: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert parsed medical data to FHIR resources.
        
        Args:
            parsed_data: Parsed data from MedicalParser
            patient_id: Patient ID
            document_id: Optional document ID for provenance
        
        Returns:
            Dictionary with FHIR resources:
            - observations: List of Observation resources
            - medication_statements: List of MedicationStatement resources
            - conditions: List of Condition resources
            - document_reference: DocumentReference resource (if document_id provided)
        """
        resources = {
            "observations": [],
            "medication_statements": [],
            "conditions": [],
            "document_reference": None,
        }
        
        # Map lab values to Observations
        for lab in parsed_data.get("lab_values", []):
            observation = self._lab_to_observation(lab, patient_id, document_id)
            if observation:
                resources["observations"].append(observation)
        
        # Map vital signs to Observations
        for vital in parsed_data.get("vital_signs", []):
            observation = self._vital_to_observation(vital, patient_id, document_id)
            if observation:
                resources["observations"].append(observation)
        
        # Map medications to MedicationStatement
        for med in parsed_data.get("medications", []):
            medication = self._med_to_medication_statement(med, patient_id, document_id)
            if medication:
                resources["medication_statements"].append(medication)
        
        # Map conditions to Condition
        for condition in parsed_data.get("conditions", []):
            fhir_condition = self._condition_to_fhir(condition, patient_id, document_id)
            if fhir_condition:
                resources["conditions"].append(fhir_condition)
        
        # Create DocumentReference if document_id provided
        if document_id:
            resources["document_reference"] = self._create_document_reference(
                document_id, patient_id, parsed_data
            )
        
        logger.info(
            "Mapped to FHIR: %d observations, %d medications, %d conditions",
            len(resources["observations"]),
            len(resources["medication_statements"]),
            len(resources["conditions"]),
        )
        
        return resources
    
    def _lab_to_observation(
        self,
        lab: Dict[str, Any],
        patient_id: str,
        document_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Convert lab value to FHIR Observation."""
        lab_name = lab.get("name", "").lower()
        loinc = LOINC_CODES.get(lab_name)
        
        if not loinc:
            logger.warning("Unknown lab test: %s", lab.get("name"))
            return None
        
        # Parse date
        effective_date = self._parse_date(lab.get("date"))
        if not effective_date:
            effective_date = datetime.now().isoformat()
        
        observation = {
            "resourceType": "Observation",
            "id": str(uuid4()),
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": loinc["code"],
                        "display": loinc["display"],
                    }
                ],
                "text": lab.get("name"),
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "valueQuantity": {
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "system": "http://unitsofmeasure.org",
                "code": self._get_ucum_code(lab.get("unit")),
            },
            "effectiveDateTime": effective_date,
        }
        
        # Add interpretation if available
        if lab.get("interpretation"):
            observation["interpretation"] = [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": self._normalize_interpretation(lab.get("interpretation")),
                        }
                    ]
                }
                ]
        
        # Add reference range if available
        if lab.get("reference_range"):
            observation["referenceRange"] = [
                {
                    "text": lab.get("reference_range"),
                }
            ]
        
        # Add provenance if document_id provided
        if document_id:
            observation["derivedFrom"] = [
                {
                    "reference": f"DocumentReference/{document_id}",
                    "display": "Extracted from document via OCR",
                }
            ]
        
        return observation
    
    def _vital_to_observation(
        self,
        vital: Dict[str, Any],
        patient_id: str,
        document_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Convert vital sign to FHIR Observation."""
        vital_type = vital.get("type", "").lower()
        loinc = VITAL_LOINC.get(vital_type)
        
        if not loinc:
            logger.warning("Unknown vital sign type: %s", vital.get("type"))
            return None
        
        # Parse date
        effective_date = self._parse_date(vital.get("date"))
        if not effective_date:
            effective_date = datetime.now().isoformat()
        
        observation = {
            "resourceType": "Observation",
            "id": str(uuid4()),
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": loinc["code"],
                        "display": loinc["display"],
                    }
                ],
                "text": vital.get("type"),
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "effectiveDateTime": effective_date,
        }
        
        # Handle blood pressure specially (has two values)
        if vital_type == "bp":
            # Parse systolic/diastolic from unit field
            unit_str = vital.get("unit", "")
            if "/" in unit_str:
                parts = unit_str.split("/")
                if len(parts) >= 2:
                    observation["component"] = [
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "8480-6",
                                        "display": "Systolic blood pressure",
                                    }
                                ]
                            },
                            "valueQuantity": {
                                "value": float(parts[0]),
                                "unit": "mmHg",
                                "system": "http://unitsofmeasure.org",
                                "code": "mm[Hg]",
                            },
                        },
                        {
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "8462-4",
                                        "display": "Diastolic blood pressure",
                                    }
                                ]
                            },
                            "valueQuantity": {
                                "value": float(parts[1].split()[0]),
                                "unit": "mmHg",
                                "system": "http://unitsofmeasure.org",
                                "code": "mm[Hg]",
                            },
                        },
                    ]
        else:
            observation["valueQuantity"] = {
                "value": vital.get("value"),
                "unit": vital.get("unit"),
                "system": "http://unitsofmeasure.org",
                "code": self._get_ucum_code(vital.get("unit")),
            }
        
        # Add provenance if document_id provided
        if document_id:
            observation["derivedFrom"] = [
                {
                    "reference": f"DocumentReference/{document_id}",
                    "display": "Extracted from document via OCR",
                }
            ]
        
        return observation
    
    def _med_to_medication_statement(
        self,
        med: Dict[str, Any],
        patient_id: str,
        document_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Convert medication to FHIR MedicationStatement."""
        # Parse date
        effective_date = self._parse_date(med.get("date"))
        if not effective_date:
            effective_date = datetime.now().isoformat()
        
        medication = {
            "resourceType": "MedicationStatement",
            "id": str(uuid4()),
            "status": "active",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "display": med.get("name"),
                    }
                ],
                "text": med.get("name"),
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "effectiveDateTime": effective_date,
        }
        
        # Add dosage if available
        if med.get("dosage") or med.get("frequency"):
            dosage_text = []
            if med.get("dosage"):
                dosage_text.append(med.get("dosage"))
            if med.get("frequency"):
                dosage_text.append(med.get("frequency"))
            if med.get("route"):
                dosage_text.append(f"via {med.get('route')}")
            
            medication["dosage"] = [
                {
                    "text": " ".join(dosage_text),
                }
            ]
        
        # Add provenance if document_id provided
        if document_id:
            medication["derivedFrom"] = [
                {
                    "reference": f"DocumentReference/{document_id}",
                    "display": "Extracted from document via OCR",
                }
            ]
        
        return medication
    
    def _condition_to_fhir(
        self,
        condition: Dict[str, Any],
        patient_id: str,
        document_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Convert condition to FHIR Condition."""
        condition_name = condition.get("name", "").lower()
        
        # Try to find SNOMED code
        snomed = None
        for key, value in SNOMED_CONDITIONS.items():
            if key in condition_name:
                snomed = value
                break
        
        # Parse date
        onset_date = self._parse_date(condition.get("date"))
        if not onset_date:
            onset_date = datetime.now().isoformat()
        
        fhir_condition = {
            "resourceType": "Condition",
            "id": str(uuid4()),
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                        "display": "Active",
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": snomed["code"] if snomed else None,
                        "display": snomed["display"] if snomed else condition.get("name"),
                    }
                ] if snomed else [],
                "text": condition.get("name"),
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "onsetDateTime": onset_date,
        }
        
        # Add provenance if document_id provided
        if document_id:
            fhir_condition["evidence"] = [
                {
                    "detail": [
                        {
                            "reference": f"DocumentReference/{document_id}",
                            "display": "Extracted from document via OCR",
                        }
                    ]
                }
            ]
        
        return fhir_condition
    
    def _create_document_reference(
        self,
        document_id: str,
        patient_id: str,
        parsed_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create DocumentReference for the source document."""
        return {
            "resourceType": "DocumentReference",
            "id": document_id,
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "34133-9",
                        "display": "Summary of episode note",
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "date": datetime.now().isoformat(),
            "content": [
                {
                    "attachment": {
                        "contentType": "application/pdf",
                        "url": f"DocumentReference/{document_id}",
                    }
                }
            ],
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%y",
            "%m-%d-%y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        return None
    
    def _get_ucum_code(self, unit: Optional[str]) -> Optional[str]:
        """Get UCUM code for unit."""
        if not unit:
            return None
        
        unit_lower = unit.lower()
        ucum_map = {
            "mg/dl": "mg/dL",
            "mg/l": "mg/L",
            "meq/l": "meq/L",
            "mmol/l": "mmol/L",
            "g/dl": "g/dL",
            "%": "%",
            "bpm": "/min",
            "°f": "[degF]",
            "°c": "Cel",
            "/min": "/min",
        }
        
        return ucum_map.get(unit_lower, unit)
    
    def _normalize_interpretation(self, interpretation: str) -> str:
        """Normalize interpretation to FHIR code."""
        interp_lower = interpretation.lower()
        
        if "high" in interp_lower or "elevated" in interp_lower:
            return "H"
        elif "low" in interp_lower or "decreased" in interp_lower:
            return "L"
        elif "critical" in interp_lower:
            return "HH"  # Critical high
        elif "normal" in interp_lower:
            return "N"
        else:
            return "N"  # Default to normal


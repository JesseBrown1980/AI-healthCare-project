"""
Medical text parser for extracting structured data from OCR text.

Extracts lab values, medications, vital signs, conditions, and dates from
unstructured medical document text.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LabValue:
    """Extracted lab value."""
    name: str
    value: float
    unit: str
    reference_range: Optional[str] = None
    interpretation: Optional[str] = None
    date: Optional[str] = None
    confidence: float = 1.0


@dataclass
class Medication:
    """Extracted medication."""
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    date: Optional[str] = None
    confidence: float = 1.0


@dataclass
class VitalSign:
    """Extracted vital sign."""
    type: str  # 'bp', 'hr', 'temp', 'rr', 'o2'
    value: float
    unit: str
    date: Optional[str] = None
    confidence: float = 1.0


@dataclass
class Condition:
    """Extracted condition/diagnosis."""
    name: str
    code: Optional[str] = None
    date: Optional[str] = None
    confidence: float = 1.0


class MedicalParser:
    """Parser for extracting structured medical data from OCR text."""
    
    # Common lab test patterns
    LAB_PATTERNS = [
        # Glucose: "Glucose: 95 mg/dL"
        (r'(?i)(glucose|blood.?sugar|bs)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL|mmol/L)',
         'glucose', 'mg/dL'),
        # Hemoglobin A1C: "HbA1c: 6.5%"
        (r'(?i)(hba1c|hemoglobin.?a1c|a1c)\s*[:=]?\s*(\d+\.?\d*)\s*%?',
         'hba1c', '%'),
        # Cholesterol: "Total Cholesterol: 200 mg/dL"
        (r'(?i)(total.?cholesterol|cholesterol)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL)',
         'cholesterol', 'mg/dL'),
        # LDL: "LDL: 120 mg/dL"
        (r'(?i)(ldl|low.?density.?lipoprotein)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL)',
         'ldl', 'mg/dL'),
        # HDL: "HDL: 50 mg/dL"
        (r'(?i)(hdl|high.?density.?lipoprotein)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL)',
         'hdl', 'mg/dL'),
        # Triglycerides: "Triglycerides: 150 mg/dL"
        (r'(?i)(triglycerides?|trig)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL)',
         'triglycerides', 'mg/dL'),
        # Creatinine: "Creatinine: 1.2 mg/dL"
        (r'(?i)(creatinine)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL|mg/L)',
         'creatinine', 'mg/dL'),
        # BUN: "BUN: 20 mg/dL"
        (r'(?i)(bun|blood.?urea.?nitrogen)\s*[:=]?\s*(\d+\.?\d*)\s*(mg/dl|mg/dL)',
         'bun', 'mg/dL'),
        # Sodium: "Na: 140 mEq/L"
        (r'(?i)(sodium|na\+?)\s*[:=]?\s*(\d+\.?\d*)\s*(meq/l|mEq/L|mmol/L)',
         'sodium', 'mEq/L'),
        # Potassium: "K: 4.0 mEq/L"
        (r'(?i)(potassium|k\+?)\s*[:=]?\s*(\d+\.?\d*)\s*(meq/l|mEq/L|mmol/L)',
         'potassium', 'mEq/L'),
        # Hemoglobin: "Hgb: 14.5 g/dL"
        (r'(?i)(hemoglobin|hgb|hb)\s*[:=]?\s*(\d+\.?\d*)\s*(g/dl|g/dL)',
         'hemoglobin', 'g/dL'),
        # White Blood Count: "WBC: 7.5 x10^3/uL"
        (r'(?i)(wbc|white.?blood.?count)\s*[:=]?\s*(\d+\.?\d*)\s*(x10\^?3|k/ul|/ul)',
         'wbc', 'x10^3/uL'),
        # Platelet Count: "Platelets: 250 x10^3/uL"
        (r'(?i)(platelets?|plt)\s*[:=]?\s*(\d+\.?\d*)\s*(x10\^?3|k/ul|/ul)',
         'platelets', 'x10^3/uL'),
    ]
    
    # Medication patterns
    MEDICATION_PATTERNS = [
        # "Lisinopril 10mg daily"
        (r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+\.?\d*)\s*(mg|g|mcg|units?)\s*(?:po|oral|daily|qd|bid|tid|qid|prn)?',
         'name_dosage'),
        # "Metformin 500mg BID"
        (r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+\.?\d*)\s*(mg|g|mcg)\s+(bid|tid|qid|daily|qd|prn)',
         'name_dosage_frequency'),
    ]
    
    # Vital sign patterns
    VITAL_PATTERNS = [
        # Blood Pressure: "BP: 120/80 mmHg"
        (r'(?i)(?:bp|blood.?pressure)\s*[:=]?\s*(\d+)\s*/\s*(\d+)\s*(?:mmhg|mm.?hg)',
         'bp'),
        # Heart Rate: "HR: 72 bpm"
        (r'(?i)(?:hr|heart.?rate|pulse)\s*[:=]?\s*(\d+)\s*(?:bpm|beats?/min)',
         'hr'),
        # Temperature: "Temp: 98.6 F"
        (r'(?i)(?:temp|temperature)\s*[:=]?\s*(\d+\.?\d*)\s*[°]?\s*(?:f|fahrenheit|c|celsius)',
         'temp'),
        # Respiratory Rate: "RR: 16 /min"
        (r'(?i)(?:rr|respiratory.?rate|resp)\s*[:=]?\s*(\d+)\s*(?:/min|breaths?/min)',
         'rr'),
        # Oxygen Saturation: "O2 Sat: 98%"
        (r'(?i)(?:o2|oxygen|o2.?sat|spo2)\s*[:=]?\s*(\d+\.?\d*)\s*%',
         'o2'),
    ]
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse medical text and extract structured data.
        
        Args:
            text: OCR-extracted text from medical document
        
        Returns:
            Dictionary with extracted data:
            - lab_values: List of LabValue
            - medications: List of Medication
            - vital_signs: List of VitalSign
            - conditions: List of Condition
            - dates: List of extracted dates
        """
        if not text or not text.strip():
            return {
                "lab_values": [],
                "medications": [],
                "vital_signs": [],
                "conditions": [],
                "dates": [],
            }
        
        logger.info("Parsing medical text (%d characters)", len(text))
        
        # Extract dates first (used for context)
        dates = self._extract_dates(text)
        
        # Extract structured data
        lab_values = self._extract_lab_values(text, dates)
        medications = self._extract_medications(text, dates)
        vital_signs = self._extract_vital_signs(text, dates)
        conditions = self._extract_conditions(text, dates)
        
        logger.info(
            "Extracted: %d lab values, %d medications, %d vital signs, %d conditions",
            len(lab_values),
            len(medications),
            len(vital_signs),
            len(conditions),
        )
        
        return {
            "lab_values": [self._lab_to_dict(lv) for lv in lab_values],
            "medications": [self._med_to_dict(m) for m in medications],
            "vital_signs": [self._vital_to_dict(vs) for vs in vital_signs],
            "conditions": [self._condition_to_dict(c) for c in conditions],
            "dates": dates,
        }
    
    def _extract_lab_values(self, text: str, dates: List[str]) -> List[LabValue]:
        """Extract lab values from text."""
        lab_values = []
        
        for pattern, name, unit in self.LAB_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    value = float(match.group(2))
                    # Find nearest date
                    date = self._find_nearest_date(text, match.start(), dates)
                    
                    lab_value = LabValue(
                        name=name,
                        value=value,
                        unit=unit,
                        date=date,
                    )
                    lab_values.append(lab_value)
                except (ValueError, IndexError):
                    continue
        
        return lab_values
    
    def _extract_medications(self, text: str, dates: List[str]) -> List[Medication]:
        """Extract medications from text."""
        medications = []
        
        for pattern, pattern_type in self.MEDICATION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    # Initialize variables
                    name = None
                    dosage = None
                    frequency = None
                    
                    if pattern_type == 'name_dosage':
                        name = match.group(1).strip()
                        dosage = f"{match.group(2)} {match.group(3)}"
                    elif pattern_type == 'name_dosage_frequency':
                        name = match.group(1).strip()
                        dosage = f"{match.group(2)} {match.group(3)}"
                        frequency = match.group(4)
                    else:
                        continue
                    
                    if not name or not dosage:
                        continue
                    
                    date = self._find_nearest_date(text, match.start(), dates)
                    
                    medication = Medication(
                        name=name,
                        dosage=dosage,
                        frequency=frequency,
                        date=date,
                    )
                    medications.append(medication)
                except (ValueError, IndexError):
                    continue
        
        return medications
    
    def _extract_vital_signs(self, text: str, dates: List[str]) -> List[VitalSign]:
        """Extract vital signs from text."""
        vital_signs = []
        
        for pattern, vital_type in self.VITAL_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if vital_type == 'bp':
                        # Blood pressure has two values
                        systolic = float(match.group(1))
                        diastolic = float(match.group(2))
                        value = systolic  # Store systolic, include diastolic in unit
                        unit = f"{systolic}/{diastolic} mmHg"
                    else:
                        value = float(match.group(1))
                        unit = self._get_vital_unit(vital_type)
                    
                    date = self._find_nearest_date(text, match.start(), dates)
                    
                    vital = VitalSign(
                        type=vital_type,
                        value=value,
                        unit=unit,
                        date=date,
                    )
                    vital_signs.append(vital)
                except (ValueError, IndexError):
                    continue
        
        return vital_signs
    
    def _extract_conditions(self, text: str, dates: List[str]) -> List[Condition]:
        """Extract conditions/diagnoses from text."""
        conditions = []
        
        # Common condition patterns
        condition_keywords = [
            r'(?i)(?:diagnosis|dx|condition):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?i)(?:diabetes|hypertension|asthma|copd|chf|cad|mi|stroke)',
        ]
        
        for pattern in condition_keywords:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    name = match.group(1) if match.lastindex else match.group(0)
                    date = self._find_nearest_date(text, match.start(), dates)
                    
                    condition = Condition(
                        name=name,
                        date=date,
                    )
                    conditions.append(condition)
                except (ValueError, IndexError):
                    continue
        
        return conditions
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text."""
        dates = []
        
        # Common date patterns
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',  # YYYY-MM-DD
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                dates.append(match.group(0))
        
        return dates
    
    def _find_nearest_date(self, text: str, position: int, dates: List[str]) -> Optional[str]:
        """Find the nearest date to a given position in text."""
        if not dates:
            return None
        
        # Find date positions
        date_positions = []
        for date_str in dates:
            pos = text.find(date_str)
            if pos >= 0:
                date_positions.append((pos, date_str))
        
        if not date_positions:
            return None
        
        # Find nearest
        nearest = min(date_positions, key=lambda x: abs(x[0] - position))
        # Only return if within reasonable distance (500 chars)
        if abs(nearest[0] - position) < 500:
            return nearest[1]
        
        return None
    
    def _get_vital_unit(self, vital_type: str) -> str:
        """Get unit for vital sign type."""
        units = {
            'hr': 'bpm',
            'temp': '°F',
            'rr': '/min',
            'o2': '%',
        }
        return units.get(vital_type, '')
    
    def _lab_to_dict(self, lab: LabValue) -> Dict[str, Any]:
        """Convert LabValue to dictionary."""
        return {
            "name": lab.name,
            "value": lab.value,
            "unit": lab.unit,
            "reference_range": lab.reference_range,
            "interpretation": lab.interpretation,
            "date": lab.date,
            "confidence": lab.confidence,
        }
    
    def _med_to_dict(self, med: Medication) -> Dict[str, Any]:
        """Convert Medication to dictionary."""
        return {
            "name": med.name,
            "dosage": med.dosage,
            "frequency": med.frequency,
            "route": med.route,
            "date": med.date,
            "confidence": med.confidence,
        }
    
    def _vital_to_dict(self, vital: VitalSign) -> Dict[str, Any]:
        """Convert VitalSign to dictionary."""
        return {
            "type": vital.type,
            "value": vital.value,
            "unit": vital.unit,
            "date": vital.date,
            "confidence": vital.confidence,
        }
    
    def _condition_to_dict(self, condition: Condition) -> Dict[str, Any]:
        """Convert Condition to dictionary."""
        return {
            "name": condition.name,
            "code": condition.code,
            "date": condition.date,
            "confidence": condition.confidence,
        }


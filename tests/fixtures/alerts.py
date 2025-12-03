"""
Clinical Alert Test Fixtures
Generates realistic alert/notification data for testing.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import random
import uuid


# Alert templates by severity
ALERT_TEMPLATES = {
    "critical": [
        {
            "code": "CRIT-001",
            "title": "High Cardiovascular Risk Score",
            "message": "Patient has cardiovascular risk score >85%. Recommend immediate specialist consultation.",
            "category": "risk_assessment",
            "action_required": True,
        },
        {
            "code": "CRIT-002",
            "title": "Dangerous Drug Interaction Detected",
            "message": "Potential life-threatening interaction between current medications. Review immediately.",
            "category": "medication",
            "action_required": True,
        },
        {
            "code": "CRIT-003",
            "title": "Abnormal Lab Values - Critical",
            "message": "Lab results outside critical range. Patient may require urgent intervention.",
            "category": "lab_results",
            "action_required": True,
        },
    ],
    "high": [
        {
            "code": "HIGH-001",
            "title": "Elevated Readmission Risk",
            "message": "30-day readmission risk score is elevated. Consider care coordination.",
            "category": "risk_assessment",
            "action_required": True,
        },
        {
            "code": "HIGH-002",
            "title": "Medication Adherence Concern",
            "message": "Patient has not refilled critical medication. Follow up recommended.",
            "category": "medication",
            "action_required": True,
        },
        {
            "code": "HIGH-003",
            "title": "Missing Follow-up Appointment",
            "message": "Patient missed scheduled follow-up after hospitalization.",
            "category": "care_gap",
            "action_required": True,
        },
    ],
    "medium": [
        {
            "code": "MED-001",
            "title": "Preventive Care Due",
            "message": "Annual screening is due. Schedule appointment.",
            "category": "preventive_care",
            "action_required": False,
        },
        {
            "code": "MED-002",
            "title": "Chronic Condition Review Needed",
            "message": "Recommend reviewing chronic condition management plan.",
            "category": "care_management",
            "action_required": False,
        },
    ],
    "low": [
        {
            "code": "LOW-001",
            "title": "Vaccination Reminder",
            "message": "Patient is due for recommended vaccination.",
            "category": "preventive_care",
            "action_required": False,
        },
        {
            "code": "LOW-002",
            "title": "Health Maintenance Reminder",
            "message": "Annual wellness visit recommended.",
            "category": "preventive_care",
            "action_required": False,
        },
    ],
    "info": [
        {
            "code": "INFO-001",
            "title": "New Patient Information Available",
            "message": "Updated patient records received from external provider.",
            "category": "information",
            "action_required": False,
        },
        {
            "code": "INFO-002",
            "title": "Care Plan Updated",
            "message": "Patient's care plan has been updated by care team.",
            "category": "information",
            "action_required": False,
        },
    ],
}


class AlertFactory:
    """Factory for generating test alert data."""
    
    _counter = 0
    
    @classmethod
    def reset(cls):
        """Reset counter for deterministic tests."""
        cls._counter = 0
    
    @classmethod
    def create(
        cls,
        severity: str = "medium",
        patient_id: Optional[str] = None,
        acknowledged: bool = False,
        template_index: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single alert record."""
        cls._counter += 1
        
        # Get templates for severity
        severity = severity.lower()
        if severity not in ALERT_TEMPLATES:
            severity = "medium"
        
        templates = ALERT_TEMPLATES[severity]
        if template_index is not None and 0 <= template_index < len(templates):
            template = templates[template_index]
        else:
            template = templates[cls._counter % len(templates)]
        
        # Generate timestamp (within last 7 days)
        hours_ago = random.randint(1, 7 * 24)
        created_at = datetime.now() - timedelta(hours=hours_ago)
        
        return {
            "id": f"alert-{uuid.uuid4().hex[:8]}",
            "patient_id": patient_id or f"test-patient-{uuid.uuid4().hex[:8]}",
            "severity": severity,
            "code": template["code"],
            "title": template["title"],
            "message": template["message"],
            "category": template["category"],
            "action_required": template["action_required"],
            "acknowledged": acknowledged,
            "acknowledged_by": None if not acknowledged else "test-user",
            "acknowledged_at": None if not acknowledged else datetime.now().isoformat(),
            "created_at": created_at.isoformat(),
            "expires_at": (created_at + timedelta(days=30)).isoformat(),
            **kwargs
        }
    
    @classmethod
    def create_batch(
        cls,
        count: int,
        patient_id: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Create multiple alerts for a patient."""
        return [
            cls.create(
                patient_id=patient_id,
                severity=severity or random.choice(["critical", "high", "medium", "low"])
            )
            for _ in range(count)
        ]


def create_sample_alert(
    severity: str = "medium",
    patient_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sample alert with specified severity."""
    return AlertFactory.create(
        severity=severity,
        patient_id=patient_id,
    )


def create_alert_set(patient_id: str, scenario: str = "high_risk") -> List[Dict[str, Any]]:
    """Create a set of alerts for common scenarios."""
    if scenario == "high_risk":
        return [
            AlertFactory.create(severity="critical", patient_id=patient_id),
            AlertFactory.create(severity="high", patient_id=patient_id),
            AlertFactory.create(severity="high", patient_id=patient_id),
        ]
    elif scenario == "routine":
        return [
            AlertFactory.create(severity="low", patient_id=patient_id),
            AlertFactory.create(severity="info", patient_id=patient_id),
        ]
    elif scenario == "care_gaps":
        return [
            AlertFactory.create(severity="medium", patient_id=patient_id, template_index=0),
            AlertFactory.create(severity="low", patient_id=patient_id, template_index=0),
        ]
    else:
        return [AlertFactory.create(patient_id=patient_id)]

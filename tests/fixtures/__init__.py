# Test Fixtures Package
# Provides factory functions for generating realistic test data

from .patients import PatientFactory, create_sample_patient, create_high_risk_patient
from .conditions import ConditionFactory, create_sample_condition, COMMON_CONDITIONS
from .medications import MedicationFactory, create_sample_medication, COMMON_MEDICATIONS
from .alerts import AlertFactory, create_sample_alert, ALERT_TEMPLATES
from .fhir_bundles import FHIRBundleFactory, create_patient_bundle

__all__ = [
    # Patient fixtures
    "PatientFactory",
    "create_sample_patient", 
    "create_high_risk_patient",
    # Condition fixtures
    "ConditionFactory",
    "create_sample_condition",
    "COMMON_CONDITIONS",
    # Medication fixtures
    "MedicationFactory",
    "create_sample_medication",
    "COMMON_MEDICATIONS",
    # Alert fixtures
    "AlertFactory",
    "create_sample_alert",
    "ALERT_TEMPLATES",
    # FHIR bundle fixtures
    "FHIRBundleFactory",
    "create_patient_bundle",
]

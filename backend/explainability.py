"""Explainability utilities using SHAP for patient risk scoring."""

from __future__ import annotations

from datetime import date
from typing import Dict, Tuple

import numpy as np
import shap


FeatureVector = Tuple[np.ndarray, list[str]]


def _calculate_age(birth_date) -> int:
    """Calculate patient age from an ISO birthdate string or date object."""
    if not birth_date:
        return 0

    try:
        if isinstance(birth_date, str):
            birth = date.fromisoformat(birth_date)
        elif isinstance(birth_date, date):
            birth = birth_date
        else:
            return 0
        today = date.today()
        return today.year - birth.year - (
            (today.month, today.day) < (birth.month, birth.day)
        )
    except Exception:
        return 0


def _extract_feature_vector(patient_data: Dict) -> FeatureVector:
    """Construct the feature vector used for SHAP explanations."""
    patient_info = patient_data.get("patient", {})
    age = _calculate_age(patient_info.get("birthDate"))

    conditions = [c.get("code", "").lower() for c in patient_data.get("conditions", [])]
    medications = patient_data.get("medications", [])
    encounters = patient_data.get("encounters", [])

    medication_count = len(medications)
    hypertension = any("hypertension" in c for c in conditions)
    diabetes = any("diabetes" in c for c in conditions)
    smoking = any("smoke" in c for c in conditions)
    polypharmacy = medication_count > 10
    recent_encounters = len(
        [e for e in encounters if e.get("status") in {"finished", "completed"}]
    )

    features = np.array(
        [
            float(age),
            float(medication_count),
            1.0 if hypertension else 0.0,
            1.0 if diabetes else 0.0,
            1.0 if smoking else 0.0,
            1.0 if polypharmacy else 0.0,
            float(recent_encounters),
        ]
    )

    feature_names = [
        "age",
        "medication_count",
        "hypertension",
        "diabetes",
        "smoking",
        "polypharmacy",
        "recent_encounters",
    ]

    return features, feature_names


def _predict_linear(X: np.ndarray, coeffs: np.ndarray, intercept: float) -> np.ndarray:
    """Vectorized linear prediction helper."""
    return np.dot(X, coeffs) + intercept


def compute_risk_shap(patient_data: Dict) -> Dict[str, Dict[str, float]]:
    """Compute SHAP values for the supported risk scores.

    Args:
        patient_data: Patient record used in :class:`backend.patient_analyzer.PatientAnalyzer`.

    Returns:
        Mapping of risk score name to per-feature SHAP contributions.
    """

    feature_vector, feature_names = _extract_feature_vector(patient_data)

    # Surrogate linear models approximate the scoring logic in ``PatientAnalyzer._calculate_risk_scores``.
    surrogate_models = {
        "cardiovascular_risk": {
            "coeffs": np.array([
                0.0035,  # age factor scaled from 0.35 * (age / 100)
                0.02,  # medication load contribution (capped in original logic)
                0.2,  # hypertension bonus
                0.2,  # diabetes bonus
                0.2,  # smoking bonus
                0.1,  # polypharmacy bonus
                0.0,  # recent encounters not used in CV risk
            ]),
            "intercept": 0.15,
        },
        "readmission_risk": {
            "coeffs": np.array([
                0.0025,  # age factor scaled from 0.25 * (age / 100)
                0.02,  # medication contribution
                0.0,  # hypertension
                0.0,  # diabetes
                0.0,  # smoking
                0.1,  # polypharmacy
                0.05,  # encounter contribution
            ]),
            "intercept": 0.12,
        },
        "medication_non_adherence_risk": {
            "coeffs": np.array([
                0.003,  # age factor scaled from 0.3 * (age / 100)
                0.03,  # medication complexity
                0.0,  # hypertension
                0.0,  # diabetes
                0.0,  # smoking
                0.15,  # polypharmacy
                0.0,  # recent encounters
            ]),
            "intercept": 0.1,
        },
    }

    shap_results: Dict[str, Dict[str, float]] = {}

    background = np.zeros((1, len(feature_names)))

    for risk_name, params in surrogate_models.items():
        coeffs = params["coeffs"]
        intercept = params["intercept"]
        predict_fn = lambda X, c=coeffs, i=intercept: _predict_linear(X, c, i)

        explainer = shap.KernelExplainer(predict_fn, background)
        shap_values = explainer.shap_values(np.array([feature_vector]))[0]

        shap_results[risk_name] = {
            name: float(value) for name, value in zip(feature_names, shap_values)
        }

    return shap_results


__all__ = ["compute_risk_shap"]

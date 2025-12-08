"""Explainability utilities for the baseline risk model.

The module extracts structured features from normalized FHIR data, trains a
lightweight baseline model on synthetic samples, and surfaces SHAP values for
per-patient explanations. The synthetic dataset keeps the workflow
demonstrative while avoiding coupling to clinical data.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

import numpy as np
import shap
from sklearn.linear_model import LogisticRegression

FeatureVector = Tuple[np.ndarray, List[str]]


_BASELINE_MODEL: LogisticRegression | None = None
_MODEL_FEATURES: List[str] | None = None
_BACKGROUND: np.ndarray | None = None
_EXPLAINER: shap.Explainer | None = None


def _calculate_age(birth_date: Any) -> int:
    """Calculate patient age from an ISO birthdate string or date object."""

    if not birth_date:
        return 0

    if isinstance(birth_date, str):
        try:
            birth = date.fromisoformat(birth_date)
        except ValueError:
            return 0
    elif isinstance(birth_date, date):
        birth = birth_date
    else:
        return 0

    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _normalize_patient_payload(patient_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Return the patient payload regardless of caller input shape."""

    if "patient_data" in patient_analysis:
        return patient_analysis.get("patient_data") or {}
    return patient_analysis


def extract_features(patient_analysis: Dict[str, Any]) -> FeatureVector:
    """Extract numeric features for the baseline risk model.

    The function is resilient to missing fields and defaults to zeros when
    values are absent.
    """

    patient_data = _normalize_patient_payload(patient_analysis)
    patient_info = patient_data.get("patient", {})

    conditions = [str(c.get("code", "")).lower() for c in patient_data.get("conditions", [])]
    medications = patient_data.get("medications", [])
    observations = patient_data.get("observations", [])
    encounters = patient_data.get("encounters", [])

    age = float(_calculate_age(patient_info.get("birthDate")))
    num_conditions = float(len(conditions))
    num_medications = float(len(medications))
    num_observations = float(len(observations))
    num_encounters = float(len(encounters))

    has_diabetes = float(any("diab" in code for code in conditions))
    has_hypertension = float(any("hypertension" in code for code in conditions))
    has_smoking_history = float(any("smok" in code for code in conditions))

    feature_names = [
        "age",
        "number_of_conditions",
        "number_of_medications",
        "number_of_observations",
        "number_of_encounters",
        "has_diabetes",
        "has_hypertension",
        "has_smoking_history",
    ]

    features = np.array(
        [
            age,
            num_conditions,
            num_medications,
            num_observations,
            num_encounters,
            has_diabetes,
            has_hypertension,
            has_smoking_history,
        ],
        dtype=float,
    )

    return features, feature_names


def _generate_synthetic_dataset(feature_names: List[str], n_samples: int = 400) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic dataset aligned with the expected feature order."""

    rng = np.random.default_rng(seed=42)
    X = np.zeros((n_samples, len(feature_names)), dtype=float)
    y = np.zeros(n_samples, dtype=int)

    for idx in range(n_samples):
        age = rng.integers(20, 90)
        num_conditions = max(rng.poisson(2), 0)
        num_medications = max(rng.poisson(5), 0)
        num_observations = max(rng.poisson(10), 0)
        num_encounters = max(rng.poisson(3), 0)

        has_diabetes = rng.random() < 0.25
        has_hypertension = rng.random() < 0.35
        has_smoking_history = rng.random() < 0.2

        feature_row = {
            "age": float(age),
            "number_of_conditions": float(num_conditions),
            "number_of_medications": float(num_medications),
            "number_of_observations": float(num_observations),
            "number_of_encounters": float(num_encounters),
            "has_diabetes": float(has_diabetes),
            "has_hypertension": float(has_hypertension),
            "has_smoking_history": float(has_smoking_history),
        }

        logit = (
            0.03 * age
            + 0.06 * num_conditions
            + 0.05 * num_medications
            + 0.04 * num_observations
            + 0.05 * num_encounters
            + (0.6 if has_diabetes else 0.0)
            + (0.5 if has_hypertension else 0.0)
            + (0.4 if has_smoking_history else 0.0)
            - 6.0
        )

        prob = 1.0 / (1.0 + np.exp(-logit))
        label = rng.binomial(1, prob)

        X[idx] = [feature_row[name] for name in feature_names]
        y[idx] = label

    return X, y


def _ensure_model(feature_names: List[str]) -> Tuple[LogisticRegression, shap.Explainer, np.ndarray]:
    """Train or return a cached baseline model and SHAP explainer."""

    global _BASELINE_MODEL, _MODEL_FEATURES, _BACKGROUND, _EXPLAINER

    if _BASELINE_MODEL is not None and _MODEL_FEATURES == feature_names:
        assert _EXPLAINER is not None
        assert _BACKGROUND is not None
        return _BASELINE_MODEL, _EXPLAINER, _BACKGROUND

    X, y = _generate_synthetic_dataset(feature_names)
    model = LogisticRegression(max_iter=500)
    model.fit(X, y)

    background = X[: min(len(X), 50)]
    explainer = shap.Explainer(model, background, feature_names=feature_names)

    _BASELINE_MODEL = model
    _MODEL_FEATURES = list(feature_names)
    _BACKGROUND = background
    _EXPLAINER = explainer

    return model, explainer, background


def explain_risk(patient_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Compute SHAP explanations for the baseline risk model.

    Returns a dictionary containing feature names, SHAP contributions, base
    value, and the model's predicted probability for the positive class.
    """

    features, feature_names = extract_features(patient_analysis)
    model, explainer, _background = _ensure_model(feature_names)

    shap_result = explainer(np.array([features]))
    contributions = [float(value) for value in shap_result.values[0]]
    base_value = float(shap_result.base_values[0])
    risk_score = float(model.predict_proba([features])[0][1])

    return {
        "feature_names": feature_names,
        "shap_values": contributions,
        "base_value": base_value,
        "risk_score": risk_score,
        "model_type": "logistic_regression",
    }


def compute_risk_shap(patient_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Backward-compatible wrapper returning a mapping of SHAP contributions."""

    explanation = explain_risk({"patient_data": patient_data})
    shap_mapping = dict(zip(explanation["feature_names"], explanation["shap_values"]))
    return {"baseline_risk": shap_mapping}


__all__ = ["extract_features", "explain_risk", "compute_risk_shap"]

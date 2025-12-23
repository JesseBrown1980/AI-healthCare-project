import sys
from backend.models import ExplainResponse


def test_explain_response_accepts_current_payload_shape():
    payload = {
        "status": "success",
        "patient_id": "patient-123",
        "feature_names": ["age", "blood_pressure"],
        "shap_values": [0.12, -0.08],
        "base_value": 0.37,
        "risk_score": 0.42,
        "model_type": "baseline_risk",
        "correlation_id": "corr-abc",
    }

    model = ExplainResponse.model_validate(payload)
    dumped = model.model_dump()

    expected_keys = {
        "status",
        "patient_id",
        "feature_names",
        "shap_values",
        "base_value",
        "risk_score",
        "model_type",
        "correlation_id",
    }

    assert set(dumped.keys()) == expected_keys
    assert dumped == payload

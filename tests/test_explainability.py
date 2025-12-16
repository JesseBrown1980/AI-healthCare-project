import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Any, Dict

import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
for path in (ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

patient_analyzer_stub = types.ModuleType("patient_analyzer")


class PatientAnalyzer:  # pragma: no cover - import stub
    pass


patient_analyzer_stub.PatientAnalyzer = PatientAnalyzer
sys.modules.setdefault("patient_analyzer", patient_analyzer_stub)

from backend.explainability import explain_risk
from backend.main import app
from backend.di import get_audit_service, get_patient_analyzer
from backend.security import TokenContext


EXPECTED_FEATURES = [
    "age",
    "number_of_conditions",
    "number_of_medications",
    "number_of_observations",
    "number_of_encounters",
    "has_diabetes",
    "has_hypertension",
    "has_smoking_history",
]


def _synthetic_patient():
    return {
        "patient": {"birthDate": "1950-01-01"},
        "conditions": [
            {"code": "hypertension"},
            {"code": "diabetes"},
            {"code": "smoking history"},
        ],
        "medications": [{"id": f"med-{idx}"} for idx in range(12)],
        "encounters": [
            {"status": "finished"},
            {"status": "completed"},
            {"status": "planned"},
        ],
        "observations": [{"code": "hbA1c", "value": 7.1}],
    }


def test_explain_risk_outputs_reasonable_values():
    patient_data = _synthetic_patient()

    explanation = explain_risk({"patient_data": patient_data})

    assert explanation["feature_names"] == EXPECTED_FEATURES
    assert len(explanation["shap_values"]) == len(EXPECTED_FEATURES)
    assert all(np.isfinite(value) for value in explanation["shap_values"])
    assert 0.0 <= explanation["risk_score"] <= 1.0


def test_explain_endpoint_returns_success():
    payload = _synthetic_patient()

    # Bypass expensive application startup
    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    stub_token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    explain_route = next(
        route for route in app.routes if route.path == "/api/v1/patient/{patient_id}/explain"
    )
    auth_dependency = explain_route.dependant.dependencies[0].call

    class _StubAnalyzer:
        def __init__(self, data: Dict[str, Any]):
            self.data = data
            self.analysis_history = []

        async def analyze(self, patient_id: str, *_, **__):
            record = {"patient_id": patient_id, "patient_data": self.data}
            self.analysis_history.append(record)
            return record

    class _StubAuditService:
        def new_correlation_id(self):
            return "corr-123"

        async def record_event(self, *_, **__):
            return None

    overrides = {
        auth_dependency: lambda: stub_token,
        get_patient_analyzer: lambda: _StubAnalyzer(payload),
        get_audit_service: lambda: _StubAuditService(),
    }

    app.dependency_overrides.update(overrides)

    try:
        with TestClient(app) as client:
            for path in (
                "/api/v1/patient/test-patient/explain",
                "/api/v1/explain/test-patient",
            ):
                response = client.get(path, headers={"Authorization": "Bearer token"})

                assert response.status_code == 200
                body = response.json()
                assert body["status"] == "success"
                assert body["patient_id"] == "test-patient"
                assert body["shap_values"]
                assert body["feature_names"] == EXPECTED_FEATURES
    finally:
        for key in overrides:
            app.dependency_overrides.pop(key, None)

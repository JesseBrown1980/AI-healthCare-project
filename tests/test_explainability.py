import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

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

from backend.explainability import compute_risk_shap
from backend.main import app
from backend.security import TokenContext


EXPECTED_FEATURES = [
    "age",
    "medication_count",
    "hypertension",
    "diabetes",
    "smoking",
    "polypharmacy",
    "recent_encounters",
]


def _synthetic_patient():
    return {
        "patient": {"birthDate": "1950-01-01"},
        "conditions": [
            {"code": "hypertension"},
            {"code": "diabetes"},
            {"code": "smoker"},
        ],
        "medications": [{"id": f"med-{idx}"} for idx in range(12)],
        "encounters": [
            {"status": "finished"},
            {"status": "completed"},
            {"status": "planned"},
        ],
    }


def test_compute_risk_shap_outputs_reasonable_values():
    patient_data = _synthetic_patient()

    shap_values = compute_risk_shap(patient_data)

    assert set(shap_values) == {
        "cardiovascular_risk",
        "readmission_risk",
        "medication_non_adherence_risk",
    }

    for risk_name, contributions in shap_values.items():
        assert set(contributions) == set(EXPECTED_FEATURES)
        assert all(np.isfinite(value) for value in contributions.values())
        assert contributions["age"] > 0.05, f"Age should increase {risk_name}"
        assert contributions["medication_count"] > 0.05
        assert contributions["polypharmacy"] > 0


class _StubFHIRConnector:
    def __init__(self, payload):
        self.payload = payload

    @asynccontextmanager
    async def request_context(self, *_args, **_kwargs):
        yield

    async def get_patient(self, patient_id: str):
        return {"id": patient_id, **self.payload}


def test_explain_endpoint_returns_success(monkeypatch):
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
        route for route in app.routes if route.path == "/api/v1/explain/{patient_id}"
    )
    auth_dependency = explain_route.dependant.dependencies[0].call
    app.dependency_overrides[auth_dependency] = lambda: stub_token

    monkeypatch.setattr(
        "backend.main.fhir_connector",
        _StubFHIRConnector(payload),
        raising=False,
    )
    monkeypatch.setattr("backend.main.audit_service", None, raising=False)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/explain/test-patient",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["patient_id"] == "test-patient"
    assert body["shap_values"]
    assert body["feature_names"] == EXPECTED_FEATURES

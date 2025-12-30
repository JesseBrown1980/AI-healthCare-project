import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from backend.di import (
    get_analysis_job_manager,
    get_audit_service,
    get_fhir_connector,
    get_patient_analyzer,
    get_patient_summary_cache,
)
from backend.main import app
from backend.patient_analyzer import PatientAnalyzer
from backend.security import TokenContext


class _StubAnalyzer:
    def __init__(self, responses: Dict[str, Dict[str, Any]]):
        self.analysis_history = {}
        self._responses = responses

    async def analyze(self, patient_id: str, include_recommendations: bool = False, analysis_focus: str = None):
        result = self._responses[patient_id]
        self.analysis_history.setdefault(patient_id, []).append(result)
        await asyncio.sleep(0)
        return result

    async def get_latest_analysis(self, patient_id: str) -> Dict[str, Any]:
        bucket = self.analysis_history.get(patient_id, [])
        await asyncio.sleep(0)  # Make it async
        return bucket[-1] if bucket else None

    def get_history(self, patient_id: str = None):
        if patient_id:
            return list(self.analysis_history.get(patient_id, []))
        combined = []
        for bucket in self.analysis_history.values():
            combined.extend(bucket)
        return combined


class _StubFHIRConnector:
    @asynccontextmanager
    async def request_context(self, *_args, **_kwargs):
        yield


@pytest.mark.anyio
async def test_dashboard_endpoint_returns_list(monkeypatch, dependency_overrides_guard):
    original_lifespan = app.router.lifespan_context
    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan
    patient_summary_cache = {}

    monkeypatch.setenv("DASHBOARD_PATIENT_IDS", "p1,p2")

    now = datetime.now(timezone.utc).isoformat()
    responses = {
        "p1": {
            "patient_id": "p1",
            "summary": {"patient_name": "Pat One"},
            "risk_scores": {"cardiovascular_risk": 0.8},
            "overall_risk_score": 0.8,
            "alerts": [{"severity": "high"}],
            "highest_alert_severity": "high",
            "analysis_timestamp": now,
            "last_analyzed_at": now,
        },
        "p2": {
            "patient_id": "p2",
            "summary": {"patient_name": "Pat Two"},
            "risk_scores": {"cardiovascular_risk": 0.4},
            "overall_risk_score": 0.4,
            "alerts": [{"severity": "medium"}],
            "highest_alert_severity": "medium",
            "analysis_timestamp": now,
            "last_analyzed_at": now,
        },
    }

    stub_token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    dashboard_route = next(route for route in app.routes if route.path == "/api/v1/patients/dashboard")
    auth_dependency = dashboard_route.dependant.dependencies[0].call
    overrides = dependency_overrides_guard
    overrides[auth_dependency] = lambda: stub_token

    stub_analyzer = _StubAnalyzer(responses)
    overrides[get_patient_analyzer] = lambda: stub_analyzer
    overrides[get_fhir_connector] = lambda: _StubFHIRConnector()
    overrides[get_analysis_job_manager] = lambda: None
    overrides[get_audit_service] = lambda: None
    overrides[get_patient_summary_cache] = lambda: patient_summary_cache

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/patients/dashboard", headers={"Authorization": "Bearer token"})
    finally:
        app.router.lifespan_context = original_lifespan

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2

    for entry in body:
        assert {"patient_id", "name", "latest_risk_score", "highest_alert_severity", "last_analyzed_at"}.issubset(entry.keys())

    assert body[0]["patient_id"] == "p1"
    assert body[0]["highest_alert_severity"] in {"high", "medium", "low", "none", "critical"}
    assert body[0]["latest_risk_score"] == 0.8

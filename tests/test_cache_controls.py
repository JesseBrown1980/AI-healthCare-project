from contextlib import asynccontextmanager

import importlib
import sys

from fastapi.testclient import TestClient

security_module = importlib.import_module("backend.security")
sys.modules["security"] = security_module
audit_module = importlib.import_module("backend.audit_service")
sys.modules["audit_service"] = audit_module
for module_name in [
    "fhir_connector",
    "llm_engine",
    "rag_fusion",
    "s_lora_manager",
    "mlc_learning",
    "aot_reasoner",
    "patient_analyzer",
    "notifier",
    "patient_data_service",
    "recommendation_service",
    "risk_scoring_service",
    "alert_service",
    "notification_service",
]:
    module = importlib.import_module(f"backend.{module_name}")
    sys.modules[module_name] = module

explainability_stub = importlib.import_module("types").SimpleNamespace(
    explain_risk=lambda *_args, **_kwargs: {}
)
sys.modules["explainability"] = explainability_stub

from backend.main import TokenContext, app, patient_summary_cache


class _StubAnalyzer:
    def __init__(self, entries: int):
        self.analysis_history = {"all": [{"patient_id": f"p{idx}"} for idx in range(entries)]}

    def clear_history(self) -> None:
        self.analysis_history.clear()

    def total_history_count(self) -> int:
        return sum(len(bucket) for bucket in self.analysis_history.values())


def _override_auth_dependency(route_path: str, token: TokenContext) -> None:
    route = next(route for route in app.routes if route.path == route_path)
    auth_dependency = route.dependant.dependencies[0].call
    app.dependency_overrides[auth_dependency] = lambda: token


def test_cache_clear_endpoint_resets_caches(monkeypatch):
    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    patient_summary_cache.clear()
    patient_summary_cache.update({"p1": {"summary": {}}, "p2": {"summary": {}}})

    stub_token = TokenContext(
        access_token="token",
        scopes={"user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    _override_auth_dependency("/api/v1/cache/clear", stub_token)

    monkeypatch.setattr("backend.main.patient_analyzer", _StubAnalyzer(entries=3), raising=False)
    monkeypatch.setattr("backend.main.audit_service", None, raising=False)

    with TestClient(app) as client:
        response = client.post("/api/v1/cache/clear", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    body = response.json()
    assert body["summary_cache_entries_cleared"] == 2
    assert body["analysis_history_cleared"] == 3
    assert patient_summary_cache == {}
    assert app.dependency_overrides

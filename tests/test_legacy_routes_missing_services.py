import importlib
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

security_module = importlib.import_module("backend.security")
sys.modules["security"] = security_module

explainability_stub = types.ModuleType("explainability")
explainability_stub.explain_risk = lambda *_args, **_kwargs: {}
sys.modules["explainability"] = explainability_stub

for module_name in [
    "audit_service",
    "fhir_connector",
    "llm_engine",
    "rag_fusion",
    "s_lora_manager",
    "mlc_learning",
    "aot_reasoner",
    "patient_analyzer",
    "notifier",
]:
    module = importlib.import_module(f"backend.{module_name}")
    sys.modules[module_name] = module

from backend.di import (
    get_analysis_job_manager,
    get_audit_service,
    get_fhir_connector,
    get_patient_analyzer,
    get_patient_summary_cache,
)
from backend.main import TokenContext, app


class _FakeFHIRConnector:
    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def request_context(self, *_args, **_kwargs):
        return self._Ctx()

    async def get_patient(self, patient_id: str):
        return {"patient": {"id": patient_id}}


def _override_auth_dependency(route_path: str, token: TokenContext) -> None:
    route = next(route for route in app.routes if route.path == route_path)
    auth_dependency = route.dependant.dependencies[0].call
    app.dependency_overrides[auth_dependency] = lambda: token


@asynccontextmanager
async def noop_lifespan(_app):
    yield


def _prepare_test_app():
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan
    return original_lifespan


def _teardown_test_app(original_lifespan):
    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


@pytest.mark.anyio
@pytest.mark.parametrize(
    "route_path, overrides, expected_detail",
    [
        (
            "/api/v1/patients",
            {
                get_patient_analyzer: lambda: None,
                get_fhir_connector: lambda: None,
                get_audit_service: lambda: None,
            },
            "Patient analyzer not initialized",
        ),
        (
            "/api/v1/alerts",
            {get_patient_analyzer: lambda: None, get_audit_service: lambda: None},
            "Patient analyzer not initialized",
        ),
    ],
)
async def test_legacy_routes_return_503_when_services_missing(
    route_path, overrides, expected_detail
):
    token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    original_lifespan = _prepare_test_app()
    try:
        _override_auth_dependency(route_path, token)
        app.dependency_overrides.update(overrides)

        with TestClient(app) as client:
            response = client.get(route_path, headers={"Authorization": "Bearer token"})
    finally:
        _teardown_test_app(original_lifespan)

    assert response.status_code == 503
    body = response.json()
    assert body.get("detail") == expected_detail or body.get("message") == expected_detail


@pytest.mark.anyio
async def test_dashboard_summary_returns_503_without_analyzer():
    token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    original_lifespan = _prepare_test_app()
    try:
        _override_auth_dependency("/api/v1/dashboard-summary", token)
        app.dependency_overrides[get_patient_analyzer] = lambda: None
        app.dependency_overrides[get_fhir_connector] = lambda: _FakeFHIRConnector()
        app.dependency_overrides[get_analysis_job_manager] = lambda: None
        app.dependency_overrides[get_patient_summary_cache] = lambda: {}
        app.dependency_overrides[get_audit_service] = lambda: None

        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard-summary", headers={"Authorization": "Bearer token"})
    finally:
        _teardown_test_app(original_lifespan)

    assert response.status_code == 503
    body = response.json()
    assert body.get("detail") == "Patient analyzer not initialized" or body.get("message") == "Patient analyzer not initialized"


@pytest.mark.anyio
async def test_patient_fhir_returns_503_without_connector():
    token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    original_lifespan = _prepare_test_app()
    try:
        _override_auth_dependency("/api/v1/patient/{patient_id}/fhir", token)
        app.dependency_overrides[get_fhir_connector] = lambda: None
        app.dependency_overrides[get_audit_service] = lambda: None

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/patient/p-100/fhir", headers={"Authorization": "Bearer token"}
            )
    finally:
        _teardown_test_app(original_lifespan)

    assert response.status_code == 503
    body = response.json()
    assert body.get("detail") == "FHIR connector not initialized" or body.get("message") == "FHIR connector not initialized"


@pytest.mark.anyio
async def test_explain_endpoint_returns_503_without_analyzer():
    token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    original_lifespan = _prepare_test_app()
    try:
        _override_auth_dependency("/api/v1/patient/{patient_id}/explain", token)
        app.dependency_overrides[get_patient_analyzer] = lambda: None
        app.dependency_overrides[get_audit_service] = lambda: None

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/patient/p-200/explain",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        _teardown_test_app(original_lifespan)

    assert response.status_code == 503
    body = response.json()
    assert body.get("detail") == "Patient analyzer not initialized" or body.get("message") == "Patient analyzer not initialized"


@pytest.mark.anyio
async def test_explain_alias_returns_503_without_analyzer():
    token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
    )

    original_lifespan = _prepare_test_app()
    try:
        _override_auth_dependency("/api/v1/explain/{patient_id}", token)
        app.dependency_overrides[get_patient_analyzer] = lambda: None
        app.dependency_overrides[get_audit_service] = lambda: None

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/explain/p-200",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        _teardown_test_app(original_lifespan)

    assert response.status_code == 503
    body = response.json()
    assert body.get("detail") == "Patient analyzer not initialized" or body.get("message") == "Patient analyzer not initialized"

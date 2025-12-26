from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from backend.di import get_audit_service, get_fhir_connector
from backend.main import app
from backend.security import TokenContext


class _StubFhirConnector:
    def __init__(self):
        self.context_calls = []

    @asynccontextmanager
    async def request_context(self, access_token, scopes, patient):
        self.context_calls.append((access_token, scopes, patient))
        yield

    async def get_patient(self, patient_id):
        return {"resourceType": "Patient", "id": patient_id}


class _StubAuditService:
    def __init__(self):
        self.events = []

    def new_correlation_id(self):
        return "test-correlation-id"

    async def record_event(self, **kwargs):
        self.events.append(kwargs)


def test_get_patient_fhir_uses_injected_dependencies():
    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    original_overrides = dict(app.dependency_overrides)
    original_lifespan = app.router.lifespan_context

    stub_connector = _StubFhirConnector()
    stub_audit_service = _StubAuditService()

    route = next(
        route for route in app.routes if route.path == "/api/v1/patient/{patient_id}/fhir"
    )
    auth_dependency = route.dependant.dependencies[0].call

    stub_token = TokenContext(
        access_token="token",
        scopes={"patient/*.read", "user/*.read", "system/*.read"},
        clinician_roles=set(),
        patient=None,
    )

    app.router.lifespan_context = noop_lifespan
    app.dependency_overrides[auth_dependency] = lambda: stub_token
    app.dependency_overrides[get_fhir_connector] = lambda: stub_connector
    app.dependency_overrides[get_audit_service] = lambda: stub_audit_service

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/patient/test-patient/fhir",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        app.dependency_overrides = original_overrides
        app.router.lifespan_context = original_lifespan

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "success"
    assert json_response["patient_id"] == "test-patient"
    assert json_response["data"] == {"resourceType": "Patient", "id": "test-patient"}
    assert "correlation_id" in json_response
    assert json_response.get("error_type") is None
    assert json_response.get("message") is None

    assert stub_connector.context_calls == [("token", stub_token.scopes, None)]
    assert any(event.get("outcome") == "0" for event in stub_audit_service.events)

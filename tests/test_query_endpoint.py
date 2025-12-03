from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from backend.di import (
    get_aot_reasoner,
    get_audit_service,
    get_fhir_connector,
    get_llm_engine,
    get_rag_fusion,
)
from backend.main import app


class _StubAuditService:
    def __init__(self):
        self.events = []

    def new_correlation_id(self) -> str:
        return "stub-correlation-id"

    async def record_event(self, **kwargs):
        self.events.append(kwargs)


class _StubLLMEngine:
    async def query_with_rag(self, **_kwargs):
        return {
            "answer": "stub-answer",
            "reasoning": ["step 1", "step 2"],
            "sources": ["source-1"],
            "confidence": 0.9,
        }


class _StubFhirConnector:
    # The query endpoint does not use the connector when no patient_id is supplied.
    client = None


def _override_dependencies():
    app.dependency_overrides[get_llm_engine] = lambda: _StubLLMEngine()
    app.dependency_overrides[get_rag_fusion] = lambda: object()
    app.dependency_overrides[get_aot_reasoner] = lambda: object()
    app.dependency_overrides[get_fhir_connector] = lambda: _StubFhirConnector()
    app.dependency_overrides[get_audit_service] = lambda: _StubAuditService()


def _restore_lifespan(original_lifespan):
    app.router.lifespan_context = original_lifespan


def test_query_endpoint_returns_payload_and_correlation_header(dependency_overrides_guard):
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan
    _override_dependencies()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/query",
                params={"question": "What is hypertension?"},
                headers={"X-Correlation-ID": "test-correlation-id"},
            )
    finally:
        dependency_overrides_guard.clear()
        _restore_lifespan(original_lifespan)

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "test-correlation-id"

    body = response.json()
    assert body == {
        "status": "success",
        "question": "What is hypertension?",
        "answer": "stub-answer",
        "reasoning": ["step 1", "step 2"],
        "sources": ["source-1"],
        "confidence": 0.9,
    }

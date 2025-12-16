from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from backend.di import get_audit_service, get_optional_mlc_learning
from backend.main import app


class _StubAuditService:
    def new_correlation_id(self) -> str:
        return "test-correlation-id"


class _StubMLCLearning:
    def __init__(self):
        self.calls = []

    async def process_feedback(self, query_id: str, feedback_type: str, corrected_text=None):
        self.calls.append((query_id, feedback_type, corrected_text))


def _override_dependencies(mlc_instance):
    app.dependency_overrides[get_optional_mlc_learning] = lambda: mlc_instance
    app.dependency_overrides[get_audit_service] = lambda: _StubAuditService()


def _reset_overrides(original_lifespan):
    app.dependency_overrides = {}
    app.router.lifespan_context = original_lifespan


def test_feedback_endpoint_processes_feedback():
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    stub_mlc = _StubMLCLearning()
    _override_dependencies(stub_mlc)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/feedback",
                params={"query_id": "q-123", "feedback_type": "positive"},
            )
    finally:
        _reset_overrides(original_lifespan)

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Feedback processed and learning model updated",
        "query_id": "q-123",
    }
    assert stub_mlc.calls == [("q-123", "positive", None)]


def test_feedback_endpoint_returns_503_when_learning_missing():
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    _override_dependencies(None)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/feedback",
                params={"query_id": "q-404", "feedback_type": "negative"},
            )
    finally:
        _reset_overrides(original_lifespan)

    assert response.status_code == 503
    body = response.json()
    assert body.get("message") == "MLC learning system not initialized"
    assert body.get("status") == "error"

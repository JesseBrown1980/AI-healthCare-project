from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from backend.di import get_audit_service, get_s_lora_manager
from backend.main import app


class _StubSLoRAManager:
    def __init__(self, status_response=None, activate_response=None):
        self.status_response = status_response or {}
        self.activate_response = activate_response
        self.activate_calls = []

    async def get_status(self):
        return self.status_response

    async def activate_adapter(self, adapter_name, specialty=None):
        self.activate_calls.append((adapter_name, specialty))
        return self.activate_response


def _noop_lifespan(_app):
    @asynccontextmanager
    async def _lifespan(_):
        yield

    return _lifespan


def test_get_adapters_returns_stubbed_status():
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan(app)

    status_payload = {
        "active": ["cardiology"],
        "available": ["cardiology", "oncology"],
        "memory": {"used_gb": 1.2},
        "specialties": {"cardiology": "Cardiology"},
    }
    stub_manager = _StubSLoRAManager(status_response=status_payload)

    overrides = {
        get_s_lora_manager: lambda: stub_manager,
        get_audit_service: lambda: None,
    }
    app.dependency_overrides.update(overrides)

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/adapters")

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "status": "success",
            "active_adapters": status_payload["active"],
            "available_adapters": status_payload["available"],
            "memory_usage": status_payload["memory"],
            "specialties": status_payload["specialties"],
        }
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def test_activate_adapter_returns_stubbed_result():
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan(app)

    stub_manager = _StubSLoRAManager(activate_response={"loaded": True})

    overrides = {
        get_s_lora_manager: lambda: stub_manager,
        get_audit_service: lambda: None,
    }
    app.dependency_overrides.update(overrides)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/adapters/activate", params={"adapter_name": "cardiology"}
            )

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "status": "success",
            "adapter": "cardiology",
            "active": {"loaded": True},
        }
        assert stub_manager.activate_calls == [("cardiology", None)]
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan

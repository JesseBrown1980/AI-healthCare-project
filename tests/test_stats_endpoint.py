from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi.testclient import TestClient

from backend.di import (
    get_audit_service,
    get_optional_llm_engine,
    get_optional_mlc_learning,
    get_optional_rag_fusion,
    get_optional_s_lora_manager,
)
from backend.main import app


class _StubLLMEngine:
    def __init__(self, stats: Dict[str, Any]):
        self._stats = stats

    def get_stats(self) -> Dict[str, Any]:
        return self._stats


def _noop_lifespan(_app):
    @asynccontextmanager
    async def _lifespan(_):
        yield

    return _lifespan


def test_stats_endpoint_returns_none_when_services_missing(dependency_overrides_guard):
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan(app)

    overrides = {
        get_optional_llm_engine: lambda: None,
        get_optional_rag_fusion: lambda: None,
        get_optional_s_lora_manager: lambda: None,
        get_optional_mlc_learning: lambda: None,
        get_audit_service: lambda: None,
    }
    dependency_overrides_guard.update(overrides)

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        stats = body.get("stats", {})
        for key in ["llm", "rag", "s_lora", "mlc", "rl"]:
            assert key in stats
            assert stats[key] is None
    finally:
        app.router.lifespan_context = original_lifespan


def test_stats_endpoint_includes_stubbed_service_stats(dependency_overrides_guard):
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan(app)

    stub_stats = {"model": "stub-llm"}
    overrides = {
        get_optional_llm_engine: lambda: _StubLLMEngine(stub_stats),
        get_optional_rag_fusion: lambda: None,
        get_optional_s_lora_manager: lambda: None,
        get_optional_mlc_learning: lambda: None,
        get_audit_service: lambda: None,
    }
    dependency_overrides_guard.update(overrides)

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/stats")

        assert response.status_code == 200
        body = response.json()
        stats = body.get("stats", {})
        assert stats.get("llm") == stub_stats
        assert stats.get("rag") is None
    finally:
        app.router.lifespan_context = original_lifespan

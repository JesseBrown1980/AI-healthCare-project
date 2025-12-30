import types
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend import main
from backend.di import (
    get_analysis_job_manager,
    get_audit_service,
    get_container,
    get_fhir_connector,
    get_notifier,
    get_patient_analyzer,
    get_patient_summary_cache,
)
from backend.notifier import Notifier
from backend.patient_analyzer import PatientAnalyzer as RealPatientAnalyzer
from backend.security import TokenContext


class DummyNotifier:
    def __init__(self) -> None:
        self.callback_url = "http://callback.local"
        self.slack_webhook_url = None
        self.sent_payload = None
        self.sent_correlation_id = None
        self.push_notification = None

    async def notify(self, payload, correlation_id: str = ""):
        self.sent_payload = payload
        self.sent_correlation_id = correlation_id
        return {"status": "sent"}

    async def send_push_notification(self, title: str, body: str, deep_link: str, correlation_id: str = ""):
        self.push_notification = {
            "title": title,
            "body": body,
            "deep_link": deep_link,
            "correlation_id": correlation_id,
        }
        return {"status": "push-sent"}


@pytest.mark.anyio
async def test_notifier_sends_fcm_without_callback(monkeypatch):
    notifier = Notifier(callback_url="", fcm_server_key="dummy-key")
    notifier.register_device("token-1", "ios")

    send_fcm = AsyncMock(return_value={"status": "fcm-sent"})
    monkeypatch.setattr(notifier, "_send_fcm", send_fcm)

    result = await notifier.notify({"patient_id": "p-123", "alerts": []})

    send_fcm.assert_awaited_once()
    assert result == {"FCM": {"status": "fcm-sent"}}


class FakeFHIRConnector:
    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def request_context(self, *_, **__):
        return self._Ctx()


class StubFHIRConnector:
    async def get_patient(self, patient_id: str):
        return {
            "patient": {"name": "Test Patient", "gender": "other", "birthDate": "1970-01-01"},
            "conditions": [{"code": "stroke"}],
            "medications": [],
            "encounters": [],
            "observations": [],
        }


class StubSLoRA:
    async def select_adapters(self, specialties=None, patient_data=None):
        return []

    async def activate_adapter(self, adapter):
        return None

    @property
    def adapters(self):
        return {}


class Noop:
    def __getattr__(self, _):
        async def _noop(*_, **__):
            return None

        return _noop


def make_request_with_state(correlation_id: str = ""):
    request = types.SimpleNamespace()
    request.state = types.SimpleNamespace(correlation_id=correlation_id)
    request.query_params = {}
    return request


@pytest.mark.anyio
async def test_patient_analyzer_triggers_notifications_for_critical_alerts(monkeypatch):
    notifier = DummyNotifier()
    analyzer = RealPatientAnalyzer(
        fhir_connector=StubFHIRConnector(),
        llm_engine=Noop(),
        rag_fusion=Noop(),
        s_lora_manager=StubSLoRA(),
        aot_reasoner=Noop(),
        mlc_learning=Noop(),
        notifier=notifier,
        notifications_enabled=True,
    )

    result = await analyzer.analyze(
        patient_id="p-1",
        include_recommendations=False,
        specialty=None,
        notify=True,
        correlation_id="corr-123",
    )

    assert notifier.sent_payload["analysis"]["patient_id"] == "p-1"
    assert notifier.sent_payload["alert_count"] == result["alert_count"]
    assert notifier.sent_payload["deep_link"].endswith("/patients/p-1/analysis")
    assert notifier.sent_payload["title"].startswith("Patient p-1: ")
    assert notifier.sent_payload["body"].startswith("Alerts")
    assert notifier.sent_payload["risk_summary"]
    assert notifier.sent_correlation_id == "corr-123"
    assert notifier.push_notification == {
        "title": notifier.sent_payload["title"],
        "body": notifier.sent_payload["body"],
        "deep_link": "healthcareai://patients/p-1/analysis",
        "correlation_id": "corr-123",
    }


@pytest.mark.anyio
async def test_patient_analyzer_skips_notifications_when_disabled(monkeypatch):
    notifier = DummyNotifier()
    analyzer = RealPatientAnalyzer(
        fhir_connector=StubFHIRConnector(),
        llm_engine=Noop(),
        rag_fusion=Noop(),
        s_lora_manager=StubSLoRA(),
        aot_reasoner=Noop(),
        mlc_learning=Noop(),
        notifier=notifier,
        notifications_enabled=True,
    )

    await analyzer.analyze(
        patient_id="p-2",
        include_recommendations=False,
        specialty=None,
        notify=False,
        correlation_id="corr-999",
    )

    assert notifier.sent_payload is None


def test_registration_endpoints_return_503_when_notifier_missing():
    app = main.app
    original_lifespan = app.router.lifespan_context
    original_overrides = dict(app.dependency_overrides)

    @asynccontextmanager
    async def dummy_lifespan(_app):
        yield

    app.router.lifespan_context = dummy_lifespan

    app.dependency_overrides[get_container] = lambda: types.SimpleNamespace(notifier=None)

    def override_auth():
        return TokenContext(access_token="", scopes=set(), clinician_roles=set())

    target_paths = {
        "/api/v1/device/register",
        "/api/v1/register-device",
        "/api/v1/notifications/register",
    }

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path in target_paths:
            for dependency in route.dependant.dependencies:
                if dependency.call.__module__ == "backend.security":
                    app.dependency_overrides[dependency.call] = override_auth

    try:
        with TestClient(app) as client:
            payload = {"device_token": "token-abc", "platform": "ios"}

            for path in target_paths:
                response = client.post(path, json=payload)
                assert response.status_code == 503
                response_json = response.json()
                # Check for new error response format (with correlation_id, hint, etc.)
                assert response_json.get("status") == "error"
                assert "Notifier not initialized" in response_json.get("message", "") or "Notifier not initialized" in response_json.get("detail", "")
    finally:
        app.dependency_overrides = original_overrides
        app.router.lifespan_context = original_lifespan


class RecordingAnalyzer:
    def __init__(self):
        self.last_notify = None

    async def analyze(
        self,
        patient_id: str,
        include_recommendations: bool = True,
        specialty=None,
        notify: bool = False,
        correlation_id: str = "",
    ):
        self.last_notify = notify
        return {"alerts": [], "risk_scores": {}, "patient_id": patient_id}


@pytest.mark.anyio
async def test_analyze_patient_respects_notify_flag(monkeypatch):
    recorder = RecordingAnalyzer()
    app = main.app
    original_lifespan = app.router.lifespan_context
    original_overrides = dict(app.dependency_overrides)

    @asynccontextmanager
    async def dummy_lifespan(_app):
        yield

    def override_auth():
        return TokenContext(
            access_token="token", scopes=set(), clinician_roles=set(), patient="p-3"
        )

    analyze_route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/api/v1/analyze-patient"
    )

    overrides = {
        get_patient_analyzer: lambda: recorder,
        get_fhir_connector: lambda: FakeFHIRConnector(),
        get_analysis_job_manager: lambda: None,
        get_audit_service: lambda: None,
        get_patient_summary_cache: lambda: {},
    }

    for dependency in analyze_route.dependant.dependencies:
        if dependency.call.__module__ == "backend.security":
            overrides[dependency.call] = override_auth

    app.router.lifespan_context = dummy_lifespan
    app.dependency_overrides.update(overrides)

    try:
        monkeypatch.setattr(main, "notifications_enabled", False)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze-patient",
                params={"fhir_patient_id": "p-3", "notify": "true"},
            )

        assert response.status_code == 200
        assert response.json() == {
            "alerts": [],
            "risk_scores": {},
            "patient_id": "p-3",
        }

        first_notify = recorder.last_notify
        recorder.last_notify = None

        # Clear the cache and reset the recorder
        app.dependency_overrides[get_patient_summary_cache] = lambda: {}
        monkeypatch.setattr(main, "notifications_enabled", True)
        
        # Reset the recorder to ensure fresh state
        recorder.analysis_history = {}

        with TestClient(app) as client:
            second_response = client.post(
                "/api/v1/analyze-patient",
                params={"fhir_patient_id": "p-3", "notify": "true"},
            )

        assert second_response.status_code == 200
        assert second_response.json() == {
            "alerts": [],
            "risk_scores": {},
            "patient_id": "p-3",
        }

        assert first_notify is False
        assert recorder.last_notify is True
    finally:
        app.dependency_overrides = original_overrides
        app.router.lifespan_context = original_lifespan


@pytest.mark.anyio
async def test_register_device_stores_tokens(monkeypatch):
    app = main.app
    notifier = Notifier()

    original_lifespan = app.router.lifespan_context
    original_overrides = dict(app.dependency_overrides)

    @asynccontextmanager
    async def dummy_lifespan(_app):
        yield

    register_route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/api/v1/device/register"
    )

    def override_auth():
        return TokenContext(access_token="token", scopes=set(), clinician_roles=set())

    overrides = {get_notifier: lambda: notifier}

    for dependency in register_route.dependant.dependencies:
        if dependency.call.__module__ == "backend.security":
            overrides[dependency.call] = override_auth

    app.router.lifespan_context = dummy_lifespan
    app.dependency_overrides.update(overrides)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/device/register",
                json={"device_token": "abc123", "platform": "ios"},
                headers={"Authorization": "Bearer token"},
            )
    finally:
        app.dependency_overrides = original_overrides
        app.router.lifespan_context = original_lifespan

    assert response.status_code == 200
    assert response.json() == {
        "status": "registered",
        "device": {"device_token": "abc123", "platform": "iOS"},
    }
    assert notifier.registered_devices == [
        {"device_token": "abc123", "platform": "iOS"}
    ]

import sys
import types
from pathlib import Path

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

# Ensure imports like `import security` inside backend.main work during tests
ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
for path in (ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Stub modules that backend.main expects so we can import without full dependencies
patient_analyzer_stub = types.ModuleType("patient_analyzer")

class PatientAnalyzer:  # pragma: no cover - import stub
    pass

patient_analyzer_stub.PatientAnalyzer = PatientAnalyzer
sys.modules.setdefault("patient_analyzer", patient_analyzer_stub)

shap_stub = types.ModuleType("shap")
sys.modules.setdefault("shap", shap_stub)

sklearn_stub = types.ModuleType("sklearn")
linear_model_stub = types.ModuleType("sklearn.linear_model")


class LogisticRegression:  # pragma: no cover - import stub
    def __init__(self, *_, **__):
        pass

    def fit(self, *_, **__):
        return self

    def predict_proba(self, X):
        return [[0.5, 0.5] for _ in range(len(X))]


linear_model_stub.LogisticRegression = LogisticRegression
sklearn_stub.linear_model = linear_model_stub
sys.modules.setdefault("sklearn", sklearn_stub)
sys.modules.setdefault("sklearn.linear_model", linear_model_stub)

from backend import main  # noqa: E402
from backend.notifier import Notifier  # noqa: E402
from backend.patient_analyzer import PatientAnalyzer as RealPatientAnalyzer  # noqa: E402
from backend.security import TokenContext  # noqa: E402
from backend.di import get_container  # noqa: E402


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

    @asynccontextmanager
    async def dummy_lifespan(_app):
        yield

    app.router.lifespan_context = dummy_lifespan

    class DummyContainer:
        notifier = None

    app.dependency_overrides[get_container] = lambda: DummyContainer()

    def override_auth():
        return TokenContext(access_token="", scopes=set(), clinician_roles=set())

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path in {
            "/api/v1/device/register",
            "/api/v1/register-device",
            "/api/v1/notifications/register",
        }:
            for dependency in route.dependant.dependencies:
                if dependency.call.__module__ == "backend.security":
                    app.dependency_overrides[dependency.call] = override_auth

    try:
        with TestClient(app) as client:
            payload = {"device_token": "token-abc", "platform": "ios"}

            response = client.post("/api/v1/device/register", json=payload)
            assert response.status_code == 503
            assert response.json() == {"detail": "Notifier not initialized"}

            response = client.post("/api/v1/notifications/register", json=payload)
            assert response.status_code == 503
            assert response.json() == {"detail": "Notifier not initialized"}
    finally:
        app.dependency_overrides = {}
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
    monkeypatch.setattr(main, "patient_analyzer", recorder)
    monkeypatch.setattr(main, "fhir_connector", FakeFHIRConnector())
    monkeypatch.setattr(main, "notifications_enabled", False)

    request = make_request_with_state("corr-000")
    auth = TokenContext(access_token="token", scopes=set(), clinician_roles=set(), patient="p-3")

    await main.analyze_patient(
        request,
        fhir_patient_id="p-3",
        include_recommendations=True,
        specialty=None,
        notify=True,
        auth=auth,
    )

    assert recorder.last_notify is False

    monkeypatch.setattr(main, "notifications_enabled", True)

    await main.analyze_patient(
        request,
        fhir_patient_id="p-3",
        include_recommendations=True,
        specialty=None,
        notify=True,
        auth=auth,
    )

    assert recorder.last_notify is True


@pytest.mark.anyio
async def test_register_device_stores_tokens(monkeypatch):
    notifier = Notifier()
    monkeypatch.setattr(main, "notifier", notifier)

    request = make_request_with_state()
    auth = TokenContext(access_token="token", scopes=set(), clinician_roles=set())

    result = await main.register_device(
        main.DeviceRegistration(device_token="abc123", platform="ios"),
        request,
        auth=auth,
        notifier=notifier,
    )

    assert result["status"] == "registered"
    assert notifier.registered_devices == [{"device_token": "abc123", "platform": "iOS"}]

import sys
import types
from pathlib import Path

import pytest

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

from backend import main  # noqa: E402
from backend.notifier import Notifier  # noqa: E402
from backend.security import TokenContext  # noqa: E402


class DummyNotifier:
    def __init__(self) -> None:
        self.callback_url = "http://callback.local"
        self.sent_payload = None
        self.sent_correlation_id = None
        self.push_notification = None
        self.push_correlation_id = None

    async def send(self, payload, correlation_id: str = ""):
        self.sent_payload = payload
        self.sent_correlation_id = correlation_id
        return {"status": "sent"}

    async def send_push_notification(
        self, title: str, body: str, deep_link: str, correlation_id: str = ""
    ):
        self.push_notification = {
            "title": title,
            "body": body,
            "deep_link": deep_link,
        }
        self.push_correlation_id = correlation_id
        return {"status": "push_sent"}


class FakeFHIRConnector:
    class _Ctx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def request_context(self, *_, **__):
        return self._Ctx()


class FakeAnalyzer:
    async def analyze(self, patient_id: str, include_recommendations=True, specialty=None):
        return {
            "alerts": [
                {
                    "severity": "info",
                    "type": "test",
                    "message": "a1",
                    "recommendation": "none",
                }
            ],
            "alert_count": 1,
            "risk_scores": {"sepsis": 0.92},
            "analysis": {"patient": patient_id},
        }


def make_request_with_state(correlation_id: str = ""):
    request = types.SimpleNamespace()
    request.state = types.SimpleNamespace(correlation_id=correlation_id)
    request.query_params = {}
    return request


@pytest.mark.anyio
async def test_analyze_patient_sends_notifications(monkeypatch):
    notifier = DummyNotifier()
    monkeypatch.setattr(main, "notifier", notifier)
    monkeypatch.setattr(main, "fhir_connector", FakeFHIRConnector())
    monkeypatch.setattr(main, "patient_analyzer", FakeAnalyzer())

    request = make_request_with_state("corr-123")
    auth = TokenContext(access_token="token", scopes=set(), clinician_roles=set(), patient="p-1")

    await main.analyze_patient(
        request,
        fhir_patient_id="p-1",
        include_recommendations=True,
        specialty=None,
        notify=True,
        auth=auth,
    )

    assert notifier.sent_payload is not None
    assert notifier.sent_correlation_id == "corr-123"
    assert notifier.push_notification == {
        "title": "Patient analysis ready",
        "body": "Patient p-1: 1 alerts, top risk sepsis 0.92",
        "deep_link": "healthcareai://patients/p-1/analysis",
    }
    assert notifier.push_correlation_id == "corr-123"


@pytest.mark.anyio
async def test_analyze_patient_sends_notifications_without_callback(monkeypatch):
    notifier = DummyNotifier()
    notifier.callback_url = None
    monkeypatch.setattr(main, "notifier", notifier)
    monkeypatch.setattr(main, "fhir_connector", FakeFHIRConnector())
    monkeypatch.setattr(main, "patient_analyzer", FakeAnalyzer())

    request = make_request_with_state("corr-789")
    auth = TokenContext(access_token="token", scopes=set(), clinician_roles=set(), patient="p-2")

    await main.analyze_patient(
        request,
        fhir_patient_id="p-2",
        include_recommendations=True,
        specialty=None,
        notify=True,
        auth=auth,
    )

    assert notifier.sent_payload is not None
    assert notifier.sent_correlation_id == "corr-789"
    assert notifier.push_notification == {
        "title": "Patient analysis ready",
        "body": "Patient p-2: 1 alerts, top risk sepsis 0.92",
        "deep_link": "healthcareai://patients/p-2/analysis",
    }
    assert notifier.push_correlation_id == "corr-789"


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
    )

    assert result["status"] == "registered"
    assert notifier.registered_devices == [{"device_token": "abc123", "platform": "iOS"}]

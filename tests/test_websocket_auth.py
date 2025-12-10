import sys
from types import ModuleType
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, QueryParams
from starlette.websockets import WebSocketDisconnect

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.security as backend_security

sys.modules.setdefault("security", backend_security)
sys.modules.setdefault("backend.security", backend_security)


def _stub_module(name: str, attributes: dict) -> None:
    module = sys.modules.get(name) or ModuleType(name)
    for attr_name, attr_value in attributes.items():
        setattr(module, attr_name, attr_value)
    sys.modules[name] = module
    sys.modules[f"backend.{name}"] = module


class _StubError(Exception):
    pass


_stub_module("audit_service", {"AuditService": type("AuditService", (), {})})
_stub_module(
    "fhir_connector",
    {
        "FHIRConnectorError": _StubError,
        "FhirHttpClient": type("FhirHttpClient", (), {}),
        "FhirResourceService": type("FhirResourceService", (), {}),
    },
)
_stub_module("llm_engine", {"LLMEngine": type("LLMEngine", (), {})})
_stub_module("rag_fusion", {"RAGFusion": type("RAGFusion", (), {})})
_stub_module("s_lora_manager", {"SLoRAManager": type("SLoRAManager", (), {})})
_stub_module("mlc_learning", {"MLCLearning": type("MLCLearning", (), {})})
_stub_module("aot_reasoner", {"AoTReasoner": type("AoTReasoner", (), {})})
_stub_module(
    "patient_analyzer",
    {
        "PatientAnalyzer": type("PatientAnalyzer", (), {"_derive_overall_risk_score": staticmethod(lambda _: 0), "_highest_alert_severity": staticmethod(lambda alerts: None)}),
    },
)
_stub_module("notifier", {"Notifier": type("Notifier", (), {})})
_stub_module("explainability", {"explain_risk": lambda *_, **__: None})


class _StubWebSocket:
    def __init__(self, headers=None, query_params=None):
        self.headers = Headers(headers or {})
        self.query_params = QueryParams(query_params or {})
        self.closed_with = None

    async def close(self, code: int, reason: str | None = None):
        self.closed_with = (code, reason)

import backend.main as main
from backend.security import TokenContext


def _fake_auth_dependency(required_scopes=None, required_roles=None):
    async def _dependency(credentials=None):
        if not credentials or credentials.credentials != "valid-token":
            raise HTTPException(status_code=401, detail="Missing bearer token")

        return TokenContext(
            access_token=credentials.credentials,
            scopes=set(required_scopes or []),
            clinician_roles=set(required_roles or []),
            patient="patient-123",
        )

    return _dependency


def _build_test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "auth_dependency", _fake_auth_dependency)

    app = FastAPI()

    @app.websocket("/ws/patient-updates")
    async def _ws_endpoint(websocket: WebSocket):
        try:
            context = await main._authenticate_websocket(websocket)
        except HTTPException:
            return

        await websocket.accept()
        await websocket.send_json({"patient": context.patient})
        await websocket.close()

    return TestClient(app)


def test_authenticated_websocket_connection(monkeypatch: pytest.MonkeyPatch):
    client = _build_test_client(monkeypatch)

    with client.websocket_connect("/ws/patient-updates?token=valid-token") as websocket:
        message = websocket.receive_json()

    assert message == {"patient": "patient-123"}


@pytest.mark.anyio
async def test_websocket_rejects_missing_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main, "auth_dependency", _fake_auth_dependency)
    websocket = _StubWebSocket()

    with pytest.raises(WebSocketDisconnect) as excinfo:
        await main._authenticate_websocket(websocket)

    assert excinfo.value.code == 4401
    assert websocket.closed_with == (4401, "Missing bearer token")

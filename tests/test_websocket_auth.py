import pytest
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, QueryParams
from starlette.websockets import WebSocketDisconnect

import backend.main as main
from backend.security import TokenContext


class _StubWebSocket:
    def __init__(self, headers=None, query_params=None):
        self.headers = Headers(headers or {})
        self.query_params = QueryParams(query_params or {})
        self.closed_with = None

    async def close(self, code: int, reason: str | None = None):
        self.closed_with = (code, reason)


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

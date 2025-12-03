import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from backend.fhir_http_client import FhirHttpClient


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.content = json.dumps(data).encode()
        self.text = json.dumps(data)

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def request(self, *_args, **_kwargs):
        self.calls += 1
        if not self.responses:
            raise AssertionError("No more responses configured")
        return self.responses.pop(0)


@pytest.mark.anyio
async def test_request_retries_and_succeeds(monkeypatch):
    monkeypatch.setattr(FhirHttpClient, "_configure_from_well_known", lambda *_: None)

    session = FakeSession([FakeResponse({}, status_code=429), FakeResponse({})])
    client = FhirHttpClient("http://fake.fhir", session=session)
    client.access_token = "token"

    response = await client.request("GET", "http://fake.fhir/Patient/p1")

    assert response.status_code == 200
    assert session.calls == 2


@pytest.mark.anyio
async def test_request_refreshes_on_401(monkeypatch):
    monkeypatch.setattr(FhirHttpClient, "_configure_from_well_known", lambda *_: None)

    session = FakeSession([FakeResponse({}, status_code=401), FakeResponse({})])
    client = FhirHttpClient("http://fake.fhir", session=session)
    client.access_token = "token"
    refresh_calls = {"count": 0}

    async def fake_refresh():
        refresh_calls["count"] += 1
        client.access_token = "refreshed"

    monkeypatch.setattr(client, "_refresh_access_token", fake_refresh)

    response = await client.request("GET", "http://fake.fhir/Observation")

    assert response.status_code == 200
    assert refresh_calls["count"] == 1
    assert session.calls == 2


def test_build_authorization_url_includes_pkce_and_context(monkeypatch):
    monkeypatch.setattr(FhirHttpClient, "_configure_from_well_known", lambda *_: None)

    client = FhirHttpClient(
        "http://example.local",
        client_id="client-123",
        auth_url="https://auth.local/authorize",
        token_url="https://auth.local/token",
    )

    redirect_uri = "https://app.example/callback"
    url, state = client.build_authorization_url(
        redirect_uri,
        patient="patient-1",
        user="user-7",
    )

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["client-123"]
    assert params["redirect_uri"] == [redirect_uri]
    assert params["patient"] == ["patient-1"]
    assert params["user"] == ["user-7"]
    assert params["state"] == [state]
    assert client.code_verifier
    assert client.code_challenge


def test_refresh_access_token_falls_back_to_client_credentials(monkeypatch):
    monkeypatch.setattr(FhirHttpClient, "_configure_from_well_known", lambda *_: None)

    client = FhirHttpClient(
        "http://example.local",
        client_id="client-123",
        token_url="https://auth.local/token",
    )
    client.refresh_token = "expired-refresh"

    calls = {"client_credentials": 0}

    async def fake_request_token():
        calls["client_credentials"] += 1

    class RefreshFailingClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse({"error_description": "expired"}, status_code=400)

    monkeypatch.setattr(client, "_request_token", fake_request_token)
    monkeypatch.setattr("backend.fhir_http_client.httpx.AsyncClient", RefreshFailingClient)

    asyncio.run(client._refresh_access_token())

    assert calls["client_credentials"] == 1


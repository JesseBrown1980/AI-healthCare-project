import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from backend.fhir_connector import FHIRConnector


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.content = json.dumps(data).encode()
        self.text = json.dumps(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


def _load(path_parts):
    p = Path(__file__).parent.joinpath(*path_parts)
    return json.loads(p.read_text())


@pytest.mark.anyio
async def test_paginated_observations(monkeypatch):
    connector = FHIRConnector(server_url="http://fake.fhir")
    first_bundle = {
        "entry": [
            {"resource": {"id": "o1", "code": {"coding": [{"display": "BP"}]}, "valueQuantity": {"value": 120}}}
        ],
        "link": [
            {"relation": "next", "url": "http://fake.fhir/Observation?page=2"}
        ],
    }
    second_bundle = {
        "entry": [
            {"resource": {"id": "o2", "code": {"coding": [{"display": "Pulse"}]}, "valueQuantity": {"value": 80}}}
        ]
    }
    calls = {"count": 0}

    async def fake_request(method, url, params=None, correlation_context=""):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse(first_bundle)
        return FakeResponse(second_bundle)

    monkeypatch.setattr(connector, "_request_with_retry", fake_request)
    observations = await connector._get_patient_observations("p1", limit=1)

    assert len(observations) == 2
    assert {obs["id"] for obs in observations} == {"o1", "o2"}
    assert calls["count"] == 2


@pytest.mark.anyio
async def test_patient_cache_and_invalidation(monkeypatch):
    connector = FHIRConnector(server_url="http://fake.fhir", cache_ttl_seconds=60)
    patient_resource = {"id": "p-cache", "name": [{"given": ["Pat"], "family": "Cache"}]}
    calls = {"patient": 0}

    async def fake_request(method, url, params=None, correlation_context=""):
        if "Patient" in url:
            calls["patient"] += 1
            return FakeResponse(patient_resource)
        return FakeResponse({"entry": []})

    async def stubbed(*args, **kwargs):  # pragma: no cover - helper stub
        return []

    monkeypatch.setattr(connector, "_request_with_retry", fake_request)
    monkeypatch.setattr(connector, "_get_patient_conditions", stubbed)
    monkeypatch.setattr(connector, "_get_patient_medications", stubbed)
    monkeypatch.setattr(connector, "_get_patient_observations", stubbed)
    monkeypatch.setattr(connector, "_get_patient_encounters", stubbed)

    await connector.get_patient("p-cache")
    await connector.get_patient("p-cache")
    assert calls["patient"] == 1

    connector.invalidate_cache("p-cache")
    await connector.get_patient("p-cache")
    assert calls["patient"] == 2


def test_normalize_patient_and_stats():
    data_path = Path(__file__).parent / "data" / "sample_patient.json"
    patient_json = json.loads(data_path.read_text())

    connector = FHIRConnector(server_url="http://example.local")
    normalized = connector._normalize_patient(patient_json)

    assert normalized["id"] == patient_json.get("id")
    assert "John" in normalized["name"]
    assert normalized["gender"] == patient_json.get("gender")

    stats = connector.get_stats()
    assert stats["server"] == "http://example.local"
    assert stats["status"] == "connected"


def test_get_patient_with_mocked_http(monkeypatch):
    # Load sample patient and simple bundles for other resources
    patient = _load(["data", "sample_patient.json"])

    condition = {"id": "c1", "code": {"coding": [{"display": "Hypertension", "system": "ICD-10"}]}, "clinicalStatus": {"coding": [{"code": "active"}]}}
    med_request = {"id": "m1", "medicationCodeableConcept": {"coding": [{"display": "Lisinopril", "code": "med-123"}]}, "status": "active"}
    observation = {"id": "o1", "code": {"coding": [{"display": "Hemoglobin"}]}, "valueQuantity": {"value": 13.2, "unit": "g/dL"}}
    encounter = {"id": "e1", "type": [{"coding": [{"display": "Outpatient"}]}], "status": "finished", "period": {"start": "2023-01-01"}}

    cond_bundle = {"entry": [{"resource": condition}]}
    med_bundle = {"entry": [{"resource": med_request}]}
    obs_bundle = {"entry": [{"resource": observation}]}
    enc_bundle = {"entry": [{"resource": encounter}]}

    connector = FHIRConnector(server_url="http://fake.fhir")

    async def fake_get(url, params=None, headers=None):
        # Simple routing by path
        if url.endswith(f"/Patient/{patient.get('id')}") or "/Patient/" in url:
            return FakeResponse(patient)
        if url.endswith("/Condition"):
            return FakeResponse(cond_bundle)
        if url.endswith("/MedicationRequest") or url.endswith("/MedicationRequest"):
            return FakeResponse(med_bundle)
        if url.endswith("/Observation"):
            return FakeResponse(obs_bundle)
        if url.endswith("/Encounter"):
            return FakeResponse(enc_bundle)
        return FakeResponse({})

    class FakeSession:
        request = staticmethod(lambda method, url, params=None, headers=None: fake_get(url, params=params, headers=headers))

    # Patch the connector's session.get
    monkeypatch.setattr(connector, "session", FakeSession())

    # Call the async get_patient via asyncio.run
    result = asyncio.run(connector.get_patient(patient.get("id")))

    assert "patient" in result
    assert result["patient"]["id"] == patient.get("id")
    assert isinstance(result.get("conditions"), list)
    assert isinstance(result.get("medications"), list)
    assert isinstance(result.get("observations"), list)
    assert isinstance(result.get("encounters"), list)


def test_build_authorization_url_includes_pkce_and_context():
    connector = FHIRConnector(
        server_url="http://example.local",
        client_id="client-123",
        auth_url="https://auth.local/authorize",
        token_url="https://auth.local/token",
    )

    redirect_uri = "https://app.example/callback"
    url, state = connector.build_authorization_url(
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
    assert connector.code_verifier
    assert connector.code_challenge


def test_complete_authorization_persists_context(monkeypatch):
    connector = FHIRConnector(
        server_url="http://example.local",
        client_id="client-123",
        auth_url="https://auth.local/authorize",
        token_url="https://auth.local/token",
    )

    connector.code_verifier = "verifier"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, data=None, auth=None):
            assert data["code_verifier"] == "verifier"
            return FakeResponse(
                {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "scope": "patient/*.read user/*.read",
                    "patient": "pat-123",
                    "user": "dr-9",
                    "expires_in": 120,
                }
            )

    monkeypatch.setattr("backend.fhir_connector.httpx.AsyncClient", FakeAsyncClient)

    token_data = asyncio.run(
        connector.complete_authorization("code-abc", "https://app.example/callback")
    )

    assert token_data["access_token"] == connector.access_token
    assert connector.refresh_token == "new-refresh"
    assert connector.patient_context == "pat-123"
    assert connector.user_context == "dr-9"
    assert "patient/*.read" in connector.granted_scopes


def test_refresh_access_token_falls_back_to_client_credentials(monkeypatch):
    connector = FHIRConnector(
        server_url="http://example.local",
        client_id="client-123",
        token_url="https://auth.local/token",
    )
    connector.refresh_token = "expired-refresh"

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

    monkeypatch.setattr(connector, "_request_token", fake_request_token)
    monkeypatch.setattr("backend.fhir_connector.httpx.AsyncClient", RefreshFailingClient)

    asyncio.run(connector._refresh_access_token())

    assert calls["client_credentials"] == 1


@pytest.mark.anyio
async def test_get_patient_paginates_and_concatenates(monkeypatch):
    patient_id = "pat-1"
    connector = FHIRConnector(server_url="http://fake.fhir")

    patient_payload = {"id": patient_id, "name": [{"given": ["Jane"], "family": "Doe"}]}

    condition_bundles = [
        {
            "entry": [
                {"resource": {"id": "c1", "code": {"coding": [{"display": "Cond1"}]}}},
                {"resource": {"id": "c2", "code": {"coding": [{"display": "Cond2"}]}}},
            ],
            "link": [{"relation": "next", "url": "/Condition?page=2"}],
        },
        {"entry": [{"resource": {"id": "c3", "code": {"coding": [{"display": "Cond3"}]}}}]},
    ]

    medication_bundles = [
        {
            "entry": [
                {"resource": {"id": "m1", "medicationCodeableConcept": {"coding": [{"display": "Med1"}]}}},
            ],
            "link": [{"relation": "next", "url": "http://fake.fhir/MedicationRequest?page=2"}],
        },
        {
            "entry": [
                {"resource": {"id": "m2", "medicationCodeableConcept": {"coding": [{"display": "Med2"}]}}},
            ]
        },
    ]

    observation_bundles = [
        {
            "entry": [
                {"resource": {"id": "o1", "code": {"coding": [{"display": "Obs1"}]}}},
            ],
            "link": [{"relation": "next", "url": "Observation?page=2"}],
        },
        {"entry": [{"resource": {"id": "o2", "code": {"coding": [{"display": "Obs2"}]}}}]},
    ]

    encounter_bundles = [
        {
            "entry": [
                {"resource": {"id": "e1", "type": [{"coding": [{"display": "Visit"}]}]}},
            ],
            "link": [{"relation": "next", "url": "Encounter?page=2"}],
        },
        {
            "entry": [
                {"resource": {"id": "e2", "type": [{"coding": [{"display": "Followup"}]}]}},
            ]
        },
    ]

    counters = {"Condition": 0, "MedicationRequest": 0, "Observation": 0, "Encounter": 0}

    async def fake_request(method, url, params=None, headers=None, correlation_context=None):
        if f"/Patient/{patient_id}" in url:
            return FakeResponse(patient_payload)

        for resource, bundles in [
            ("Condition", condition_bundles),
            ("MedicationRequest", medication_bundles),
            ("Observation", observation_bundles),
            ("Encounter", encounter_bundles),
        ]:
            if resource in url:
                idx = counters[resource]
                counters[resource] += 1
                return FakeResponse(bundles[idx])

        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(connector, "_request_with_retry", fake_request)

    result = await connector.get_patient(patient_id)

    assert len(result["conditions"]) == 3
    assert len(result["medications"]) == 2
    assert len(result["observations"]) == 2
    assert len(result["encounters"]) == 2


@pytest.mark.anyio
async def test_get_patient_cache_invalidation_and_expiry(monkeypatch):
    patient_id = "cache-1"
    connector = FHIRConnector(server_url="http://fake.fhir", cache_ttl_seconds=120)

    patient_payloads = [
        {"id": patient_id, "gender": "male", "name": [{"given": ["Alex"], "family": "Cache"}]},
        {"id": patient_id, "gender": "female", "name": [{"given": ["Alex"], "family": "Cache"}]},
    ]

    call_counts = {"patient": 0}

    async def fake_request(method, url, params=None, headers=None, correlation_context=None):
        if f"/Patient/{patient_id}" in url:
            idx = min(call_counts["patient"], len(patient_payloads) - 1)
            call_counts["patient"] += 1
            return FakeResponse(patient_payloads[idx])
        return FakeResponse({"entry": []})

    monkeypatch.setattr(connector, "_request_with_retry", fake_request)

    first = await connector.get_patient(patient_id)
    assert first["patient"]["gender"] == "male"
    assert call_counts["patient"] == 1

    second = await connector.get_patient(patient_id)
    assert second["patient"]["gender"] == "male"
    assert call_counts["patient"] == 1

    connector.invalidate_patient_cache(patient_id)
    third = await connector.get_patient(patient_id)
    assert third["patient"]["gender"] == "female"
    assert call_counts["patient"] == 2

    connector._patient_cache[patient_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    fourth = await connector.get_patient(patient_id)
    assert fourth["patient"]["gender"] == "female"
    assert call_counts["patient"] == 3

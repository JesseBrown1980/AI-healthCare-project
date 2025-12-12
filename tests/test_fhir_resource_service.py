import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from backend.fhir_resource_service import FhirResourceService


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


class StubHttpClient:
    def __init__(self, server_url: str, *, routes):
        self.server_url = server_url
        self.scope = "patient/*.read user/*.read system/*.read"
        self.client_id = "client"
        self.access_token = "token"
        self.granted_scopes = {"patient/*.read", "system/*.read", "user/*.read"}
        self.patient_context = None
        self.user_context = None
        self._routes = routes
        self.calls = []

    async def ensure_valid_token(self):
        return None

    def get_effective_context(self):
        return self.access_token, self.granted_scopes, self.patient_context, self.user_context

    async def request(self, method, url, params=None, correlation_context="", json=None):
        self.calls.append(url)
        handler = self._routes.get(url)
        if callable(handler):
            return await handler(method, url, params=params, json=json)
        if isinstance(handler, list):
            if not handler:
                raise AssertionError("No more responses configured")
            return handler.pop(0)
        return handler

    async def get_resource(self, url, params=None, correlation_context=""):
        return await self.request("GET", url, params=params, correlation_context=correlation_context)

    def request_context(self, *args, **kwargs):  # pragma: no cover - passthrough helper
        async def _ctx():
            yield

        return _ctx()


def _load(path_parts):
    p = Path(__file__).parent.joinpath(*path_parts)
    return json.loads(p.read_text())


@pytest.mark.anyio
async def test_paginated_observations():
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

    client = StubHttpClient(
        "http://fake.fhir",
        routes={
            "http://fake.fhir/Observation": [FakeResponse(first_bundle), FakeResponse(second_bundle)],
            "http://fake.fhir/Observation?page=2": FakeResponse(second_bundle),
        },
    )
    service = FhirResourceService(client)

    observations = await service._get_patient_observations("p1", limit=1)

    assert len(observations) == 2
    assert {obs["id"] for obs in observations} == {"o1", "o2"}
    assert client.calls == [
        "http://fake.fhir/Observation",
        "http://fake.fhir/Observation?page=2",
    ]


def test_resolve_next_link_with_relative_url():
    client = StubHttpClient("http://fake.fhir", routes={})
    service = FhirResourceService(client)
    bundle = {"link": [{"relation": "next", "url": "/Condition?_page=2"}]}

    resolved = service._resolve_next_link(bundle)

    assert resolved == "http://fake.fhir/Condition?_page=2"


@pytest.mark.anyio
async def test_get_patient_conditions_resolves_relative_next():
    first_bundle = {
        "entry": [{"resource": {"id": "c1", "code": {"coding": [{}]}}}],
        "link": [{"relation": "next", "url": "/Condition?_page=2"}],
    }
    second_bundle = {"entry": [{"resource": {"id": "c2", "code": {"coding": [{}]}}}]}
    routes = {
        "http://fake.fhir/Condition": [FakeResponse(first_bundle), FakeResponse(second_bundle)],
        "http://fake.fhir/Condition?_page=2": FakeResponse(second_bundle),
    }
    client = StubHttpClient("http://fake.fhir", routes=routes)
    service = FhirResourceService(client)

    conditions = await service._get_patient_conditions("p1")

    assert [condition["id"] for condition in conditions] == ["c1", "c2"]
    assert client.calls == [
        "http://fake.fhir/Condition",
        "http://fake.fhir/Condition?_page=2",
    ]


@pytest.mark.anyio
async def test_patient_cache_and_invalidation(monkeypatch):
    patient_resource = {"id": "p-cache", "name": [{"given": ["Pat"], "family": "Cache"}]}
    routes = {
        "http://fake.fhir/Patient/p-cache": [FakeResponse(patient_resource), FakeResponse(patient_resource)],
    }
    client = StubHttpClient("http://fake.fhir", routes=routes)
    service = FhirResourceService(client, cache_ttl_seconds=60)

    async def stubbed(*_args, **_kwargs):  # pragma: no cover - helper stub
        return []

    monkeypatch.setattr(service, "_get_patient_conditions", stubbed)
    monkeypatch.setattr(service, "_get_patient_medications", stubbed)
    monkeypatch.setattr(service, "_get_patient_observations", stubbed)
    monkeypatch.setattr(service, "_get_patient_encounters", stubbed)

    await service.get_patient("p-cache")
    await service.get_patient("p-cache")
    assert len(client.calls) == 1

    service.invalidate_cache("p-cache")
    await service.get_patient("p-cache")
    assert len(client.calls) == 2


def test_normalize_patient_and_stats():
    data_path = Path(__file__).parent / "data" / "sample_patient.json"
    patient_json = json.loads(data_path.read_text())

    client = StubHttpClient("http://example.local", routes={})
    service = FhirResourceService(client)
    normalized = service._normalize_patient(patient_json)

    assert normalized["id"] == patient_json.get("id")
    assert "John" in normalized["name"]
    assert normalized["gender"] == patient_json.get("gender")

    stats = service.get_stats()
    assert stats["server"] == "http://example.local"
    assert stats["status"] == "connected"


def test_get_patient_with_mocked_http(monkeypatch):
    patient = _load(["data", "sample_patient.json"])

    condition = {"id": "c1", "code": {"coding": [{"display": "Hypertension", "system": "ICD-10"}]}, "clinicalStatus": {"coding": [{"code": "active"}]}}
    med_request = {"id": "m1", "medicationCodeableConcept": {"coding": [{"display": "Lisinopril", "code": "med-123"}]}, "status": "active"}
    observation = {"id": "o1", "code": {"coding": [{"display": "Hemoglobin"}]}, "valueQuantity": {"value": 13.2, "unit": "g/dL"}}
    encounter = {"id": "e1", "type": [{"coding": [{"display": "Outpatient"}]}], "status": "finished", "period": {"start": "2023-01-01"}}

    cond_bundle = {"entry": [{"resource": condition}]}
    med_bundle = {"entry": [{"resource": med_request}]}
    obs_bundle = {"entry": [{"resource": observation}]}
    enc_bundle = {"entry": [{"resource": encounter}]}

    routes = {
        f"http://fake.fhir/Patient/{patient.get('id')}": FakeResponse(patient),
        "http://fake.fhir/Condition": FakeResponse(cond_bundle),
        "http://fake.fhir/MedicationRequest": FakeResponse(med_bundle),
        "http://fake.fhir/Observation": FakeResponse(obs_bundle),
        "http://fake.fhir/Encounter": FakeResponse(enc_bundle),
    }
    client = StubHttpClient("http://fake.fhir", routes=routes)
    service = FhirResourceService(client)

    result = asyncio.run(service.get_patient(patient.get("id")))

    assert "patient" in result
    assert result["patient"]["id"] == patient.get("id")
    assert isinstance(result.get("conditions"), list)
    assert isinstance(result.get("medications"), list)
    assert isinstance(result.get("observations"), list)
    assert isinstance(result.get("encounters"), list)


@pytest.mark.anyio
async def test_get_patient_cache_invalidation_and_expiry(monkeypatch):
    patient_id = "cache-1"
    patient_payloads = [
        {"id": patient_id, "gender": "male", "name": [{"given": ["Alex"], "family": "Cache"}]},
        {"id": patient_id, "gender": "female", "name": [{"given": ["Alex"], "family": "Cache"}]},
    ]

    routes = {
        f"http://fake.fhir/Patient/{patient_id}": [
            FakeResponse(patient_payloads[0]),
            FakeResponse(patient_payloads[1]),
            FakeResponse(patient_payloads[1]),
        ]
    }
    client = StubHttpClient("http://fake.fhir", routes=routes)
    service = FhirResourceService(client, cache_ttl_seconds=120)

    async def fake_bundle(*_args, **_kwargs):  # pragma: no cover - helper stub
        return []

    monkeypatch.setattr(service, "_get_patient_conditions", fake_bundle)
    monkeypatch.setattr(service, "_get_patient_medications", fake_bundle)
    monkeypatch.setattr(service, "_get_patient_observations", fake_bundle)
    monkeypatch.setattr(service, "_get_patient_encounters", fake_bundle)

    first = await service.get_patient(patient_id)
    assert first["patient"]["gender"] == "male"
    assert len(client.calls) == 1

    second = await service.get_patient(patient_id)
    assert second["patient"]["gender"] == "male"
    assert len(client.calls) == 1

    service.invalidate_patient_cache(patient_id)
    third = await service.get_patient(patient_id)
    assert third["patient"]["gender"] == "female"
    assert len(client.calls) == 2

    service._patient_cache[patient_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    fourth = await service.get_patient(patient_id)
    assert fourth["patient"]["gender"] == "female"
    assert len(client.calls) == 3


def test_sample_data_mode_serves_offline_patient(monkeypatch):
    client = StubHttpClient("http://unused.fhir", routes={})
    service = FhirResourceService(client, enable_sample_data=True)

    result = asyncio.run(service.get_patient("offline-1"))

    assert result["patient"]["id"] == "offline-1"
    assert result["conditions"]
    assert result["medications"]
    assert result["observations"]
    assert result["encounters"]
    assert client.calls == []


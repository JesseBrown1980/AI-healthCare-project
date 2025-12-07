import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from backend.fhir_connector import FHIRConnector


class FakeResponse:
    def __init__(self, data: Any, status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.content = json.dumps(data).encode()
        self.text = json.dumps(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class FakeDiscoveryClient:
    def __init__(self, *args, **kwargs):
        self.doc = kwargs.pop(
            "doc",
            {
                "authorization_endpoint": "https://auth.example/authorize",
                "token_endpoint": "https://auth.example/token",
                "scopes_supported": "patient/*.read user/*.read",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str):
        return FakeResponse(self.doc)


@pytest.mark.anyio
async def test_epic_paginated_observations_with_smart_auth(monkeypatch):
    monkeypatch.setattr("backend.fhir_connector.httpx.Client", FakeDiscoveryClient)

    connector = FHIRConnector(
        server_url="https://epic.example/fhir", vendor="epic", client_id="client-1"
    )

    token_calls = {"count": 0}

    async def fake_request_token():
        token_calls["count"] += 1
        connector.access_token = "epic-token"
        connector.granted_scopes = {"patient/Observation.read"}
        connector.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    monkeypatch.setattr(connector, "_request_token", fake_request_token)

    first_bundle = {
        "entry": [
            {
                "resource": {
                    "id": "obs-1",
                    "code": {"coding": [{"display": "Systolic"}]},
                    "valueQuantity": {"value": 118},
                }
            }
        ],
        "link": [{"relation": "next", "url": "/Observation?page=2"}],
    }
    second_bundle = {
        "entry": [
            {
                "resource": {
                    "id": "obs-2",
                    "code": {"coding": [{"display": "Diastolic"}]},
                    "valueQuantity": {"value": 76},
                }
            }
        ]
    }

    calls: List[str] = []

    class FakeSession:
        async def request(self, method, url, params=None, headers=None):
            calls.append(url)
            assert headers.get("Authorization") == "Bearer epic-token"
            if url.endswith("/Observation"):
                return FakeResponse(first_bundle)
            return FakeResponse(second_bundle)

    connector.session = FakeSession()

    observations = await connector._get_patient_observations("pat-epic", limit=1)

    assert token_calls["count"] == 1
    assert [obs["id"] for obs in observations] == ["obs-1", "obs-2"]
    assert calls == [
        "https://epic.example/fhir/Observation",
        "https://epic.example/fhir/Observation?page=2",
    ]


@pytest.mark.anyio
async def test_cerner_patient_flow_includes_pagination_and_normalization(monkeypatch):
    monkeypatch.setattr("backend.fhir_connector.httpx.Client", FakeDiscoveryClient)

    connector = FHIRConnector(
        server_url="https://cerner.example/r4", vendor="cerner", client_id="client-2"
    )

    token_calls = {"count": 0}

    async def fake_request_token():
        token_calls["count"] += 1
        connector.access_token = "cerner-token"
        connector.granted_scopes = {"patient/*.read"}
        connector.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    monkeypatch.setattr(connector, "_request_token", fake_request_token)

    patient_resource: Dict[str, Any] = {
        "id": "cerner-p1",
        "gender": "female",
        "birthDate": "1978-04-10",
        "name": [{"given": ["Taylor"], "family": "Cerner"}],
        "telecom": [{"system": "phone", "value": "555-0100"}],
        "address": [{"line": ["123 Cerner Way"], "city": "Kansas City"}],
        "contact": [{"name": {"text": "Emergency Contact"}}],
        "extension": [
            {
                "url": "https://fhir-ehr.cerner.com/special",
                "valueString": "vendor-metadata",
            }
        ],
    }

    condition_bundles = [
        {
            "entry": [
                {
                    "resource": {
                        "id": "c-1",
                        "code": {"coding": [{"display": "Condition One"}]},
                    }
                }
            ],
            "link": [{"relation": "next", "url": "Condition?page=2"}],
        },
        {
            "entry": [
                {
                    "resource": {
                        "id": "c-2",
                        "code": {"coding": [{"display": "Condition Two"}]},
                    }
                }
            ]
        },
    ]

    counters = {"Condition": 0}
    urls_seen: List[str] = []

    class FakeSession:
        async def request(self, method, url, params=None, headers=None):
            urls_seen.append(url)
            assert headers.get("Authorization") == "Bearer cerner-token"

            if "/Patient/" in url:
                return FakeResponse(patient_resource)
            if "Condition" in url:
                idx = counters["Condition"]
                counters["Condition"] += 1
                return FakeResponse(condition_bundles[idx])
            return FakeResponse({"entry": []})

    connector.session = FakeSession()

    result = await connector.get_patient("cerner-p1")

    assert token_calls["count"] == 1
    assert result["patient"]["id"] == "cerner-p1"
    assert result["patient"]["name"] == "Taylor Cerner"
    assert result["patient"]["gender"] == "female"
    assert result["patient"]["telecom"] == patient_resource["telecom"]
    assert "extension" not in result["patient"]
    assert len(result["conditions"]) == 2
    assert urls_seen.count("https://cerner.example/r4/Condition?page=2") == 1

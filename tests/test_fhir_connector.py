import json
from pathlib import Path
import asyncio

from backend.fhir_connector import FHIRConnector


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


def _load(path_parts):
    p = Path(__file__).parent.joinpath(*path_parts)
    return json.loads(p.read_text())


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

    async def fake_get(url, params=None):
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
        async def get(self, url, params=None):
            return await fake_get(url, params=params)

        async def aclose(self):
            return None

    # Close the real async client to avoid unclosed resource warnings
    asyncio.run(connector.aclose())
    # Patch the connector's session with the fake async session
    monkeypatch.setattr(connector, "session", FakeSession())

    # Call the async get_patient via asyncio.run
    result = asyncio.run(connector.get_patient(patient.get("id")))

    assert "patient" in result
    assert result["patient"]["id"] == patient.get("id")
    assert isinstance(result.get("conditions"), list)
    assert isinstance(result.get("medications"), list)
    assert isinstance(result.get("observations"), list)
    assert isinstance(result.get("encounters"), list)

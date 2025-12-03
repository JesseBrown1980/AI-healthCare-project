import pytest

from backend.patient_data_service import PatientDataService


class DummyFHIRConnector:
    async def get_patient(self, patient_id: str):
        return {
            "patient": {
                "id": patient_id,
                "name": "Test Patient",
                "gender": "female",
                "birthDate": "1980-01-01",
            },
            "conditions": [{"code": "Hypertension"}],
            "medications": [{"medication": "MedA"}],
            "encounters": [{"status": "finished"}],
        }


@pytest.mark.anyio
async def test_patient_data_service_fetch_and_summary():
    service = PatientDataService(DummyFHIRConnector())

    patient_data = await service.fetch_patient_data("patient-123")
    summary = await service.generate_summary(patient_data)

    assert patient_data["patient"]["id"] == "patient-123"
    assert summary["patient_name"] == "Test Patient"
    assert summary["active_conditions_count"] == 1
    assert "narrative_summary" in summary

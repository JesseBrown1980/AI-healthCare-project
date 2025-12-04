import pytest

from backend.patient_analyzer import PatientAnalyzer


@pytest.mark.anyio
async def test_risk_scores_and_polypharmacy_for_older_patients():
    analyzer = PatientAnalyzer(
        fhir_connector=None,
        llm_engine=None,
        rag_fusion=None,
        s_lora_manager=None,
        aot_reasoner=None,
        mlc_learning=None,
    )

    patient_data = {
        "patient": {"id": "elder", "name": "Elder Test", "gender": "male", "birthDate": "1940-01-01"},
        "conditions": [{"code": "Hypertension"}],
        "medications": [
            {"medication": f"Med {i}", "status": "active"} for i in range(12)
        ],
        "encounters": [{"status": "finished"}],
    }

    risk_scores = await analyzer._calculate_risk_scores(patient_data)
    medication_review = await analyzer._medication_review(patient_data)

    assert risk_scores["cardiovascular_risk"] >= 0.45
    assert risk_scores["medication_non_adherence_risk"] >= 0.7
    assert risk_scores["polypharmacy"] is True

    assert any("Polypharmacy" in issue for issue in medication_review.get("potential_issues", []))

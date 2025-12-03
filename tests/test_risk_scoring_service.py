import asyncio

import pytest

from backend.risk_scoring_service import RiskScoringService


def test_risk_scores_and_polypharmacy_for_older_patients():
    service = RiskScoringService()

    patient_data = {
        "patient": {
            "id": "elder",
            "name": "Elder Test",
            "gender": "male",
            "birthDate": "1940-01-01",
        },
        "conditions": [{"code": "Hypertension"}],
        "medications": [{"medication": f"Med {i}", "status": "active"} for i in range(12)],
        "encounters": [{"status": "finished"}],
    }

    risk_scores = asyncio.run(service.calculate_risk_scores(patient_data))
    medication_review = asyncio.run(service.review_medications(patient_data))

    assert 0 <= risk_scores["cardiovascular_risk"] <= 1
    assert 0 <= risk_scores["medication_non_adherence_risk"] <= 1
    assert risk_scores["polypharmacy"] is True
    assert risk_scores["polypharmacy_risk"] is True
    assert any(
        "Polypharmacy" in issue for issue in medication_review.get("potential_issues", [])
    )


def test_risk_scores_include_age_and_medication_load():
    service = RiskScoringService()

    younger_patient = {
        "patient": {"id": "young", "birthDate": "2005-01-01"},
        "conditions": [],
        "medications": [],
        "encounters": [],
    }

    older_polypharmacy_patient = {
        "patient": {"id": "senior", "birthDate": "1950-01-01"},
        "conditions": [{"code": "Hypertension"}, {"code": "Diabetes"}],
        "medications": [{"medication": f"M{i}"} for i in range(15)],
        "encounters": [{"status": "finished"} for _ in range(3)],
    }

    young_scores = asyncio.run(service.calculate_risk_scores(younger_patient))
    senior_scores = asyncio.run(
        service.calculate_risk_scores(older_polypharmacy_patient)
    )

    assert young_scores["cardiovascular_risk"] < senior_scores["cardiovascular_risk"]
    assert senior_scores["readmission_risk"] > 0.2
    assert senior_scores["polypharmacy_risk"] is True

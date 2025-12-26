import asyncio

import pytest

from backend.risk_scoring_service import RiskScoringService



def test_patient_services_risk_scoring_flags_polypharmacy_at_ten_medications():
    service = RiskScoringService()
    patient_data = {
        "patient": {"id": "boundary", "birthDate": "1960-01-01"},
        "conditions": [],
        "medications": [{"medication": f"M{i}"} for i in range(10)],
        "encounters": [],
    }

    risk_scores = asyncio.run(service.calculate_risk_scores(patient_data))

    assert risk_scores["polypharmacy"] is True
    assert risk_scores["polypharmacy_risk"] is True


def test_medication_review_flags_polypharmacy_issue_at_ten_medications():
    review_service = RiskScoringService()
    patient_data = {
        "patient": {"id": "boundary"},
        "medications": [{"medication": f"Rx{i}", "status": "active"} for i in range(10)],
    }

    review = asyncio.run(review_service.review_medications(patient_data))

    assert review["total_medications"] == 10
    assert any(
        "Polypharmacy" in issue for issue in review.get("potential_issues", [])
    )

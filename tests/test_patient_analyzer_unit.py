import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.modules.setdefault(
    "httpx",
    SimpleNamespace(
        AsyncClient=type("AsyncClient", (), {}),
        Client=type("Client", (), {}),
        TimeoutException=Exception,
        RequestError=Exception,
        HTTPError=Exception,
        Response=type("Response", (), {}),
        QueryParams=lambda params: params,
        Headers=dict,
    ),
)


class _DummyTaskGroup:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def spawn(self, *args, **kwargs):
        return None


sys.modules.setdefault(
    "anyio", SimpleNamespace(create_task_group=lambda: _DummyTaskGroup())
)

from backend.patient_analyzer import PatientAnalyzer


class DummyAdapterManager:
    adapters = {"cardio": {"specialty": "cardiology"}}

    async def select_adapters(self, specialties, patient_data):
        return ["cardio"]

    async def activate_adapter(self, adapter):
        return None


def test_patient_analyzer_orchestrates_services():
    patient_data_service = AsyncMock()
    patient_data_service.fetch_patient_data.return_value = {"patient": {"id": "p1"}}
    patient_data_service.generate_summary.return_value = {"summary": True}

    risk_service = AsyncMock()
    risk_service.calculate_risk_scores.return_value = {
        "risk": 0.5,
        "polypharmacy": False,
        "polypharmacy_risk": False,
    }
    risk_service.derive_overall_risk_score = lambda scores: 0.5
    risk_service.review_medications.return_value = {"total_medications": 0}

    alert_service = AsyncMock()
    alert_service.identify_alerts.return_value = [
        {"severity": "critical", "message": "alert"}
    ]
    alert_service.highest_alert_severity = lambda alerts: "critical"

    recommendation_service = AsyncMock()
    recommendation_service.generate_recommendations.return_value = {
        "clinical_recommendations": [{"recommendation": "do"}]
    }

    notification_service = AsyncMock()

    analyzer = PatientAnalyzer(
        fhir_connector=None,
        llm_engine=None,
        rag_fusion=None,
        s_lora_manager=DummyAdapterManager(),
        aot_reasoner=None,
        mlc_learning=None,
        patient_data_service=patient_data_service,
        risk_scoring_service=risk_service,
        recommendation_service=recommendation_service,
        alert_service=alert_service,
        notification_service=notification_service,
    )

    result = asyncio.run(analyzer.analyze("p1", notify=True))

    patient_data_service.fetch_patient_data.assert_awaited_with("p1")
    alert_service.identify_alerts.assert_awaited()
    risk_service.calculate_risk_scores.assert_awaited()
    recommendation_service.generate_recommendations.assert_awaited()
    notification_service.notify_if_needed.assert_awaited()

    assert result["patient_id"] == "p1"
    assert result["highest_alert_severity"] == "critical"
    assert result["polypharmacy_risk"] is False
    assert result["risk_scores"]["polypharmacy"] is False

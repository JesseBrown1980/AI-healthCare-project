from datetime import datetime, timezone
from unittest.mock import MagicMock

from backend.patient_analyzer import PatientAnalyzer


class _StubAdapterManager:
    adapters = {}

    async def select_adapters(self, *_, **__):
        return []

    async def activate_adapter(self, *_args, **_kwargs):
        return None


def test_history_limit_keeps_recent_entries():
    analyzer = PatientAnalyzer(
        fhir_connector=None,
        llm_engine=None,
        rag_fusion=None,
        s_lora_manager=_StubAdapterManager(),
        aot_reasoner=None,
        mlc_learning=None,
        patient_data_service=MagicMock(),
        risk_scoring_service=MagicMock(),
        recommendation_service=MagicMock(),
        alert_service=MagicMock(),
        notification_service=MagicMock(),
        history_limit=2,
    )

    now = datetime.now(timezone.utc).isoformat()
    analyzer._add_to_history({"patient_id": "p1", "analysis_timestamp": now})
    analyzer._add_to_history({"patient_id": "p1", "analysis_timestamp": now})
    analyzer._add_to_history({"patient_id": "p1", "analysis_timestamp": now})

    assert [entry["patient_id"] for entry in analyzer.get_history("p1")] == [
        "p1",
        "p1",
    ]


def test_clear_history_empties_cache():
    analyzer = PatientAnalyzer(
        fhir_connector=None,
        llm_engine=None,
        rag_fusion=None,
        s_lora_manager=_StubAdapterManager(),
        aot_reasoner=None,
        mlc_learning=None,
        patient_data_service=MagicMock(),
        risk_scoring_service=MagicMock(),
        recommendation_service=MagicMock(),
        alert_service=MagicMock(),
        notification_service=MagicMock(),
        history_limit=5,
    )

    analyzer.analysis_history = {"p1": [{"patient_id": "p1"}], "p2": [{"patient_id": "p2"}]}
    analyzer.clear_history()

    assert analyzer.total_history_count() == 0

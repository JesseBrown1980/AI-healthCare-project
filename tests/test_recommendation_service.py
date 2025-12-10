from unittest.mock import AsyncMock

import pytest

from backend.recommendation_service import RecommendationService


@pytest.mark.anyio
async def test_recommendations_use_llm_and_reasoning_components():
    llm_engine = AsyncMock()
    llm_engine.query_with_rag.return_value = {
        "answer": "Take action",
        "confidence": 0.9,
        "sources": ["guideline"],
    }

    rag_fusion = AsyncMock()
    rag_fusion.retrieve_relevant_knowledge.return_value = ["doc1"]

    aot_reasoner = AsyncMock()
    aot_reasoner.generate_reasoning_chain.return_value = {"steps": ["reason"]}

    mlc_learning = AsyncMock()
    mlc_learning.compose_for_task.return_value = ["component"]

    service = RecommendationService(llm_engine, rag_fusion, aot_reasoner, mlc_learning)

    patient_data = {"conditions": [{"code": "Condition"}]}
    alerts = [{"message": "alert", "severity": "high"}]

    recommendations = await service.generate_recommendations(
        patient_data=patient_data,
        summary={"age": 40},
        alerts=alerts,
        risk_scores={},
        adapters=["cardio"],
    )

    assert len(recommendations["clinical_recommendations"]) == 3
    assert recommendations["priority_actions"][0]["action"] == "alert"
    assert llm_engine.query_with_rag.await_count == 3
    mlc_learning.compose_for_task.assert_awaited_once()

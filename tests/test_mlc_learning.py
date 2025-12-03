import asyncio
from backend.mlc_learning import MLCLearning


def test_compose_for_task_and_feedback():
    mlc = MLCLearning(learning_rate=0.01)
    # Compose components for a known task
    composed = asyncio.run(mlc.compose_for_task("patient_analysis"))
    assert isinstance(composed, list)
    assert len(composed) >= 1

    # Simulate feedback processing
    update = asyncio.run(
        mlc.process_feedback(query_id="q-1", feedback_type="positive", corrected_text=None, components_used=["patient_summarization"])
    )
    assert "updated_components" in update

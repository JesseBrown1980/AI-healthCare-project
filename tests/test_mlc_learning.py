import asyncio

import pytest

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


def test_process_feedback_updates_rl_policy():
    mlc = MLCLearning(learning_rate=0.1)
    components = ["patient_summarization", "risk_detection"]

    state = mlc._build_state_signature(components)
    action = tuple(sorted(components))
    initial_q = mlc.rl_agent.get_q_values(state)[action]
    assert initial_q == pytest.approx(0.0)

    asyncio.run(
        mlc.process_feedback(
            query_id="user-1-q1", feedback_type="positive", corrected_text=None, components_used=components
        )
    )
    positive_q = mlc.rl_agent.get_q_values(state)[action]
    assert positive_q > initial_q

    state_after_positive = mlc._build_state_signature(components)
    asyncio.run(
        mlc.process_feedback(
            query_id="user-1-q2", feedback_type="negative", corrected_text=None, components_used=components
        )
    )
    state_after_negative = mlc._build_state_signature(components)
    negative_q = mlc.rl_agent.get_q_values(state_after_positive)[action]
    assert negative_q < positive_q

    stats = mlc.get_rl_stats()
    assert stats["cumulative_reward"] == pytest.approx(0.0)
    assert stats["last_update"] is not None

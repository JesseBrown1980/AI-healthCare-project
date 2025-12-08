import pytest

from backend.rl_agent import MLCRLAgent


def test_q_values_update_across_feedback_sequence():
    """Q-values should move toward observed rewards across transitions."""

    agent = MLCRLAgent(actions=["a", "b"], learning_rate=0.5, discount_factor=0.9)

    state = "s1"
    next_state = "s2"

    agent.update_policy(state=state, action="a", reward=1.0, next_state=next_state, done=False)
    first_q = agent.get_q_values(state)["a"]
    assert first_q == pytest.approx(0.5)

    agent.update_policy(state=next_state, action="b", reward=2.0, next_state="terminal", done=True)
    agent.update_policy(state=state, action="a", reward=0.0, next_state=next_state, done=False)

    updated_q = agent.get_q_values(state)["a"]

    assert updated_q == pytest.approx(0.7)
    assert updated_q > first_q

"""Simple reinforcement learning prototype for patient risk classification.

This experiment models risk triage as a tabular Q-learning problem over
synthetic patient features. It is intentionally minimal and meant to
illustrate how RL could refine risk policies alongside the MLCLearning
module.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


RISK_ACTIONS = ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]


@dataclass
class PatientState:
    """Simple patient-like state for the RL demo."""

    age_group: int  # 0: <40, 1: 40-65, 2: >65
    comorbidity_score: int  # 0-3 bucketed co-morbidity index
    vitals_flag: int  # 0: stable, 1: concerning

    def as_tuple(self) -> Tuple[int, int, int]:
        return (self.age_group, self.comorbidity_score, self.vitals_flag)


class PatientRiskEnv:
    """Minimal environment to simulate patient risk decisions.

    The environment is a single-step classification setup where each episode
    draws a synthetic patient profile. The agent selects a discrete risk
    class, and the reward is larger when the predicted risk matches the
    ground truth generated from the synthetic rule set.
    """

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self.current_state: PatientState | None = None

    def reset(self) -> PatientState:
        """Generate a new patient state for the episode."""
        age_group = self.random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
        comorbidity_score = self.random.choices([0, 1, 2, 3], weights=[0.35, 0.35, 0.2, 0.1])[0]
        vitals_flag = self.random.choices([0, 1], weights=[0.8, 0.2])[0]
        self.current_state = PatientState(age_group, comorbidity_score, vitals_flag)
        return self.current_state

    def true_risk(self, state: PatientState) -> str:
        """Map state to a synthetic ground-truth risk class."""
        score = (
            state.age_group * 0.6
            + state.comorbidity_score * 0.9
            + state.vitals_flag * 0.8
        )
        if score < 1.2:
            return "LOW_RISK"
        if score < 2.4:
            return "MEDIUM_RISK"
        return "HIGH_RISK"

    def step(self, action: str) -> Tuple[PatientState, float, bool]:
        """Run one step of the environment.

        Returns next_state (new patient), reward, and done flag.
        Each episode consists of a single decision; `done` is always True.
        """
        if self.current_state is None:
            raise RuntimeError("Environment must be reset before stepping.")

        true_label = self.true_risk(self.current_state)
        reward = 1.0 if action == true_label else -0.5

        next_state = self.reset()
        done = True
        return next_state, reward, done


def epsilon_greedy(q_values: Dict[Tuple[int, int, int], List[float]], state: PatientState, epsilon: float) -> str:
    """Pick an action using epsilon-greedy exploration."""
    if random.random() < epsilon:
        return random.choice(RISK_ACTIONS)

    state_key = state.as_tuple()
    if state_key not in q_values:
        q_values[state_key] = [0.0 for _ in RISK_ACTIONS]
    best_idx = max(range(len(RISK_ACTIONS)), key=lambda i: q_values[state_key][i])
    return RISK_ACTIONS[best_idx]


def train_q_learning(
    env: PatientRiskEnv,
    episodes: int = 500,
    alpha: float = 0.2,
    gamma: float = 0.9,
    epsilon: float = 0.2,
    epsilon_min: float = 0.05,
    epsilon_decay: float = 0.995,
) -> Dict[Tuple[int, int, int], List[float]]:
    """Run a simple tabular Q-learning loop over synthetic patients."""
    q_values: Dict[Tuple[int, int, int], List[float]] = {}

    state = env.reset()
    for _ in range(episodes):
        state_key = state.as_tuple()
        if state_key not in q_values:
            q_values[state_key] = [0.0 for _ in RISK_ACTIONS]

        action = epsilon_greedy(q_values, state, epsilon)
        action_idx = RISK_ACTIONS.index(action)

        next_state, reward, done = env.step(action)
        next_key = next_state.as_tuple()
        if next_key not in q_values:
            q_values[next_key] = [0.0 for _ in RISK_ACTIONS]

        future_estimate = 0.0 if done else max(q_values[next_key])
        td_target = reward + gamma * future_estimate
        td_error = td_target - q_values[state_key][action_idx]
        q_values[state_key][action_idx] += alpha * td_error

        state = next_state if not done else env.reset()
        epsilon = max(epsilon_min, epsilon * epsilon_decay)

    return q_values


def summarize_policy(q_values: Dict[Tuple[int, int, int], List[float]], limit: int = 10) -> List[str]:
    """Produce human-readable summaries of the learned policy."""
    summaries: List[str] = []
    sorted_states = sorted(q_values.items(), key=lambda item: -max(item[1]))
    for idx, (state_key, action_values) in enumerate(sorted_states[:limit]):
        best_action = RISK_ACTIONS[max(range(len(RISK_ACTIONS)), key=lambda i: action_values[i])]
        summaries.append(
            f"State {state_key} -> {best_action} | Q-values: "
            f"{[round(val, 2) for val in action_values]}"
        )
    return summaries


if __name__ == "__main__":
    random.seed(42)
    env = PatientRiskEnv(seed=42)
    learned_q = train_q_learning(env, episodes=800)

    print("RL patient risk demo")
    print("======================")
    print(f"Trained on {len(learned_q)} unique states")
    print("Sample learned policy snippets:")
    for line in summarize_policy(learned_q, limit=8):
        print(f" - {line}")

    # Example inference on a handcrafted patient
    example_state = PatientState(age_group=2, comorbidity_score=3, vitals_flag=1)
    action = epsilon_greedy(learned_q, example_state, epsilon=0.0)
    print("\nExample patient (high risk) ->", action)
    true_label = env.true_risk(example_state)
    print("True label:", true_label)

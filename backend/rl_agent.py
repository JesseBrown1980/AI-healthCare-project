"""
Reinforcement learning agent for Meta-Learning for Compositionality (MLC).

This module provides a lightweight tabular Q-learning implementation with an
interface that can later be swapped for a policy-gradient method such as PPO.
"""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from typing import Dict, Hashable, Iterable, List, Optional

logger = logging.getLogger(__name__)


class MLCRLAgent:
    """Simple tabular Q-learning agent for discrete action spaces.

    The agent maintains a Q-table mapping state-action pairs to expected
    cumulative rewards. It uses an epsilon-greedy strategy to balance
    exploration and exploitation when selecting actions.

    Notes:
        This class is intentionally lightweight so it can be replaced with a
        more advanced policy-gradient agent such as Proximal Policy
        Optimization (PPO) in the future. A PPO-based replacement would swap
        the tabular Q-table for neural network policies and value functions
        while preserving the ``select_action`` and ``update_policy`` interface.
    """

    def __init__(
        self,
        actions: Iterable[Hashable],
        learning_rate: float = 0.1,
        discount_factor: float = 0.99,
        epsilon: float = 0.1,
    ) -> None:
        """Initialize the reinforcement learning agent.

        Args:
            actions: Iterable of valid actions for the environment.
            learning_rate: Step size for Q-value updates.
            discount_factor: Future reward discount factor (gamma).
            epsilon: Exploration rate for epsilon-greedy policy.
        """
        self.actions: List[Hashable] = list(actions)
        if not self.actions:
            raise ValueError("MLCRLAgent requires at least one action")

        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon

        # Default to zero for unseen state-action pairs.
        self.q_table: Dict[Hashable, Dict[Hashable, float]] = defaultdict(
            lambda: {action: 0.0 for action in self.actions}
        )

        logger.info("Initialized MLCRLAgent with %d actions", len(self.actions))

    def select_action(self, state: Hashable) -> Hashable:
        """Choose an action using an epsilon-greedy policy.

        Args:
            state: Current environment state (hashable for dictionary use).

        Returns:
            Selected action.
        """
        if random.random() < self.epsilon:
            action = random.choice(self.actions)
            logger.debug("Selected exploratory action '%s' for state '%s'", action, state)
            return action

        state_actions = self.q_table[state]
        max_value = max(state_actions.values())
        best_actions = [act for act, value in state_actions.items() if value == max_value]
        action = random.choice(best_actions)
        logger.debug("Selected greedy action '%s' for state '%s'", action, state)
        return action

    def update_policy(
        self,
        state: Hashable,
        action: Hashable,
        reward: float,
        next_state: Optional[Hashable] = None,
        done: bool = False,
    ) -> None:
        """Update Q-values based on observed transition.

        Args:
            state: Previous state.
            action: Action taken in the previous state.
            reward: Immediate reward received.
            next_state: State reached after the action.
            done: Whether the episode terminated after the transition.

        Notes:
            When replacing this with PPO, the update would optimize clipped
            surrogate objectives using collected trajectories rather than
            tabular Q-value updates. The public method signature can remain the
            same to minimize integration changes.
        """
        if action not in self.q_table[state]:
            # Allow actions to be extended dynamically.
            self.q_table[state][action] = 0.0

        current_q = self.q_table[state][action]
        next_max = 0.0

        if not done and next_state is not None:
            next_actions = self.q_table[next_state]
            next_max = max(next_actions.values())

        updated_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max - current_q
        )
        self.q_table[state][action] = updated_q

        logger.debug(
            "Updated Q-value for state '%s', action '%s': %.4f -> %.4f",
            state,
            action,
            current_q,
            updated_q,
        )

    def get_q_values(self, state: Hashable) -> Dict[Hashable, float]:
        """Return Q-values for a given state."""
        return dict(self.q_table[state])

    def set_epsilon(self, epsilon: float) -> None:
        """Update the exploration rate (epsilon)."""
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")
        self.epsilon = epsilon


__all__ = ["MLCRLAgent"]

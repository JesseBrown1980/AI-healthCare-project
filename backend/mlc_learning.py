"""
Meta-Learning for Compositionality (MLC) Module
Enables continuous learning and adaptation from user feedback
Implements online learning strategies for personalization
"""

import logging
from itertools import combinations
from typing import Dict, List, Optional, Any, Hashable
import json
from datetime import datetime
from collections import defaultdict

from backend.rl_agent import MLCRLAgent

logger = logging.getLogger(__name__)


class MLCLearning:
    """
    Meta-Learning for Compositionality system
    Continuously adapts and learns from feedback and corrections
    Decomposes complex tasks into learned components
    """
    
    def __init__(self, learning_rate: float = 0.001, feedback_history_path: str = "./data/feedback"):
        """
        Initialize MLC Learning system
        
        Args:
            learning_rate: Learning rate for model updates
            feedback_history_path: Path to store feedback history
        """
        self.learning_rate = learning_rate
        self.feedback_history_path = feedback_history_path
        self.feedback_history: List[Dict] = []
        self.learned_components: Dict[str, Dict] = {}
        self.query_outcomes: Dict[str, List[Dict]] = defaultdict(list)
        self.personalization_profiles: Dict[str, Dict] = {}
        self._rl_metrics = {
            "cumulative_reward": 0.0,
            "last_update": None,
        }

        self._initialize_components()
        self._initialize_rl_agent()

        # RL-driven policy priors can be injected here to bias default risk thresholds
        # or component selection before any user feedback arrives.
        self._rl_policy_prior: Optional[Any] = None

        logger.info("MLC Learning system initialized")

    async def record_feedback(self, patient_id: str, analysis: Dict[str, Any]) -> None:
        """Persist analysis output for later learning cycles."""

        feedback_snapshot = {
            "patient_id": patient_id,
            "query_id": analysis.get("query_id"),
            "feedback_type": "analysis_snapshot",
            "components_used": analysis.get("components_used", []),
            "analysis_timestamp": analysis.get("analysis_timestamp"),
            "status": analysis.get("status"),
            "alert_count": analysis.get("alert_count"),
            "overall_risk_score": analysis.get("overall_risk_score"),
            "highest_alert_severity": analysis.get("highest_alert_severity"),
            "recorded_at": datetime.now().isoformat(),
        }

        self.feedback_history.append(feedback_snapshot)
        logger.info(
            "Recorded analysis feedback sample | patient_id=%s | total_samples=%d",
            patient_id,
            len(self.feedback_history),
        )

    def _initialize_components(self):
        """Initialize basic learned components"""
        self.learned_components = {
            "patient_summarization": {
                "component_id": "comp_001",
                "type": "summarization",
                "description": "Summarize patient history",
                "performance": 0.85,
                "usage_count": 0
            },
            "risk_detection": {
                "component_id": "comp_002",
                "type": "risk_analysis",
                "description": "Identify clinical risks",
                "performance": 0.88,
                "usage_count": 0
            },
            "medication_review": {
                "component_id": "comp_003",
                "type": "medication_analysis",
                "description": "Analyze medication interactions",
                "performance": 0.90,
                "usage_count": 0
            },
            "guideline_matching": {
                "component_id": "comp_004",
                "type": "guideline_alignment",
                "description": "Match patient to clinical guidelines",
                "performance": 0.87,
                "usage_count": 0
            },
            "question_decomposition": {
                "component_id": "comp_005",
                "type": "task_decomposition",
                "description": "Break complex queries into sub-tasks",
                "performance": 0.82,
                "usage_count": 0
            }
        }
    
    async def process_feedback(
        self,
        query_id: str,
        feedback_type: str,  # "positive", "negative", "correction"
        corrected_text: Optional[str] = None,
        components_used: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process user feedback and update learning models
        
        Args:
            query_id: ID of original query
            feedback_type: Type of feedback (positive, negative, correction)
            corrected_text: Corrected version of response
            components_used: Components involved in original response
            
        Returns:
            Update summary
        """
        logger.info(f"Processing {feedback_type} feedback for query {query_id}")

        try:
            feedback_record = {
                "query_id": query_id,
                "feedback_type": feedback_type,
                "corrected_text": corrected_text,
                "components_used": components_used or [],
                "timestamp": datetime.now().isoformat(),
                "processed": False
            }

            self.feedback_history.append(feedback_record)

            components_used = components_used or []
            state = self._build_state_signature(components_used)
            action = tuple(sorted(components_used))
            reward = self._compute_reward(feedback_type)
            self._rl_metrics["cumulative_reward"] += reward
            self._rl_metrics["last_update"] = datetime.now().isoformat()
            logger.info(
                "Computed reward %.2f for feedback '%s' on components %s",
                reward,
                feedback_type,
                action or "none",
            )

            # Update component performance based on feedback
            update_summary = await self._update_component_performance(
                components_used,
                feedback_type
            )

            next_state = self._build_state_signature(components_used)
            self.rl_agent.update_policy(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=False,
            )
            logger.info(
                "RL update applied | state=%s | action=%s | reward=%.2f | next_state=%s",
                state,
                action,
                reward,
                next_state,
            )

            # Generate personalization insights
            if components_used:
                self.query_outcomes[components_used[0]].append({
                    "feedback_type": feedback_type,
                    "timestamp": datetime.now().isoformat()
                })
            
            feedback_record["processed"] = True
            
            return update_summary
        
        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}")
            raise
    
    async def _update_component_performance(
        self,
        components: List[str],
        feedback_type: str
    ) -> Dict[str, Any]:
        """
        Update performance metrics of involved components
        
        Args:
            components: Components involved in the response
            feedback_type: Type of feedback
            
        Returns:
            Update summary with new performance metrics
        """
        update_summary = {
            "updated_components": [],
            "performance_changes": {}
        }
        
        # Determine adjustment factor based on feedback
        if feedback_type == "positive":
            adjustment = 0.02  # +2% boost
        elif feedback_type == "negative":
            adjustment = -0.03  # -3% penalty
        else:  # "correction"
            adjustment = -0.01  # -1% penalty
        
        for component_id in components:
            if component_id in self.learned_components:
                component = self.learned_components[component_id]
                old_performance = component["performance"]
                
                # Update performance with learning rate
                new_performance = old_performance + (adjustment * self.learning_rate)
                new_performance = max(0.1, min(0.99, new_performance))  # Clamp between 0.1 and 0.99
                
                component["performance"] = new_performance
                component["usage_count"] += 1
                
                update_summary["updated_components"].append(component_id)
                update_summary["performance_changes"][component_id] = {
                    "old": round(old_performance, 4),
                    "new": round(new_performance, 4),
                    "change": round(new_performance - old_performance, 4)
                }
                
                logger.info(f"Updated {component_id}: {old_performance:.4f} → {new_performance:.4f}")
        
        return update_summary
    
    async def compose_for_task(self, task_type: str) -> List[str]:
        """
        Suggest optimal component composition for a task type
        
        Args:
            task_type: Type of clinical task
            
        Returns:
            Ordered list of component IDs to use
        """
        logger.info(f"Composing components for task: {task_type}")
        
        # Task-specific component recipes
        recipes = {
            "patient_analysis": [
                "patient_summarization",
                "risk_detection",
                "medication_review",
                "guideline_matching"
            ],
            "treatment_recommendation": [
                "guideline_matching",
                "medication_review",
                "risk_detection"
            ],
            "diagnostic_support": [
                "question_decomposition",
                "patient_summarization",
                "guideline_matching"
            ],
            "medication_optimization": [
                "medication_review",
                "guideline_matching",
                "risk_detection"
            ]
        }
        
        components = recipes.get(task_type, list(self.learned_components.keys()))
        
        # Sort by performance (best first)
        components_with_scores = [
            (comp, self.learned_components[comp].get("performance", 0.8))
            for comp in components
            if comp in self.learned_components
        ]
        components_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        composed = [comp for comp, _ in components_with_scores]
        logger.info(f"Composed components: {composed}")
        
        return composed
    
    async def personalize_for_user(
        self,
        user_id: str,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create personalized learning profile for user
        
        Args:
            user_id: Identifier for user (clinician, hospital, etc.)
            preferences: User preferences for response style, detail level, etc.
            
        Returns:
            Personalization profile
        """
        if user_id not in self.personalization_profiles:
            self.personalization_profiles[user_id] = {
                "user_id": user_id,
                "preferences": preferences or {},
                "feedback_count": 0,
                "correction_rate": 0,
                "preferred_components": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        profile = self.personalization_profiles[user_id]
        
        # Update profile based on user preferences
        if preferences:
            profile["preferences"].update(preferences)
        
        # Calculate user-specific component preferences based on feedback
        profile["feedback_count"] = sum(
            1 for f in self.feedback_history 
            if f.get("query_id", "").startswith(user_id)
        )
        
        # Identify preferred components (those with positive feedback)
        component_feedback = defaultdict(lambda: {"positive": 0, "total": 0})
        for feedback in self.feedback_history:
            for comp in feedback.get("components_used", []):
                component_feedback[comp]["total"] += 1
                if feedback["feedback_type"] == "positive":
                    component_feedback[comp]["positive"] += 1
        
        profile["preferred_components"] = [
            comp for comp, stats in component_feedback.items()
            if stats["total"] > 0 and stats["positive"] / stats["total"] > 0.7
        ]
        
        profile["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"Personalization profile created for user: {user_id}")
        return profile
    
    async def get_learned_insights(self) -> Dict[str, Any]:
        """Get insights from accumulated learning data"""
        insights = {
            "total_feedback_samples": len(self.feedback_history),
            "component_performance": {},
            "task_performance": {},
            "improvement_rate": 0,
            "most_used_components": [],
            "users_profiles": len(self.personalization_profiles)
        }
        
        # Component-level insights
        for comp_id, component in self.learned_components.items():
            insights["component_performance"][comp_id] = {
                "performance": round(component["performance"], 4),
                "usage_count": component["usage_count"],
                "improvement_potential": "high" if component["performance"] < 0.85 else "low"
            }
        
        # Most used components
        sorted_components = sorted(
            self.learned_components.items(),
            key=lambda x: x[1]["usage_count"],
            reverse=True
        )
        insights["most_used_components"] = [comp[0] for comp in sorted_components[:3]]
        
        # Calculate overall improvement rate
        if len(self.feedback_history) > 10:
            recent = self.feedback_history[-10:]
            positive_recent = sum(1 for f in recent if f["feedback_type"] == "positive")
            insights["improvement_rate"] = positive_recent / 10
        
        return insights

    def get_stats(self) -> Dict:
        """Get MLC system statistics"""
        return {
            "total_feedback_samples": len(self.feedback_history),
            "learned_components": len(self.learned_components),
            "personalized_users": len(self.personalization_profiles),
            "average_component_performance": sum(
                c.get("performance", 0.8) for c in self.learned_components.values()
            ) / max(len(self.learned_components), 1),
            "learning_rate": self.learning_rate,
            "rl": self.get_rl_stats(),
        }

    def get_rl_stats(self) -> Dict[str, Any]:
        """Return reinforcement learning telemetry for monitoring."""
        return {
            "cumulative_reward": round(self._rl_metrics.get("cumulative_reward", 0.0), 4),
            "exploration_rate": getattr(self.rl_agent, "epsilon", None),
            "last_update": self._rl_metrics.get("last_update"),
        }

    def update_policy_from_rl(self, policy: Any) -> None:
        """Optional hook to ingest an external RL policy into MLC settings.

        Example usage could map risk-class action values into default thresholds
        for `risk_detection` or reprioritize component selection for high-risk
        patients before feedback is available.
        """
        self._rl_policy_prior = policy
        logger.info("Updated MLC policy prior from RL output")

    def _initialize_rl_agent(self) -> None:
        """Initialize the reinforcement learning agent for component composition."""
        # Seed the action space with likely component compositions so the agent can
        # immediately learn policies for realistic multi-component plans.
        base_actions = self._generate_action_space()
        self.rl_agent = MLCRLAgent(actions=base_actions, learning_rate=0.1, discount_factor=0.9)
        logger.info(
            "Initialized RL agent with %d base actions for %d components",
            len(base_actions),
            len(self.learned_components),
        )

    def _generate_action_space(self) -> List[Hashable]:
        """Create a compact action space of component compositions.

        The space includes single components and small combinations (up to 3 items)
        to balance coverage with tractability.
        """
        component_ids = sorted(self.learned_components.keys())
        actions: List[Hashable] = []

        # Single component choices
        actions.extend((comp,) for comp in component_ids)

        # Common combinations used during composition
        for r in range(2, min(3, len(component_ids)) + 1):
            actions.extend(combinations(component_ids, r))

        return actions

    def _build_state_signature(self, components: List[str]) -> Hashable:
        """Create a hashable state representation for RL updates.

        The state captures which components were involved and their average
        performance prior to an update to provide context for the reward signal.
        """
        if not components:
            return ("no_components", 0.0)

        sorted_components = tuple(sorted(components))
        performances: List[float] = [
            round(self.learned_components.get(comp, {}).get("performance", 0.0), 4)
            for comp in sorted_components
        ]
        avg_performance = sum(performances) / max(len(performances), 1)
        return (
            sorted_components,
            tuple(zip(sorted_components, performances)),
            round(avg_performance, 4),
        )

    @staticmethod
    def _compute_reward(feedback_type: str) -> float:
        """Map feedback types to reinforcement learning rewards."""
        reward_mapping = {
            "positive": 1.0,
            "negative": -1.0,
            "correction": -0.5,
        }
        return reward_mapping.get(feedback_type, 0.0)

import logging
import json
from typing import Dict, Any, Optional
from backend.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manager for autonomous agents associated with system operations.
    Currently focuses on reviewing outgoing notifications.
    """

    def __init__(self, llm_engine: LLMEngine):
        self.llm_engine = llm_engine

    async def review_notification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review a notification payload using the LLM.
        Returns a decision dictionary: {"action": "APPROVE" | "REJECT", "reason": "..."}
        """
        if not self.llm_engine:
            logger.warning("AgentManager has no LLMEngine, defaulting to APPROVE")
            return {"action": "APPROVE", "reason": "No LLM Engine available"}

        # Extract relevant info for review
        content_summary = self._summarize_payload(payload)
        
        system_prompt = """You are a notification review agent for a healthcare system.
Your job is to prevent sensitive PHI (Protected Health Information) leakage or inappropriate messages.
Analyze the notification content.
If the content contains sensitive raw patient data (like specific names combined with conditions) that typically should not be in a standard alert without redaction, or if it looks like a system error trace, REJECT it.
Otherwise, APPROVE it.
Respond with a JSON object specifically: {"action": "APPROVE", "reason": "looks safe"} or {"action": "REJECT", "reason": "contains raw PHI"}."""

        user_prompt = f"Notification Content:\n{content_summary}\n\nReview Decision:"

        try:
            response = await self.llm_engine.query_generic(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0  # Deterministic for policy enforcement
            )
            
            answer = response.get("content", "").strip()
            # Attempt to parse JSON from the response
            # LLMs might be chatty, so we'll look for the JSON part if needed, 
            # but for now let's hope the prompt instruction is enough.
            # A robust implementation would use an output parser or regex.
            
            # Simple cleanup to handle potential markdown code blocks
            answer = answer.replace("```json", "").replace("```", "").strip()
            
            decision = json.loads(answer)
            # Normalize keys
            if "action" not in decision:
                # Fallback if structure is wrong
                logger.warning(f"AgentManager received malformed JSON: {answer}")
                if "REJECT" in answer.upper():
                    return {"action": "REJECT", "reason": "LLM output implied rejection but format was wrong"}
                return {"action": "APPROVE", "reason": "LLM output format unclear, defaulting open"}
                
            return decision

        except json.JSONDecodeError:
            logger.error(f"AgentManager failed to parse LLM response: {answer}")
            return {"action": "APPROVE", "reason": "JSON parse error, fail-safe open"}
        except Exception as e:
            logger.error(f"AgentManager review failed: {e}")
            return {"action": "APPROVE", "reason": "Review exception, fail-safe open"}

    def _summarize_payload(self, payload: Dict[str, Any]) -> str:
        """Create a string summary of the payload for the LLM."""
        # We process the payload to be text-friendly
        # Sensitive fields might be deep, but we assume the 'alerts' list or 'body' is the main concern.
        
        summary = []
        if "patient_id" in payload:
            summary.append(f"Patient ID: {payload['patient_id']}")
        
        if "alerts" in payload:
            alerts = payload["alerts"]
            if isinstance(alerts, list):
                for a in alerts:
                    summary.append(f"Alert: {a.get('message', '')} (Severity: {a.get('severity', '')})")
            else:
                summary.append(f"Alerts: {str(alerts)}")
        
        if "risk_scores" in payload:
             summary.append(f"Risk Scores: {payload['risk_scores']}")

        if "body" in payload:
            summary.append(f"Body: {payload['body']}")
            
        return "\n".join(summary)

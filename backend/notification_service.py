import asyncio
import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class NotificationService:
    """Service for dispatching critical alert notifications."""

    def __init__(self, notifier, notifications_enabled: bool = False):
        self.notifier = notifier
        self.notifications_enabled = notifications_enabled

    async def notify_if_needed(
        self,
        analysis_result: Dict[str, Any],
        correlation_id: str,
        notify: bool,
    ) -> None:
        """Send notifications when configured and critical alerts exist."""

        if not (notify and self.notifications_enabled and self.notifier):
            return

        alerts = analysis_result.get("alerts") or []
        has_critical_alert = any(
            str(alert.get("severity", "")).lower() == "critical" for alert in alerts
        )

        if not has_critical_alert:
            return

        alert_count = analysis_result.get("alert_count")
        if alert_count is None:
            alert_count = len(alerts) if isinstance(alerts, list) else 0

        risk_scores = analysis_result.get("risk_scores") or {}
        top_risk_name: Optional[str] = None
        top_risk_value: Optional[float] = None
        for risk_name, risk_value in risk_scores.items():
            if isinstance(risk_value, (int, float)) and (
                top_risk_value is None or risk_value > top_risk_value
            ):
                top_risk_name = risk_name
                top_risk_value = risk_value

        risk_summary = (
            f"{top_risk_name.replace('_', ' ')}: {top_risk_value:.2f}"
            if top_risk_name is not None and top_risk_value is not None
            else ""
        )

        push_title = f"Patient {analysis_result.get('patient_id', 'unknown')}: {alert_count} alerts"
        push_body = f"Alerts: {risk_summary}" if risk_summary else "Alerts available"

        patient_id = analysis_result.get("patient_id", "unknown")
        deep_link = f"healthcareai://patients/{patient_id}/analysis"
        notification_payload = {
            "patient_id": patient_id,
            "alert_count": alert_count,
            "risk_scores": risk_scores,
            "top_risk": {"name": top_risk_name, "value": top_risk_value}
            if top_risk_name is not None and top_risk_value is not None
            else None,
            "deep_link": deep_link,
            "correlation_id": correlation_id,
            "analysis": analysis_result,
            "alerts": alerts,
            "title": push_title,
            "body": push_body,
            "risk_summary": risk_summary,
        }

        try:
            tasks = [self.notifier.notify(notification_payload, correlation_id=correlation_id)]

            if hasattr(self.notifier, "send_push_notification"):
                tasks.append(
                    self.notifier.send_push_notification(
                        title=push_title,
                        body=push_body,
                        deep_link=deep_link,
                        correlation_id=correlation_id,
                    )
                )

            await asyncio.gather(*tasks)
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning("Failed to send critical alert notification: %s", exc)

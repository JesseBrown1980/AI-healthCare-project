from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class AlertService:
    """Service responsible for identifying alerts and severity."""

    async def identify_alerts(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify clinical alerts and red flags."""

        alerts: List[Dict[str, Any]] = []

        # Check for high-risk conditions
        critical_conditions = ["mi", "stroke", "sepsis", "acute_mi", "pulmonary_embolism"]
        for condition in patient_data.get("conditions", []):
            code = condition.get("code", "").lower()
            if any(risk in code for risk in critical_conditions):
                alerts.append(
                    {
                        "severity": "critical",
                        "type": "condition",
                        "message": f"Critical condition identified: {condition.get('code')}",
                        "recommendation": "Immediate clinical review required",
                    }
                )

        # Check lab values
        for obs in patient_data.get("observations", []):
            value = obs.get("value")
            interp = obs.get("interpretation", "").lower()

            if "high" in interp or "critical" in interp:
                alerts.append(
                    {
                        "severity": "high",
                        "type": "lab",
                        "message": f"Abnormal lab value: {obs.get('code')} = {value} {obs.get('unit')}",
                        "recommendation": f"Review {obs.get('code')} and consider intervention",
                    }
                )

        return alerts

    @staticmethod
    def highest_alert_severity(alerts: List[Dict[str, Any]]) -> str:
        """Determine the most severe alert level present."""

        severity_order = ["none", "low", "medium", "high", "critical"]
        highest_index = 0

        for alert in alerts:
            severity = str(alert.get("severity", "none")).lower()
            try:
                highest_index = max(highest_index, severity_order.index(severity))
            except ValueError:
                continue

        return severity_order[highest_index]

    def collect_recent_alerts(
        self,
        history: List[Dict[str, Any]],
        limit: int,
        patient_id: Optional[str] = None,
        roster_lookup: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate recent critical and high-severity alerts from analysis history.
        """
        alerts: List[Dict[str, Any]] = []
        
        # History is expected to be provided by the caller (HistoryService.get_history())

        for analysis in reversed(history):
            timestamp = analysis.get("analysis_timestamp") or analysis.get("timestamp")
            analysis_patient_id = analysis.get("patient_id")

            patient_name = (
                (analysis.get("summary") or {}).get("patient_name")
                or (analysis.get("patient_data") or {})
                .get("patient", {})
                .get("name")
                or (roster_lookup.get(analysis_patient_id) if roster_lookup else None)
                or analysis_patient_id
            )

            for idx, alert in enumerate(analysis.get("alerts") or []):
                normalized = alert if isinstance(alert, dict) else {"summary": str(alert)}
                severity = (normalized.get("severity") or "").lower()

                if severity not in {"critical", "high"}:
                    continue

                alerts.append(
                    {
                        "id": normalized.get("id")
                        or f"{analysis_patient_id}-{idx}-{timestamp or len(alerts)}",
                        "patient_id": analysis_patient_id,
                        "patient_name": patient_name,
                        "title": normalized.get("title")
                        or normalized.get("type")
                        or "Clinical Alert",
                        "summary": normalized.get("summary")
                        or normalized.get("description")
                        or normalized.get("message")
                        or str(alert),
                        "severity": normalized.get("severity") or "critical",
                        "timestamp": normalized.get("timestamp")
                        or normalized.get("created_at")
                        or timestamp
                        or datetime.now(timezone.utc).isoformat(),
                    }
                )

                if len(alerts) >= limit:
                    break

            if len(alerts) >= limit:
                break

        return sorted(alerts, key=lambda a: a.get("timestamp", ""), reverse=True)[:limit]

from typing import Any, Dict, List


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

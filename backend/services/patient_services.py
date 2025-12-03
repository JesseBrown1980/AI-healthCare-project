"""Patient-centric services that isolate domain logic for analysis orchestration."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class PatientDataService:
    fhir_connector: Any

    async def fetch_patient(self, patient_id: str) -> Dict[str, Any]:
        return await self.fhir_connector.get_patient(patient_id)


class SummaryService:
    @staticmethod
    def _calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
        if not birth_date_str:
            return None

        try:
            birth_date = date.fromisoformat(birth_date_str[:10])
        except ValueError:
            return None

        today = date.today()
        return (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

    async def generate_summary(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        patient_info = patient_data.get("patient", {})
        age = self._calculate_age(patient_info.get("birthDate"))

        return {
            "patient_name": patient_info.get("name"),
            "age_gender": f"{age if age is not None else 'Unknown'} / {patient_info.get('gender', 'Unknown')}",
            "age": age,
            "active_conditions_count": len(patient_data.get("conditions", [])),
            "current_medications_count": len(patient_data.get("medications", [])),
            "recent_visits": len(patient_data.get("encounters", [])),
            "key_conditions": [c.get("code") for c in patient_data.get("conditions", [])[:3]],
            "key_medications": [m.get("medication") for m in patient_data.get("medications", [])[:3]],
            "narrative_summary": f"Patient {patient_info.get('name')} (age {age if age is not None else 'Unknown'}) has {len(patient_data.get('conditions', []))} active conditions and is on {len(patient_data.get('medications', []))} medications.",
        }


class AlertService:
    async def identify_alerts(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        critical_conditions = ["MI", "stroke", "sepsis", "acute_MI", "pulmonary_embolism"]
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

        meds = [m.get("medication", "").lower() for m in patient_data.get("medications", [])]
        known_interactions = [
            ("warfarin", "nsaid"),
            ("lisinopril", "potassium"),
            ("metformin", "dye"),
        ]

        for drug1, drug2 in known_interactions:
            if any(drug1 in m for m in meds) and any(drug2 in m for m in meds):
                alerts.append(
                    {
                        "severity": "medium",
                        "type": "drug_interaction",
                        "message": f"Potential interaction: {drug1} + {drug2}",
                        "recommendation": "Consider alternative or adjust dosing",
                    }
                )

        return alerts

    @staticmethod
    def highest_alert_severity(alerts: List[Dict[str, Any]]) -> str:
        severity_order = ["none", "low", "medium", "high", "critical"]
        highest_index = 0

        for alert in alerts:
            severity = str(alert.get("severity", "none")).lower()
            try:
                highest_index = max(highest_index, severity_order.index(severity))
            except ValueError:
                continue

        return severity_order[highest_index]


class RiskScoringService:
    @staticmethod
    def derive_overall_risk_score(risk_scores: Dict[str, Any]) -> Optional[float]:
        numeric_scores = [
            value
            for value in risk_scores.values()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]

        if not numeric_scores:
            return None

        return max(numeric_scores)

    async def calculate_risk_scores(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        risk_scores: Dict[str, Any] = {}

        def _normalize(score: float) -> float:
            return max(0.0, min(1.0, score))

        patient_info = patient_data.get("patient", {})
        age = SummaryService._calculate_age(patient_info.get("birthDate"))
        age_factor = _normalize((age or 0) / 100)

        conditions = [c.get("code", "").lower() for c in patient_data.get("conditions", [])]
        medication_count = len(patient_data.get("medications", []))
        polypharmacy = medication_count >= 10
        med_burden_factor = min(0.2, medication_count * 0.02)

        cv_risk = 0.15 + (0.35 * age_factor)
        if any("hypertension" in c for c in conditions):
            cv_risk += 0.2
        if any("diabetes" in c for c in conditions):
            cv_risk += 0.2
        if any("smoke" in c for c in conditions):
            cv_risk += 0.2
        cv_risk += med_burden_factor
        if polypharmacy:
            cv_risk += 0.1

        risk_scores["cardiovascular_risk"] = _normalize(cv_risk)

        recent_encounters = len(
            [
                e
                for e in patient_data.get("encounters", [])
                if e.get("status") in ["finished", "completed"]
            ]
        )
        readmit_risk = 0.12 + (0.25 * age_factor)
        readmit_risk += min(0.25, recent_encounters * 0.05)
        readmit_risk += min(0.25, medication_count * 0.02)
        if polypharmacy:
            readmit_risk += 0.1

        risk_scores["readmission_risk"] = _normalize(readmit_risk)

        adherence_risk = 0.1 + (0.3 * age_factor) + min(0.35, medication_count * 0.03)
        if polypharmacy:
            adherence_risk += 0.15

        risk_scores["medication_non_adherence_risk"] = _normalize(adherence_risk)
        risk_scores["polypharmacy"] = polypharmacy
        risk_scores["polypharmacy_risk"] = polypharmacy

        return risk_scores


class MedicationReviewService:
    async def review_medications(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        review = {
            "total_medications": len(patient_data.get("medications", [])),
            "medications": [],
            "potential_issues": [],
            "deprescribing_candidates": [],
        }

        for med in patient_data.get("medications", []):
            med_review = {
                "name": med.get("medication"),
                "status": med.get("status"),
                "indication": med.get("medication"),
                "appropriateness": "appropriate",
            }
            review["medications"].append(med_review)

        if review["total_medications"] >= 10:
            review["potential_issues"].append(
                "Polypharmacy (>=10 medications) - review for duplication"
            )
            review["deprescribing_candidates"] = [
                m.get("medication") for m in patient_data.get("medications", [])[:2]
            ]

        return review


class AlertNotificationService:
    def __init__(self, notifier: Any, notifications_enabled: bool = False) -> None:
        self.notifier = notifier
        self.notifications_enabled = notifications_enabled

    async def notify_if_needed(
        self,
        analysis_result: Dict[str, Any],
        notify: bool,
        correlation_id: str,
    ) -> None:
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
        top_risk_name = None
        top_risk_value = None
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
            tasks: Sequence[Any] = [
                self.notifier.notify(notification_payload, correlation_id=correlation_id)
            ]

            if hasattr(self.notifier, "send_push_notification"):
                tasks = list(tasks) + [
                    self.notifier.send_push_notification(
                        title=push_title,
                        body=push_body,
                        deep_link=deep_link,
                        correlation_id=correlation_id,
                    )
                ]

            await asyncio.gather(*tasks)
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning("Failed to send critical alert notification: %s", exc)

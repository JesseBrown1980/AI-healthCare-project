"""Audit service for recording FHIR AuditEvent and Provenance resources."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.security import TokenContext


class AuditService:
    """Construct and submit FHIR audit artifacts for key operations."""

    def __init__(self, fhir_connector) -> None:
        self.fhir_connector = fhir_connector
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def new_correlation_id() -> str:
        """Generate a correlation identifier for related audit entries."""

        return uuid.uuid4().hex

    def _build_agent(self, user_context: Optional[TokenContext]) -> Dict:
        identifier = (user_context.subject if user_context else None) or "unknown"
        scopes = sorted(user_context.scopes) if user_context else []

        return {
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/extra-security-role-type",
                "code": "human",
                "display": "Human user",
            },
            "who": {"identifier": {"value": identifier}},
            "requestor": True,
            "policy": scopes,
        }

    def build_audit_event(
        self,
        *,
        action: str,
        patient_id: Optional[str],
        user_context: Optional[TokenContext],
        correlation_id: str,
        outcome: str,
        outcome_desc: str,
        event_type: str,
    ) -> Dict:
        recorded = datetime.now(timezone.utc).isoformat()

        audit_event = {
            "resourceType": "AuditEvent",
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
                "code": "rest",
                "display": "Restful Operation",
            },
            "subtype": [
                {
                    "system": "http://hl7.org/fhir/restful-interaction",
                    "code": event_type,
                    "display": event_type.replace("-", " ").title(),
                }
            ],
            "action": action,
            "recorded": recorded,
            "outcome": outcome,
            "outcomeDesc": outcome_desc,
            "agent": [self._build_agent(user_context)],
            "source": {
                "observer": {"identifier": {"value": "HealthcareAIAssistant"}},
                "type": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/security-source-type",
                        "code": "4",
                        "display": "Application Server",
                    }
                ],
            },
        }

        if patient_id:
            audit_event["entity"] = [
                {
                    "what": {"reference": f"Patient/{patient_id}"},
                    "detail": [
                        {
                            "type": "correlation-id",
                            "valueString": correlation_id,
                        }
                    ],
                }
            ]
        else:
            audit_event["entity"] = [
                {
                    "detail": [
                        {
                            "type": "correlation-id",
                            "valueString": correlation_id,
                        }
                    ]
                }
            ]

        return audit_event

    def build_provenance(
        self,
        *,
        patient_id: str,
        user_context: Optional[TokenContext],
        correlation_id: str,
        activity_code: str,
    ) -> Dict:
        recorded = datetime.now(timezone.utc).isoformat()
        agent_identifier = (user_context.subject if user_context else None) or "unknown"

        return {
            "resourceType": "Provenance",
            "recorded": recorded,
            "activity": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                        "code": activity_code,
                        "display": activity_code.replace("-", " ").title(),
                    }
                ]
            },
            "target": [{"reference": f"Patient/{patient_id}"}],
            "agent": [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                "code": "author",
                                "display": "Author",
                            }
                        ]
                    },
                    "who": {"identifier": {"value": agent_identifier}},
                    "requestor": True,
                }
            ],
            "signature": [
                {
                    "type": [
                        {
                            "system": "urn:iso-astm:E1762-95:2013",
                            "code": "1.2.840.10065.1.12.1.1",
                            "display": "Author's Signature",
                        }
                    ],
                    "when": recorded,
                    "who": {"identifier": {"value": agent_identifier}},
                    "data": correlation_id,
                }
            ],
        }

    async def record_event(
        self,
        *,
        action: str,
        patient_id: Optional[str],
        user_context: Optional[TokenContext],
        correlation_id: str,
        outcome: str,
        outcome_desc: str,
        event_type: str,
        include_provenance: bool = False,
        provenance_activity: str = ""
    ) -> None:
        """Create and submit AuditEvent (and optional Provenance) resources."""

        if not self.fhir_connector:
            self.logger.warning("FHIR connector unavailable; skipping audit submission")
            return

        audit_event = self.build_audit_event(
            action=action,
            patient_id=patient_id,
            user_context=user_context,
            correlation_id=correlation_id,
            outcome=outcome,
            outcome_desc=outcome_desc,
            event_type=event_type,
        )

        provenance: Optional[Dict] = None
        if include_provenance and patient_id:
            provenance = self.build_provenance(
                patient_id=patient_id,
                user_context=user_context,
                correlation_id=correlation_id,
                activity_code=provenance_activity or event_type,
            )

        try:
            async with self.fhir_connector.request_context(
                user_context.access_token if user_context else "",
                user_context.scopes if user_context else set(),
                user_context.patient if user_context else None,
                user_context.subject if user_context else None,
            ):
                await self.fhir_connector.submit_resource(
                    "AuditEvent", audit_event, correlation_context=correlation_id
                )
                if provenance:
                    await self.fhir_connector.submit_resource(
                        "Provenance", provenance, correlation_context=correlation_id
                    )
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.warning("Unable to submit audit artifacts: %s", exc)

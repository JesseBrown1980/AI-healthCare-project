import asyncio
import anyio
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

import httpx

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    """Protocol for notification channels."""

    async def notify(
        self, payload: Dict[str, Any], correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        ...


class WebhookNotifier:
    """Send notifications to a generic webhook."""

    def __init__(self, callback_url: str) -> None:
        self.callback_url = callback_url

    async def notify(
        self, payload: Dict[str, Any], correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.callback_url, json=payload, headers=headers)
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {"status": "sent", "http_status": response.status_code}
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("Notification delivery failed via callback: %s", exc)
            return None


class SlackNotifier:
    """Send notifications to Slack via webhook."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    @staticmethod
    def _format_message(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        alerts = payload.get("alerts", []) or []
        critical_alerts = [
            alert
            for alert in alerts
            if str(alert.get("severity", "")).lower() == "critical"
        ]

        if not critical_alerts:
            return None

        patient_id = payload.get("patient_id", "unknown")
        summary_lines = [
            f"*Critical alert for patient* `{patient_id}`",
            f"Alerts detected: {len(critical_alerts)} critical / {len(alerts)} total",
        ]

        for alert in critical_alerts[:3]:
            summary_lines.append(
                f"• {alert.get('message', 'Critical alert')} ({alert.get('type', 'alert')})"
            )

        risk_scores = payload.get("risk_scores", {}) or {}
        if risk_scores:
            top_risk_name = None
            top_risk_value = None
            for risk_name, risk_value in risk_scores.items():
                if isinstance(risk_value, (int, float)) and (
                    top_risk_value is None or risk_value > top_risk_value
                ):
                    top_risk_name = risk_name
                    top_risk_value = risk_value

            if top_risk_name is not None:
                summary_lines.append(
                    f"Top risk: {top_risk_name.replace('_', ' ')} ({top_risk_value:.2f})"
                )

        return {"text": "\n".join(summary_lines)}

    async def notify(
        self, payload: Dict[str, Any], correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        message = self._format_message(payload)
        if not message:
            return None

        headers = {"Content-Type": "application/json"}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=message, headers=headers)
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {"status": "sent", "http_status": response.status_code}
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("Notification delivery failed via Slack: %s", exc)
            return None


class EmailNotifier:
    """Send notifications via email."""
    
    def __init__(self, email_service=None):
        self.email_service = email_service
    
    async def notify(
        self, payload: Dict[str, Any], correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Send email notification."""
        if not self.email_service:
            return None
        
        # Extract recipient email from payload
        recipient_email = payload.get("recipient_email") or payload.get("email")
        if not recipient_email:
            logger.warning("No recipient email in payload, skipping email notification")
            return None
        
        notification_type = payload.get("notification_type", "default")
        patient_id = payload.get("patient_id")
        alert_data = payload.get("alerts") and {"alerts": payload.get("alerts")} or None
        risk_scores = payload.get("risk_scores")
        
        success = await self.email_service.send_notification_email(
            to_email=recipient_email,
            notification_type=notification_type,
            patient_id=patient_id,
            alert_data=alert_data,
            risk_scores=risk_scores,
        )
        
        return {"status": "sent" if success else "failed"}


class Notifier:
    """Coordinator for notification channels (webhook, Slack, FCM, Email, and Calendar)."""

    def __init__(
        self,
        callback_url: Optional[str] = None,
        fcm_server_key: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        email_service: Optional[Any] = None,
        google_calendar_service: Optional[Any] = None,
        microsoft_calendar_service: Optional[Any] = None,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> None:
        self.callback_url = callback_url or os.getenv("NOTIFICATION_URL", "").strip()
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL", "").strip()
        self.fcm_server_key = fcm_server_key or os.getenv("FCM_SERVER_KEY", "").strip()
        self.email_service = email_service
        self.google_calendar_service = google_calendar_service
        self.microsoft_calendar_service = microsoft_calendar_service
        self.registered_devices: List[Dict[str, str]] = []

        if channels is not None:
            self.channels = channels
        else:
            configured_channels: List[NotificationChannel] = []
            if self.callback_url:
                configured_channels.append(WebhookNotifier(self.callback_url))
            if self.slack_webhook_url:
                configured_channels.append(SlackNotifier(self.slack_webhook_url))
            if self.email_service:
                configured_channels.append(EmailNotifier(self.email_service))
            self.channels = configured_channels

    def register_device(self, device_token: str, platform: str) -> Dict[str, str]:
        device = {"device_token": device_token, "platform": platform}
        for existing in self.registered_devices:
            if existing["device_token"] == device_token:
                existing.update(device)
                return existing

        self.registered_devices.append(device)
        return device

    async def _send_fcm(
        self, payload: Dict[str, Any], data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not self.fcm_server_key or not self.registered_devices:
            logger.info("FCM notification skipped: no server key or registered devices")
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"key={self.fcm_server_key}",
        }
        title = payload.get("title") or f"Patient {payload.get('patient_id', 'update')}"
        body_text = payload.get("body") or (
            f"Risk: {payload.get('risk_summary', '')}" if payload.get("risk_summary") else ""
        )

        notification_content = {
            "title": title,
            "body": body_text,
            "click_action": payload.get("deep_link") or payload.get("click_action"),
        }

        body = {
            "registration_ids": [device["device_token"] for device in self.registered_devices],
            "notification": notification_content,
        }
        if data or payload:
            data_payload = data.copy() if data else {}
            data_payload.update(
                {
                    "patient_id": payload.get("patient_id"),
                    "alerts": payload.get("alerts"),
                    "analysis": payload.get("analysis"),
                    "deep_link": payload.get("deep_link"),
                    "correlation_id": payload.get("correlation_id"),
                }
            )
            body["data"] = data_payload

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://fcm.googleapis.com/fcm/send", json=body, headers=headers
                )
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {"status": "sent", "http_status": response.status_code}
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("Notification delivery failed via FCM: %s", exc)
            return None

    async def notify(
        self, payload: Dict[str, Any], correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Send a notification asynchronously to all configured channels."""

        tasks = [channel.notify(payload, correlation_id) for channel in self.channels]
        task_names = [channel.__class__.__name__ for channel in self.channels]

        if self.fcm_server_key and self.registered_devices:
            tasks.append(self._send_fcm(payload))
            task_names.append("FCM")

        if not tasks:
            logger.info("Notification skipped: no destination configured")
            return None

        results: Dict[str, Any] = {}

        async def _collect(name: str, coro):
            try:
                results[name] = await coro
            except Exception as exc:  # pragma: no cover - logging only
                logger.warning("Notification delivery failed (%s): %s", name, exc)

        async with anyio.create_task_group() as tg:
            for task_name, task in zip(task_names, tasks):
                tg.start_soon(_collect, task_name, task)

        return results or None

    async def send(
        self, payload: Dict[str, Any], correlation_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Backward compatible alias for notify."""

        return await self.notify(payload, correlation_id)

    async def send_push_notification(
        self,
        title: str,
        body: str,
        deep_link: str,
        correlation_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Send a concise push notification for mobile clients."""

        notification_payload = {
            "title": title,
            "body": body,
            "click_action": deep_link,
            "deep_link": deep_link,
        }

        return await self._send_fcm(
            notification_payload,
            data={"deep_link": deep_link, "correlation_id": correlation_id} if deep_link else None,
        )

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class Notifier:
    """Send notifications to an external callback endpoint or FCM."""

    def __init__(self, callback_url: Optional[str] = None, fcm_server_key: Optional[str] = None) -> None:
        self.callback_url = callback_url or os.getenv("NOTIFICATION_URL", "").strip()
        self.fcm_server_key = fcm_server_key or os.getenv("FCM_SERVER_KEY", "").strip()
        self.registered_devices: List[Dict[str, str]] = []

    def register_device(self, device_token: str, platform: str) -> Dict[str, str]:
        device = {"device_token": device_token, "platform": platform}
        for existing in self.registered_devices:
            if existing["device_token"] == device_token:
                existing.update(device)
                return existing

        self.registered_devices.append(device)
        return device

    async def _send_callback(self, payload: Dict[str, Any], correlation_id: str) -> Optional[Dict[str, Any]]:
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

    async def _send_fcm(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.fcm_server_key:
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"key={self.fcm_server_key}",
        }
        body = {
            "registration_ids": [device["device_token"] for device in self.registered_devices],
            "notification": payload,
        }

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

    async def send(self, payload: Dict[str, Any], correlation_id: str = "") -> Optional[Dict[str, Any]]:
        """Send a notification asynchronously.

        Args:
            payload: Notification body to send as JSON.
            correlation_id: Optional correlation identifier for tracing.
        """
        tasks = []
        task_names = []

        if self.callback_url:
            tasks.append(self._send_callback(payload, correlation_id))
            task_names.append("callback")
        if self.fcm_server_key and self.registered_devices:
            tasks.append(self._send_fcm(payload))
            task_names.append("fcm")

        if not tasks:
            logger.info("Notification skipped: no destination configured")
            return None

        results: Dict[str, Any] = {}
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for task_name, result in zip(task_names, responses):
            if isinstance(result, Exception):
                logger.warning("Notification delivery failed (%s): %s", task_name, result)
            elif result is not None:
                results[task_name] = result

        return results or None

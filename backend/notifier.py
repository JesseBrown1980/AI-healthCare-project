import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class Notifier:
    """Send notifications to an external callback endpoint."""

    def __init__(self, callback_url: Optional[str] = None) -> None:
        self.callback_url = callback_url or os.getenv("NOTIFICATION_URL", "").strip()

    async def send(self, payload: Dict[str, Any], correlation_id: str = "") -> Optional[Dict[str, Any]]:
        """Send a notification asynchronously.

        Args:
            payload: Notification body to send as JSON.
            correlation_id: Optional correlation identifier for tracing.
        """
        if not self.callback_url:
            logger.info("Notification skipped: NOTIFICATION_URL not configured")
            return None

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
            logger.warning("Notification delivery failed: %s", exc)
            return None

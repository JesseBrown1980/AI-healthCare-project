from unittest.mock import AsyncMock

import pytest

from backend.notification_service import NotificationService


@pytest.mark.anyio
async def test_notification_service_sends_when_critical():
    notifier = AsyncMock()
    notifier.send_push_notification = AsyncMock()
    service = NotificationService(notifier, notifications_enabled=True)

    analysis_result = {
        "patient_id": "123",
        "alerts": [{"severity": "critical", "message": "test"}],
        "alert_count": 1,
        "risk_scores": {"cardiovascular_risk": 0.8},
    }

    await service.notify_if_needed(analysis_result, correlation_id="corr-1", notify=True)

    notifier.notify.assert_awaited()
    notifier.send_push_notification.assert_awaited()


@pytest.mark.anyio
async def test_notification_service_skips_when_disabled():
    notifier = AsyncMock()
    service = NotificationService(notifier, notifications_enabled=False)

    analysis_result = {
        "patient_id": "123",
        "alerts": [{"severity": "critical", "message": "test"}],
        "alert_count": 1,
    }

    await service.notify_if_needed(analysis_result, correlation_id="corr-1", notify=True)

    notifier.notify.assert_not_awaited()

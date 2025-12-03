import pytest

from backend.alert_service import AlertService


@pytest.mark.anyio
async def test_identify_alerts_and_highest_severity():
    service = AlertService()

    patient_data = {
        "conditions": [{"code": "Acute_MI"}],
        "observations": [
            {"code": "LDL", "value": 200, "unit": "mg/dL", "interpretation": "high"}
        ],
    }

    alerts = await service.identify_alerts(patient_data)

    assert any(alert["severity"] == "critical" for alert in alerts)
    assert any(alert["type"] == "lab" for alert in alerts)
    assert service.highest_alert_severity(alerts) == "critical"

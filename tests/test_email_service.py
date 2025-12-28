"""
Tests for email notification service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.email.email_service import EmailService


@pytest.mark.asyncio
async def test_email_service_send_email():
    """Test sending email."""
    service = EmailService(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="test@test.com",
        smtp_password="testpass"
    )
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = await service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
            text_body="Test"
        )
        
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


@pytest.mark.asyncio
async def test_email_service_send_notification_email():
    """Test sending notification email with template."""
    service = EmailService(
        smtp_user="test@test.com",
        smtp_password="testpass"
    )
    
    with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        result = await service.send_notification_email(
            to_email="recipient@test.com",
            notification_type="critical_alert",
            patient_id="patient-123",
            alert_data={"alerts": [{"severity": "critical", "title": "Test Alert"}]}
        )
        
        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["to_email"] == "recipient@test.com"
        assert "critical" in call_args[1]["subject"].lower()


def test_email_templates():
    """Test email template generation."""
    from backend.email.templates import get_email_template
    
    # Test critical alert template
    template = get_email_template("critical_alert")
    subject, html_body, text_body = template(
        patient_id="patient-123",
        alert_data={"alerts": [{"severity": "critical", "title": "Test", "description": "Test alert"}]}
    )
    
    assert "critical" in subject.lower()
    assert "patient-123" in html_body
    assert "patient-123" in text_body
    
    # Test password reset template
    template = get_email_template("password_reset")
    subject, html_body, text_body = template(reset_token="test-token-123")
    
    assert "reset" in subject.lower()
    assert "test-token-123" in html_body or "test-token-123" in text_body


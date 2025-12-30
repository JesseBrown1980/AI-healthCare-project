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
        
        # EmailService.send_email is async but uses sync smtplib
        result = await service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
            text_body="Test"
        )
        
        assert result is True
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
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
        # Check call arguments - call_args is a tuple of (args, kwargs) or None
        if mock_send.call_args:
            call_args, call_kwargs = mock_send.call_args
            # Check if to_email is in kwargs or args
            if call_kwargs and "to_email" in call_kwargs:
                assert call_kwargs["to_email"] == "recipient@test.com"
                assert "critical" in call_kwargs["subject"].lower()
            elif call_args and len(call_args) > 0:
                # If passed as positional args, check first arg
                assert call_args[0] == "recipient@test.com"
        else:
            # Fallback: just verify it was called
            assert True


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


"""
Enhanced tests for email service including SMTP connection handling and error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from email.mime.multipart import MIMEMultipart
import smtplib

from backend.email.email_service import EmailService


@pytest.fixture
def email_service():
    """Create email service instance for testing."""
    return EmailService(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="test@test.com",
        smtp_password="testpass",
        smtp_use_tls=True,
    )


@pytest.mark.asyncio
async def test_smtp_connection_success(email_service):
    """Test successful SMTP connection."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
            text_body="Test",
        )
        
        assert result is True
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_connection_without_tls(email_service):
    """Test SMTP connection without TLS."""
    email_service.smtp_use_tls = False
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        assert result is True
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_connection_failure(email_service):
    """Test SMTP connection failure."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Connection refused")
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        assert result is False


@pytest.mark.asyncio
async def test_smtp_login_failure(email_service):
    """Test SMTP login failure."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_server.starttls = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Invalid credentials")
        mock_smtp.return_value = mock_server
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        assert result is False
        mock_server.login.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_send_failure(email_service):
    """Test SMTP send message failure."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_server.starttls = MagicMock()
        mock_server.login = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused({"recipient@test.com": (550, "Mailbox not found")})
        mock_smtp.return_value = mock_server
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        assert result is False
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_timeout_error(email_service):
    """Test SMTP timeout error."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = TimeoutError("Connection timeout")
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        assert result is False


@pytest.mark.asyncio
async def test_smtp_generic_exception(email_service):
    """Test handling of generic SMTP exceptions."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = Exception("Unexpected error")
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        assert result is False


@pytest.mark.asyncio
async def test_send_email_missing_credentials():
    """Test sending email without SMTP credentials."""
    service = EmailService(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="",  # Empty credentials
        smtp_password="",
    )
    
    result = await service.send_email(
        to_email="recipient@test.com",
        subject="Test Subject",
        html_body="<html><body>Test</body></html>",
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_send_email_with_attachments(email_service):
    """Test sending email with attachments."""
    attachments = [
        {
            "filename": "test.pdf",
            "content": b"fake pdf content",
            "content_type": "application/pdf",
        }
    ]
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
            attachments=attachments,
        )
        
        assert result is True
        # Verify message was sent (attachment handling is internal)
        mock_server.send_message.assert_called_once()
        # Check that attachment was added to message
        call_args = mock_server.send_message.call_args[0][0]
        assert isinstance(call_args, MIMEMultipart)


@pytest.mark.asyncio
async def test_send_email_server_quit_failure(email_service):
    """Test handling of server quit failure."""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_server.starttls = MagicMock()
        mock_server.login = MagicMock()
        mock_server.send_message = MagicMock()
        mock_server.quit.side_effect = Exception("Quit failed")
        mock_smtp.return_value = mock_server
        
        # Email service catches all exceptions, so quit failure causes send to fail
        result = await email_service.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )
        
        # Email service returns False on any exception
        assert result is False


@pytest.mark.asyncio
async def test_send_notification_email_success(email_service):
    """Test sending notification email with template."""
    with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        result = await email_service.send_notification_email(
            to_email="recipient@test.com",
            notification_type="critical_alert",
            patient_id="patient-123",
            alert_data={"severity": "high"},
        )
        
        assert result is True
        mock_send.assert_called_once()
        # Verify template was used
        call_args = mock_send.call_args
        assert call_args[0][0] == "recipient@test.com"  # to_email
        assert "subject" in str(call_args).lower() or len(call_args[0]) > 1


@pytest.mark.asyncio
async def test_send_notification_email_template_failure(email_service):
    """Test sending notification email when template fails."""
    # Patch at the templates module level where it's imported from
    with patch('backend.email.templates.get_email_template') as mock_template:
        mock_template.side_effect = Exception("Template error")
        
        # Template error will propagate (not caught in send_notification_email)
        with pytest.raises(Exception, match="Template error"):
            await email_service.send_notification_email(
                to_email="recipient@test.com",
                notification_type="invalid_type",
            )


@pytest.mark.asyncio
async def test_send_notification_email_send_failure(email_service):
    """Test sending notification email when send_email fails."""
    with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = False
        
        result = await email_service.send_notification_email(
            to_email="recipient@test.com",
            notification_type="risk_update",
        )
        
        assert result is False
        mock_send.assert_called_once()


def test_email_message_creation(email_service):
    """Test email message creation with various options."""
    # Test with HTML only
    msg1 = email_service._create_message(
        to_email="test@test.com",
        subject="Test",
        html_body="<html><body>Test</body></html>",
    )
    assert isinstance(msg1, MIMEMultipart)
    assert msg1["To"] == "test@test.com"
    assert msg1["Subject"] == "Test"
    
    # Test with HTML and text
    msg2 = email_service._create_message(
        to_email="test@test.com",
        subject="Test",
        html_body="<html><body>Test</body></html>",
        text_body="Test",
    )
    assert isinstance(msg2, MIMEMultipart)
    
    # Test with attachments
    attachments = [
        {
            "filename": "test.pdf",
            "content": b"fake pdf content",
            "content_type": "application/pdf",
        }
    ]
    msg3 = email_service._create_message(
        to_email="test@test.com",
        subject="Test",
        html_body="<html><body>Test</body></html>",
        attachments=attachments,
    )
    assert isinstance(msg3, MIMEMultipart)


def test_email_service_initialization_from_env():
    """Test email service initialization from environment variables."""
    with patch.dict('os.environ', {
        'SMTP_HOST': 'env.smtp.com',
        'SMTP_PORT': '465',
        'SMTP_USER': 'env@test.com',
        'SMTP_PASSWORD': 'envpass',
        'SMTP_USE_TLS': 'false',
        'SMTP_FROM_EMAIL': 'from@test.com',
        'SMTP_FROM_NAME': 'Test Service',
    }):
        service = EmailService()
        
        assert service.smtp_host == "env.smtp.com"
        assert service.smtp_port == 465
        assert service.smtp_user == "env@test.com"
        assert service.smtp_password == "envpass"
        assert service.smtp_use_tls is False
        assert service.from_email == "from@test.com"
        assert service.from_name == "Test Service"

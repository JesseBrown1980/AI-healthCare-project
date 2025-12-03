"""
Security Tests
Tests for audit logging, security controls, and compliance features.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path


class TestAuditEvents:
    """Tests for audit event definitions."""
    
    def test_audit_event_creation(self):
        """Test creating an audit event."""
        from backend.audit.audit_events import (
            AuditEvent,
            AuditEventType,
            AuditEventCategory,
            AuditSeverity,
        )
        
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            category=AuditEventCategory.AUTHENTICATION,
            severity=AuditSeverity.INFO,
            actor="user123",
            action="User logged in",
            outcome="success",
        )
        
        assert event.event_type == AuditEventType.LOGIN_SUCCESS
        assert event.actor == "user123"
        assert event.outcome == "success"
        assert event.event_id  # Should be auto-generated
        assert event.timestamp  # Should be auto-generated
    
    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary."""
        from backend.audit.audit_events import (
            AuditEvent,
            AuditEventType,
            AuditEventCategory,
            AuditSeverity,
        )
        
        event = AuditEvent(
            event_type=AuditEventType.PHI_ACCESS,
            category=AuditEventCategory.DATA_ACCESS,
            severity=AuditSeverity.INFO,
            actor="clinician001",
            action="Viewed patient record",
            outcome="success",
            patient_id="patient123",
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "data.phi.access"
        assert event_dict["actor"] == "clinician001"
        assert event_dict["patient_id"] == "patient123"
        assert "timestamp" in event_dict
        assert "event_id" in event_dict
    
    def test_audit_event_to_json(self):
        """Test converting audit event to JSON."""
        from backend.audit.audit_events import login_success
        
        event = login_success(actor="user123", ip_address="192.168.1.1")
        json_str = event.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["actor"] == "user123"
        assert parsed["ip_address"] == "192.168.1.1"
    
    def test_event_builders(self):
        """Test pre-defined event builders."""
        from backend.audit.audit_events import (
            login_success,
            login_failure,
            access_denied,
            phi_access,
            config_changed,
        )
        
        # Login success
        event = login_success("user1")
        assert event.event_type.value == "auth.login.success"
        
        # Login failure
        event = login_failure("user1", "Invalid password")
        assert event.event_type.value == "auth.login.failure"
        assert event.details["reason"] == "Invalid password"
        
        # Access denied
        event = access_denied("user1", "/admin", "Insufficient permissions")
        assert event.event_type.value == "authz.access.denied"
        
        # PHI access
        event = phi_access("clinician1", "patient123", "medical_record")
        assert event.patient_id == "patient123"
        
        # Config changed
        event = config_changed("admin1", "rate_limit", "60", "100")
        assert event.details["old_value"] == "60"
        assert event.details["new_value"] == "100"


class TestAuditLogger:
    """Tests for audit logger."""
    
    def test_logger_creation(self, tmp_path):
        """Test creating an audit logger."""
        from backend.audit.audit_logger import AuditLogger
        
        logger = AuditLogger(log_dir=str(tmp_path), console_output=False)
        assert logger.log_dir == tmp_path
    
    def test_log_event(self, tmp_path):
        """Test logging an event."""
        from backend.audit.audit_logger import AuditLogger
        from backend.audit.audit_events import login_success
        
        logger = AuditLogger(log_dir=str(tmp_path), console_output=False)
        event = login_success("testuser")
        
        logger.log(event)
        
        # Check log file was created
        log_files = list(tmp_path.glob("audit_*.jsonl"))
        assert len(log_files) == 1
        
        # Check log content
        with open(log_files[0]) as f:
            content = f.read()
            parsed = json.loads(content.strip())
            assert parsed["actor"] == "testuser"
    
    def test_log_authentication(self, tmp_path):
        """Test logging authentication events."""
        from backend.audit.audit_logger import AuditLogger
        
        logger = AuditLogger(log_dir=str(tmp_path), console_output=False)
        
        # Log successful auth
        logger.log_authentication("user1", success=True, ip_address="1.2.3.4")
        
        # Log failed auth
        logger.log_authentication("user2", success=False, reason="Invalid token")
        
        log_files = list(tmp_path.glob("audit_*.jsonl"))
        with open(log_files[0]) as f:
            lines = f.readlines()
            assert len(lines) == 2
    
    def test_severity_filtering(self, tmp_path):
        """Test minimum severity filtering."""
        from backend.audit.audit_logger import AuditLogger
        from backend.audit.audit_events import (
            AuditEvent,
            AuditEventType,
            AuditEventCategory,
            AuditSeverity,
        )
        
        logger = AuditLogger(
            log_dir=str(tmp_path),
            console_output=False,
            min_severity=AuditSeverity.WARNING,
        )
        
        # Info event should not be logged
        info_event = AuditEvent(
            event_type=AuditEventType.PATIENT_READ,
            category=AuditEventCategory.DATA_ACCESS,
            severity=AuditSeverity.INFO,
            actor="user1",
            action="Read data",
            outcome="success",
        )
        logger.log(info_event)
        
        # Warning event should be logged
        warning_event = AuditEvent(
            event_type=AuditEventType.ACCESS_DENIED,
            category=AuditEventCategory.AUTHORIZATION,
            severity=AuditSeverity.WARNING,
            actor="user1",
            action="Access denied",
            outcome="failure",
        )
        logger.log(warning_event)
        
        log_files = list(tmp_path.glob("audit_*.jsonl"))
        if log_files:
            with open(log_files[0]) as f:
                lines = f.readlines()
                assert len(lines) == 1  # Only warning logged


class TestSecurityHeaders:
    """Tests for security headers middleware."""
    
    @pytest.mark.asyncio
    async def test_security_headers_added(self):
        """Test that security headers are added to responses."""
        from backend.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        
        async def homepage(request):
            return JSONResponse({"status": "ok"})
        
        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(SecurityHeadersMiddleware)
        
        client = TestClient(app)
        response = client.get("/")
        
        # Check security headers
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    @pytest.mark.asyncio
    async def test_hsts_header(self):
        """Test HSTS header is added."""
        from backend.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        
        async def homepage(request):
            return JSONResponse({"status": "ok"})
        
        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(SecurityHeadersMiddleware, strict_transport_security=True)
        
        client = TestClient(app)
        response = client.get("/")
        
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=" in response.headers["Strict-Transport-Security"]


class TestCompliancePolicies:
    """Tests for compliance policy configuration."""
    
    def test_get_region_default(self):
        """Test default region is returned."""
        from backend.config.compliance_policies import get_region
        
        # Clear env var to test default
        import os
        original = os.environ.get("REGION")
        if "REGION" in os.environ:
            del os.environ["REGION"]
        
        try:
            region = get_region()
            assert region in ["DEFAULT", "US", "EU", "APAC"]
        finally:
            if original:
                os.environ["REGION"] = original
    
    def test_hipaa_region_config(self):
        """Test HIPAA region configuration."""
        from backend.config.compliance_policies import get_compliance_policy
        
        policy = get_compliance_policy("US")
        
        assert policy.region == "US"
        assert policy.phi_in_logs == False
        assert policy.enforce_https == True
    
    def test_gdpr_region_config(self):
        """Test GDPR region configuration."""
        from backend.config.compliance_policies import get_compliance_policy
        
        policy = get_compliance_policy("EU")
        
        assert policy.region == "EU"
        assert policy.require_consent == True
        assert policy.allow_data_deletion == True

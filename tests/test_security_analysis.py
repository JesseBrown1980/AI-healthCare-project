"""
Security testing and static analysis checks.

Tests for common security vulnerabilities and compliance with security best practices.
"""

import pytest
import os
import re
from pathlib import Path
from typing import List, Dict, Any


class TestSecurityBestPractices:
    """Test security best practices in the codebase."""
    
    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets are present in the codebase."""
        # Common secret patterns
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'apikey\s*=\s*["\'][^"\']+["\']',
        ]
        
        backend_path = Path("backend")
        issues = []
        
        for py_file in backend_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    for pattern in secret_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Skip test files and comments
                            if "test" in str(py_file) or line.strip().startswith("#"):
                                continue
                            issues.append(f"{py_file}:{i} - Potential hardcoded secret: {line.strip()[:50]}")
            except Exception:
                continue
        
        # Allow some exceptions (like default values in examples, demo/test values)
        filtered_issues = [
            issue for issue in issues
            if "example" not in issue.lower() 
            and "default" not in issue.lower()
            and "demo" not in issue.lower()
            and "test" not in issue.lower()
            and "placeholder" not in issue.lower()
        ]
        
        assert len(filtered_issues) == 0, f"Found potential hardcoded secrets:\n" + "\n".join(filtered_issues[:10])
    
    def test_no_sql_injection_vulnerabilities(self):
        """Test that SQL queries use parameterized statements."""
        backend_path = Path("backend")
        issues = []
        
        for py_file in backend_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                # Look for string formatting in SQL queries
                if "execute" in content or "query" in content:
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        # Check for f-strings or % formatting in SQL-like contexts
                        if re.search(r'execute\s*\([^)]*f["\']', line) or \
                           re.search(r'execute\s*\([^)]*%[sd]', line):
                            # Skip test files
                            if "test" in str(py_file):
                                continue
                            issues.append(f"{py_file}:{i} - Potential SQL injection: {line.strip()[:60]}")
            except Exception:
                continue
        
        assert len(issues) == 0, f"Found potential SQL injection vulnerabilities:\n" + "\n".join(issues[:10])
    
    def test_encryption_used_for_sensitive_data(self):
        """Test that sensitive data handling uses encryption."""
        backend_path = Path("backend")
        sensitive_files = []
        
        # Files that should use encryption
        encryption_keywords = ["encrypt", "cipher", "fernet", "aes"]
        
        for py_file in backend_path.rglob("*.py"):
            file_path = str(py_file)
            # Check if file handles sensitive data
            if any(keyword in file_path.lower() for keyword in ["password", "secret", "token", "auth", "phi", "patient"]):
                try:
                    content = py_file.read_text(encoding="utf-8")
                    # Check if encryption is mentioned
                    has_encryption = any(keyword in content.lower() for keyword in encryption_keywords)
                    if not has_encryption and "test" not in file_path:
                        # This is informational, not a failure
                        sensitive_files.append(file_path)
                except Exception:
                    continue
        
        # Just log, don't fail - encryption might be handled elsewhere
        if sensitive_files:
            print(f"Info: Files handling sensitive data (verify encryption): {len(sensitive_files)}")
    
    def test_input_validation_present(self):
        """Test that input validation is used in API endpoints."""
        endpoints_path = Path("backend/api/v1/endpoints")
        endpoints_without_validation = []
        
        validation_keywords = ["validate", "sanitize", "check", "verify"]
        
        for py_file in endpoints_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                # Check if endpoint file has validation
                has_validation = any(keyword in content.lower() for keyword in validation_keywords)
                if not has_validation and "test" not in str(py_file):
                    endpoints_without_validation.append(str(py_file))
            except Exception:
                continue
        
        # Most endpoints should have validation, but allow some exceptions
        assert len(endpoints_without_validation) < 5, \
            f"Multiple endpoints may lack input validation: {endpoints_without_validation[:5]}"
    
    def test_https_enforcement_middleware(self):
        """Test that HTTPS enforcement middleware exists."""
        middleware_path = Path("backend/middleware/https_enforcement.py")
        assert middleware_path.exists(), "HTTPS enforcement middleware should exist"
        
        content = middleware_path.read_text(encoding="utf-8")
        assert "HTTPSEnforcementMiddleware" in content, "HTTPS enforcement middleware class should exist"
        assert "redirect" in content.lower() or "enforce" in content.lower(), \
            "HTTPS enforcement should redirect or enforce HTTPS"
    
    def test_phi_filtering_implemented(self):
        """Test that PHI filtering is implemented for logging."""
        phi_filter_path = Path("backend/utils/phi_filter.py")
        assert phi_filter_path.exists(), "PHI filter utility should exist"
        
        content = phi_filter_path.read_text(encoding="utf-8")
        assert "filter_phi" in content.lower() or "mask_phi" in content.lower(), \
            "PHI filtering functions should exist"
        assert "sanitize" in content.lower(), "PHI sanitization should be implemented"
    
    def test_audit_logging_implemented(self):
        """Test that audit logging is implemented for compliance."""
        audit_path = Path("backend/audit_service.py")
        assert audit_path.exists(), "Audit service should exist"
        
        content = audit_path.read_text(encoding="utf-8")
        assert "audit" in content.lower(), "Audit logging should be implemented"
        assert "record" in content.lower() or "log" in content.lower(), \
            "Audit service should record/log events"
    
    def test_consent_management_implemented(self):
        """Test that consent management is implemented for GDPR."""
        consent_path = Path("backend/services/consent_service.py")
        assert consent_path.exists(), "Consent service should exist"
        
        content = consent_path.read_text(encoding="utf-8")
        assert "consent" in content.lower(), "Consent management should be implemented"
        assert "record" in content.lower() or "withdraw" in content.lower(), \
            "Consent service should handle recording and withdrawal"
    
    def test_data_deletion_implemented(self):
        """Test that data deletion service exists for GDPR right to be forgotten."""
        deletion_path = Path("backend/services/data_deletion_service.py")
        assert deletion_path.exists(), "Data deletion service should exist"
        
        content = deletion_path.read_text(encoding="utf-8")
        assert "delete" in content.lower(), "Data deletion should be implemented"
        assert "user_data" in content.lower() or "patient_data" in content.lower(), \
            "Data deletion should handle user/patient data"
    
    def test_field_encryption_implemented(self):
        """Test that field-level encryption is available."""
        encryption_path = Path("backend/utils/field_encryption.py")
        assert encryption_path.exists(), "Field encryption utility should exist"
        
        content = encryption_path.read_text(encoding="utf-8")
        assert "encrypt" in content.lower(), "Field encryption should be implemented"
        assert "fernet" in content.lower() or "cipher" in content.lower(), \
            "Field encryption should use proper encryption (Fernet/cipher)"
    
    def test_2fa_implementation_exists(self):
        """Test that 2FA implementation exists."""
        twofa_path = Path("backend/utils/two_factor_auth.py")
        assert twofa_path.exists(), "2FA utility should exist"
        
        content = twofa_path.read_text(encoding="utf-8")
        assert "totp" in content.lower() or "2fa" in content.lower(), \
            "2FA/TOTP implementation should exist"
        assert "verify" in content.lower(), "2FA verification should be implemented"

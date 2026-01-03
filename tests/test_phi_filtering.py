"""
Unit tests for PHI filtering in logs.

Tests PHI detection, masking, and filtering based on compliance policies.
"""

import pytest
import os
from unittest.mock import patch

from backend.utils.phi_filter import (
    mask_phi_value,
    hash_phi_value,
    mask_text,
    filter_phi_from_dict,
    filter_phi_from_log_data,
    sanitize_for_logging,
    PHI_PATTERNS,
    PHI_FIELD_NAMES,
)
from backend.config.compliance_policies import is_phi_allowed_in_logs


class TestPHIDetection:
    """Test PHI pattern detection."""
    
    def test_ssn_detection(self):
        """Test SSN pattern detection."""
        text = "Patient SSN: 123-45-6789"
        assert PHI_PATTERNS["ssn"].search(text) is not None
    
    def test_phone_detection(self):
        """Test phone number detection."""
        text = "Contact: 555-123-4567"
        assert PHI_PATTERNS["phone"].search(text) is not None
    
    def test_email_detection(self):
        """Test email detection."""
        text = "Email: patient@example.com"
        assert PHI_PATTERNS["email"].search(text) is not None
    
    def test_patient_id_detection(self):
        """Test patient ID detection."""
        text = "Patient ID: patient-12345"
        assert PHI_PATTERNS["patient_id"].search(text) is not None
    
    def test_mrn_detection(self):
        """Test MRN detection."""
        text = "MRN: 987654"
        assert PHI_PATTERNS["mrn"].search(text) is not None
    
    def test_date_detection(self):
        """Test date of birth detection."""
        text = "DOB: 01/15/1980"
        assert PHI_PATTERNS["date_of_birth"].search(text) is not None
    
    def test_zip_code_detection(self):
        """Test ZIP code detection."""
        text = "ZIP: 12345-6789"
        assert PHI_PATTERNS["zip_code"].search(text) is not None


class TestPHIMasking:
    """Test PHI masking functions."""
    
    def test_mask_phi_value_string(self):
        """Test masking string values."""
        result = mask_phi_value("John Doe")
        # Masking preserves first 2 and last 2 chars for values > 8 chars
        # "John Doe" is 8 chars, so it shows first char and last char
        assert result.startswith("J")
        assert result.endswith("e")
        assert "*" in result
        assert len(result) == len("John Doe")
        assert result != "John Doe"  # Should be masked
        assert result == "J******e"  # Exact format for 8-char string
    
    def test_mask_phi_value_number(self):
        """Test masking numeric values."""
        result = mask_phi_value("123-45-6789")
        assert "*" in result
        assert len(result) == len("123-45-6789")
    
    def test_mask_phi_value_custom_char(self):
        """Test masking with custom character."""
        result = mask_phi_value("test", mask_char="#")
        assert "#" in result
        assert "*" not in result
    
    def test_hash_phi_value(self):
        """Test hashing PHI values."""
        value = "123-45-6789"
        result1 = hash_phi_value(value)
        result2 = hash_phi_value(value)
        
        # Same value should produce same hash
        assert result1 == result2
        assert result1 != value
        assert result1.startswith("HASH:")
        assert len(result1) > len("HASH:")  # Should have hash suffix
    
    def test_hash_phi_value_with_salt(self):
        """Test hashing with salt produces different results."""
        value = "123-45-6789"
        result1 = hash_phi_value(value, salt="salt1")
        result2 = hash_phi_value(value, salt="salt2")
        
        assert result1 != result2
    
    def test_mask_text_ssn(self):
        """Test masking SSN in text."""
        text = "Patient SSN: 123-45-6789"
        result = mask_text(text)
        assert "123-45-6789" not in result
        assert "*" in result
    
    def test_mask_text_phone(self):
        """Test masking phone number in text."""
        text = "Call 555-123-4567"
        result = mask_text(text)
        assert "555-123-4567" not in result
        assert "*" in result
    
    def test_mask_text_email(self):
        """Test masking email in text."""
        text = "Email: patient@example.com"
        result = mask_text(text)
        assert "patient@example.com" not in result
        assert "*" in result


class TestPHIDictFiltering:
    """Test PHI filtering from dictionaries."""
    
    def test_filter_phi_from_dict_name_field(self):
        """Test filtering PHI from dict with name field."""
        data = {
            "patient_name": "John Doe",
            "age": 45,
            "diagnosis": "Hypertension"
        }
        result = filter_phi_from_dict(data)
        
        assert result["patient_name"] != "John Doe"
        assert "*" in result["patient_name"]
        # Age is in PHI_FIELD_NAMES so it gets filtered
        assert result.get("age") != 45  # Age is filtered as PHI
        assert "*" in str(result.get("age"))
        # Diagnosis might be filtered if it contains PHI patterns
        assert "diagnosis" in result
    
    def test_filter_phi_from_dict_email_field(self):
        """Test filtering email field."""
        data = {
            "email": "patient@example.com",
            "status": "active"
        }
        result = filter_phi_from_dict(data)
        
        assert result["email"] != "patient@example.com"
        assert "*" in result["email"]
        assert result["status"] == "active"
    
    def test_filter_phi_from_dict_phone_field(self):
        """Test filtering phone field."""
        data = {
            "phone": "555-123-4567",
            "department": "Cardiology"
        }
        result = filter_phi_from_dict(data)
        
        assert result["phone"] != "555-123-4567"
        assert "*" in result["phone"]
        assert result["department"] == "Cardiology"  # Non-PHI preserved
    
    def test_filter_phi_from_dict_with_hash(self):
        """Test filtering with hash instead of mask."""
        data = {
            "ssn": "123-45-6789",
            "name": "John Doe"
        }
        result = filter_phi_from_dict(data, use_hash=True)
        
        # Should be hashed (HASH:xxxx format, not full 64-char hex)
        assert result["ssn"].startswith("HASH:")
        assert result["ssn"] != "123-45-6789"
        assert len(result["ssn"]) > len("HASH:")
        assert result["name"].startswith("HASH:")
        assert result["name"] != "John Doe"
    
    def test_filter_phi_from_dict_nested(self):
        """Test filtering nested dictionaries."""
        data = {
            "patient": {
                "name": "John Doe",
                "contact": {
                    "email": "patient@example.com"
                }
            },
            "status": "active"
        }
        result = filter_phi_from_dict(data)
        
        assert "*" in result["patient"]["name"]
        assert "*" in result["patient"]["contact"]["email"]
        assert result["status"] == "active"
    
    def test_filter_phi_from_dict_preserve_keys(self):
        """Test preserving keys when filtering."""
        data = {
            "patient_name": "John Doe",
            "age": 45
        }
        result = filter_phi_from_dict(data, preserve_keys=True)
        
        assert "patient_name" in result
        assert "age" in result


class TestPHILogFiltering:
    """Test PHI filtering in log data."""
    
    def test_filter_phi_from_log_data_us(self):
        """Test PHI filtering for US region (PHI not allowed)."""
        with patch.dict(os.environ, {"REGION": "US"}):
            log_data = {
                "message": "Patient John Doe with SSN 123-45-6789",
                "patient_name": "John Doe",
                "email": "patient@example.com",
                "timestamp": "2024-01-01T00:00:00Z"
            }
            result = filter_phi_from_log_data(log_data)
            
            # PHI should be filtered
            assert "John Doe" not in str(result.values())
            assert "123-45-6789" not in str(result.values())
            assert "patient@example.com" not in str(result.values())
            assert "timestamp" in result  # Non-PHI preserved
    
    def test_filter_phi_from_log_data_eu(self):
        """Test PHI filtering for EU region (PHI not allowed)."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            log_data = {
                "message": "Patient data accessed",
                "patient_id": "patient-123",
                "phone": "555-123-4567"
            }
            result = filter_phi_from_log_data(log_data)
            
            # PHI should be filtered
            assert "patient-123" not in str(result.values())
            assert "555-123-4567" not in str(result.values())
    
    def test_sanitize_for_logging_string(self):
        """Test sanitizing string values for logging."""
        with patch.dict(os.environ, {"REGION": "US"}):
            result = sanitize_for_logging("Patient: John Doe, SSN: 123-45-6789")
            # Masking preserves some characters, so check that full values are masked
            assert "123-45-6789" not in result
            assert "*" in result  # Should have masking
    
    def test_sanitize_for_logging_dict(self):
        """Test sanitizing dictionary values for logging."""
        with patch.dict(os.environ, {"REGION": "US"}):
            data = {"name": "John Doe", "age": 45}
            result = sanitize_for_logging(data, field_name="name")
            # sanitize_for_logging with dict calls filter_phi_from_dict which returns a dict
            # But if field_name is provided and matches PHI, it might mask the whole dict
            # Let's test without field_name to get dict filtering
            result2 = sanitize_for_logging(data)
            assert isinstance(result2, dict)
            assert result2["name"] != "John Doe"
            assert "*" in result2["name"]  # Should be masked
            # Age is in PHI_FIELD_NAMES so it gets filtered
            assert result2.get("age") != 45
    
    def test_sanitize_for_logging_phi_field_name(self):
        """Test sanitizing values with PHI field names."""
        with patch.dict(os.environ, {"REGION": "US"}):
            # Field name suggests PHI
            result = sanitize_for_logging("John Doe", field_name="patient_name")
            assert result != "John Doe"
            assert "*" in result
    
    def test_sanitize_for_logging_non_phi_field(self):
        """Test sanitizing non-PHI fields."""
        with patch.dict(os.environ, {"REGION": "US"}):
            # Non-PHI field should pass through
            result = sanitize_for_logging("active", field_name="status")
            assert result == "active"


class TestPHIFilteringCompliance:
    """Test PHI filtering respects compliance policies."""
    
    def test_phi_filtering_respects_policy_us(self):
        """Test PHI filtering respects US policy (PHI not allowed)."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_phi_allowed_in_logs() is False
            
            log_data = {
                "message": "Patient John Doe",
                "patient_name": "John Doe"
            }
            result = filter_phi_from_log_data(log_data)
            
            # PHI should be filtered
            assert "John Doe" not in str(result.values())
    
    def test_phi_filtering_respects_policy_eu(self):
        """Test PHI filtering respects EU policy (PHI not allowed)."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_phi_allowed_in_logs() is False
            
            log_data = {
                "message": "Data processed",
                "email": "patient@example.com"
            }
            result = filter_phi_from_log_data(log_data)
            
            # PHI should be filtered
            assert "patient@example.com" not in str(result.values())
